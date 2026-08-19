import cv2
import numpy as np
import math
from typing import Dict, Any, Tuple, Optional
from .classes import PlanetaryBody
from .utils import Utils

class VectorizedNoiseEngine:
    def __init__(self, seed=42):
        np.random.seed(seed % 100000)
        self.p = np.arange(256, dtype=int)
        np.random.shuffle(self.p)
        self.p = np.stack([self.p, self.p]).flatten()

    def _fade(self, t):
        return t * t * t * (t * (t * 6 - 15) + 10)

    def _lerp(self, a, b, x):
        return a + x * (b - a)

    def _grad(self, hash, x, y):
        h = hash & 15
        grad_x = 1.0 + (h & 7)
        grad_x = np.where(h & 8, -grad_x, grad_x)
        grad_y = 1.0 + (h & 3)
        grad_y = np.where(h & 4, -grad_y, grad_y)
        return grad_x * x + grad_y * y

    def perlin_2d(self, x, y, repeat_x=0):
        if repeat_x > 0: x = x % repeat_x
        xi = x.astype(int) & 255
        yi = y.astype(int) & 255
        xf = x - x.astype(int)
        yf = y - y.astype(int)
        
        u = self._fade(xf)
        v = self._fade(yf)

        n00 = self.p[self.p[xi] + yi]
        n01 = self.p[self.p[xi] + yi + 1]
        n11 = self.p[self.p[xi + 1] + yi + 1]
        n10 = self.p[self.p[xi + 1] + yi]

        x1 = self._grad(n00, xf, yf)
        x2 = self._grad(n10, xf - 1, yf)
        lerp_x1 = self._lerp(x1, x2, u)

        x3 = self._grad(n01, xf, yf - 1)
        x4 = self._grad(n11, xf - 1, yf - 1)
        lerp_x2 = self._lerp(x3, x4, u)

        return self._lerp(lerp_x1, lerp_x2, v)

    def sample_fbm(self, x, y, octaves=6, persistence=0.5, lacunarity=2.0, repeat_x=0):
        total = np.zeros_like(x, dtype=np.float32)
        frequency = 1.0
        amplitude = 1.0
        max_value = 0.0
        for _ in range(octaves):
            total += self.perlin_2d(x * frequency, y * frequency, repeat_x * frequency if repeat_x > 0 else 0) * amplitude
            max_value += amplitude
            amplitude *= persistence
            frequency *= lacunarity
        return total / max_value

    def get_map(self, width, height, scale=0.01, octaves=6):
        x = np.linspace(0, width * scale, width)
        y = np.linspace(0, height * scale, height)
        xv, yv = np.meshgrid(x, y)
        tile = self.sample_fbm(xv, yv, octaves=octaves, repeat_x=width*scale)
        return (tile - tile.min()) / (tile.max() - tile.min() + 1e-6)

def generate_planetary_maps(world: PlanetaryBody, width=1024, height=512, seed=None) -> Dict[str, Any]:
    """
    Generates procedural heightmaps, land/sea masks, biomes, and equirectangular 
    surface textures for a world based on its Size and Hydrographics code.
    """
    if seed is None:
        seed = abs(hash(world.name)) % 100000

    # Parse UWP codes
    hyd_val = Utils.from_eHex(world.hydrographics_code) if world.hydrographics_code else 7
    size_val = Utils.from_eHex(world.size_code) if world.size_code else 8
    temp_k = world.mean_temperature if world.mean_temperature else 288.0

    # Hydrographic fraction (Hydro 0 = 0%, Hydro 7 = 70%, Hydro A = 100%)
    hydro_fraction = min(1.0, max(0.0, hyd_val / 10.0))
    land_threshold = 1.0 - hydro_fraction

    engine = VectorizedNoiseEngine(seed=seed)
    raw_noise = engine.get_map(width, height, scale=0.012, octaves=6)

    # Apply heightmap synthesis
    heightmap = np.power(raw_noise, 1.2)
    
    # Calculate land mask based on hydrographic threshold
    sorted_heights = np.sort(heightmap.flatten())
    cutoff_idx = int((1.0 - hydro_fraction) * len(sorted_heights))
    sea_level = sorted_heights[min(len(sorted_heights)-1, max(0, cutoff_idx))]
    
    land_mask = heightmap > sea_level

    # Latitude temperature gradient (equator warm, poles cold)
    lat_y = np.linspace(-1.0, 1.0, height)
    lat_matrix = np.tile(np.abs(lat_y)[:, np.newaxis], (1, width)) # 0 at equator, 1 at poles
    
    temp_map = temp_k - (lat_matrix * 65.0) + (heightmap * 15.0)

    # Initialize RGB surface texture (H, W, 3) in RGB format
    surface_texture = np.zeros((height, width, 3), dtype=np.uint8)

    # Color Palettes
    COLOR_DEEP_OCEAN = np.array([10, 35, 90], dtype=np.uint8)
    COLOR_SHALLOW_WATER = np.array([30, 110, 180], dtype=np.uint8)
    COLOR_COAST_SAND = np.array([210, 190, 140], dtype=np.uint8)
    COLOR_GRASSLAND = np.array([60, 140, 60], dtype=np.uint8)
    COLOR_FOREST = np.array([25, 85, 35], dtype=np.uint8)
    COLOR_DESERT = np.array([215, 170, 100], dtype=np.uint8)
    COLOR_MOUNTAIN = np.array([110, 110, 110], dtype=np.uint8)
    COLOR_SNOW_ICE = np.array([240, 245, 255], dtype=np.uint8)

    # Ocean rendering
    ocean_mask = ~land_mask
    depth_factor = (sea_level - heightmap) / (sea_level + 1e-6)
    depth_factor = np.clip(depth_factor, 0.0, 1.0)[:, :, np.newaxis]

    ocean_rgb = (COLOR_SHALLOW_WATER * (1 - depth_factor) + COLOR_DEEP_OCEAN * depth_factor).astype(np.uint8)
    surface_texture[ocean_mask] = ocean_rgb[ocean_mask]

    # Land rendering
    land_elevation = (heightmap - sea_level) / (1.0 - sea_level + 1e-6)
    
    # Biome selection
    for r in range(height):
        lat_ratio = abs(lat_y[r])
        for c in range(width):
            if land_mask[r, c]:
                elev = land_elevation[r, c]
                local_temp = temp_map[r, c]

                if local_temp < 265 or lat_ratio > 0.82: # Ice / Polar Cap
                    col = COLOR_SNOW_ICE
                elif elev > 0.68: # High Mountains
                    col = COLOR_SNOW_ICE if elev > 0.85 else COLOR_MOUNTAIN
                elif elev < 0.08: # Beach / Shore line
                    col = COLOR_COAST_SAND
                else:
                    if local_temp > 310 or (hyd_val <= 3 and local_temp > 285):
                        col = COLOR_DESERT
                    elif elev > 0.4:
                        col = COLOR_FOREST
                    else:
                        col = COLOR_GRASSLAND

                surface_texture[r, c] = col

    # Shaded relief shading overlay
    dx = cv2.Sobel(heightmap, cv2.CV_32F, 1, 0, ksize=3)
    dy = cv2.Sobel(heightmap, cv2.CV_32F, 0, 1, ksize=3)
    shade = 1.0 - np.clip((dx * 0.5 + dy * 0.5), -0.4, 0.4)
    shade = shade[:, :, np.newaxis]

    shaded_texture = np.clip(surface_texture * shade, 0, 255).astype(np.uint8)

    return {
        "surface_texture": shaded_texture,
        "heightmap": heightmap,
        "land_mask": land_mask,
        "hydro_fraction": hydro_fraction,
        "sea_level": sea_level,
        "world_name": world.name
    }
