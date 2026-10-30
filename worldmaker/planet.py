"""Planet surface synthesis and photorealistic orbital rendering.

Two products come off one shared model:

* an equirectangular surface texture, which feeds the Traveller polyhedral
  net maps (`planet_projections.render_traveller_icosahedral_net`, or
  `render_dodecahedral_net` below), and
* photorealistic views of the world from orbit, with Lambertian terrain
  shading, a day/night terminator, specular sun-glint on water, a cloud deck
  and Rayleigh-scattered atmospheric limb.

Terrain is generated as 3D noise sampled on the unit sphere rather than as a
flat image, so it is seamless in longitude and free of the pinching that
equirectangular noise produces at the poles. The world's generated
characteristics drive it: hydrographics sets sea level, mean temperature and
axial tilt set the climate bands, tectonic plate count sets the mountain
scale, biomass sets how much vegetation appears, and atmospheric pressure
sets cloud cover and the thickness of the limb.

numpy is required. Pillow is needed only to write PNG files; the render
functions return arrays regardless.
"""
import math
from typing import Any, Dict, Optional, Tuple

import numpy as np

from .utils import Utils

# Terra's profile, the reference an "Earth-like" search is scored against
TERRA = {
    'size': 8, 'atmosphere': 6, 'hydrographics': 7,
    'mean_temperature': 288.0, 'gravity': 1.0,
}


# ---------------------------------------------------------------- noise

class SphereNoise:
    """Value-gradient noise in three dimensions, evaluated on the sphere.

    Sampling 3D noise at points on the unit sphere gives a field that wraps
    seamlessly in longitude and has no polar singularity."""

    def __init__(self, seed: int = 0):
        rng = np.random.default_rng(seed & 0xFFFFFFFF)
        self.perm = rng.permutation(256).astype(np.int32)
        self.perm = np.concatenate([self.perm, self.perm])
        # Unit gradient vectors on the sphere, one per lattice hash
        vectors = rng.normal(size=(256, 3))
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        self.gradients = (vectors / np.maximum(norms, 1e-9)).astype(np.float32)

    def _hash(self, xi, yi, zi):
        p = self.perm
        return p[(p[(p[xi & 255] + (yi & 255)) & 255] + (zi & 255)) & 255]

    def noise(self, x, y, z):
        """Gradient noise at the given coordinates, roughly in [-1, 1]."""
        xi = np.floor(x).astype(np.int32)
        yi = np.floor(y).astype(np.int32)
        zi = np.floor(z).astype(np.int32)
        xf, yf, zf = x - xi, y - yi, z - zi

        # Quintic interpolant: smooth first and second derivatives
        def fade(t):
            return t * t * t * (t * (t * 6 - 15) + 10)

        u, v, w = fade(xf), fade(yf), fade(zf)

        def grad_dot(ox, oy, oz):
            h = self._hash(xi + ox, yi + oy, zi + oz)
            g = self.gradients[h]
            return (g[..., 0] * (xf - ox) + g[..., 1] * (yf - oy)
                    + g[..., 2] * (zf - oz))

        c000, c100 = grad_dot(0, 0, 0), grad_dot(1, 0, 0)
        c010, c110 = grad_dot(0, 1, 0), grad_dot(1, 1, 0)
        c001, c101 = grad_dot(0, 0, 1), grad_dot(1, 0, 1)
        c011, c111 = grad_dot(0, 1, 1), grad_dot(1, 1, 1)

        x00 = c000 + u * (c100 - c000)
        x10 = c010 + u * (c110 - c010)
        x01 = c001 + u * (c101 - c001)
        x11 = c011 + u * (c111 - c011)
        y0 = x00 + v * (x10 - x00)
        y1 = x01 + v * (x11 - x01)
        return y0 + w * (y1 - y0)

    def fbm(self, x, y, z, octaves: int = 6, lacunarity: float = 2.0,
            gain: float = 0.5, ridged: bool = False):
        """Fractal sum of noise octaves; `ridged` sharpens ridge lines.

        The plain sum stays in [-1, 1] around zero and the ridged sum in
        [0, 1]; callers rescale to whatever range they need."""
        total = np.zeros_like(x, dtype=np.float32)
        amplitude, frequency, norm = 1.0, 1.0, 0.0
        for _ in range(octaves):
            sample = self.noise(x * frequency, y * frequency, z * frequency)
            if ridged:
                sample = 1.0 - np.abs(sample)
                sample = sample * sample
            total += sample * amplitude
            norm += amplitude
            amplitude *= gain
            frequency *= lacunarity
        return total / max(norm, 1e-9)


def _sphere_grid(width: int, height: int):
    """Unit-sphere coordinates for every pixel of an equirectangular image."""
    lon = (np.arange(width, dtype=np.float32) + 0.5) / width * 2 * np.pi - np.pi
    lat = np.pi / 2 - (np.arange(height, dtype=np.float32) + 0.5) / height * np.pi
    lon_grid, lat_grid = np.meshgrid(lon, lat)
    cos_lat = np.cos(lat_grid)
    x = cos_lat * np.cos(lon_grid)
    y = cos_lat * np.sin(lon_grid)
    z = np.sin(lat_grid)
    return x, y, z, lat_grid, lon_grid


# ------------------------------------------------- Earth-like selection

def _world_label(world: Any) -> str:
    """A usable name for a world.

    Moons carry a designation rather than a name - and a moon can perfectly
    well be the most Earth-like body in a system - so fall back to that
    before giving up on an anonymous "World"."""
    for attribute in ('name', 'designation'):
        value = getattr(world, attribute, None)
        if value:
            return str(value)
    return 'World'


def earthlike_score(world: Any) -> float:
    """How closely a world resembles Terra, from 0 (nothing alike) to 1.

    The book's own shorthand for the ideal is a habitability rating of A+,
    a "Terra-equivalent garden world" (WBH p.133); this scores the underlying
    characteristics so worlds can be ranked rather than merely classified."""
    uwp = getattr(world, 'uwp', None)
    if uwp is None:
        return 0.0

    size = Utils.from_eHex(getattr(world, 'size_code', None) or uwp.size)
    atm = Utils.from_eHex(getattr(world, 'atmosphere_code', None) or uwp.atmosphere)
    hyd = Utils.from_eHex(getattr(world, 'hydrographics_code', None) or uwp.hydrographics)
    temp = getattr(world, 'mean_temperature', 0.0) or 0.0
    gravity = getattr(world, 'gravity', 0.0) or 0.0

    # A breathable atmosphere is non-negotiable: without one the world is
    # not Terra-like at all, however closely the rest of it matches.
    if atm not in (5, 6, 7, 8):
        return 0.0
    atm_score = 1.0 - abs(atm - TERRA['atmosphere']) * 0.25

    size_score = max(0.0, 1.0 - abs(size - TERRA['size']) / 6.0)
    hyd_score = max(0.0, 1.0 - abs(hyd - TERRA['hydrographics']) / 7.0)

    if temp <= 0:
        temp_score = 0.0
    else:
        temp_score = max(0.0, 1.0 - abs(temp - TERRA['mean_temperature']) / 60.0)

    if gravity <= 0:
        gravity_score = 0.5
    else:
        gravity_score = max(0.0, 1.0 - abs(gravity - TERRA['gravity']) / 0.8)

    habitability = getattr(world, 'habitability_rating', 0) / 12.0
    biosphere = min(1.0, (getattr(world, 'biomass_rating', 0) or 0) / 10.0)

    # Atmosphere and temperature dominate: without them nothing else matters
    return round(
        atm_score * 0.28 + temp_score * 0.22 + hyd_score * 0.15
        + size_score * 0.10 + gravity_score * 0.10
        + habitability * 0.10 + biosphere * 0.05, 4)


def find_earthlike_candidate(sector: Any, top: int = 1, profile: Any = None,
                             pool: int = 40):
    """Finds the most Terra-like world in a sector.

    The search itself belongs to `findworld`, which applies the hard filters
    a candidate has to survive - in the habitable zone of an F, G or K star,
    outside Zhodani space, warm enough for liquid water. This ranks the
    survivors by physical resemblance to Terra, which is what the renderer
    cares about: `findworld`'s own ranking also weighs population,
    government and law, and a world can be the right size, air and water
    while having none of those.

    Pass `profile` to search for something other than Erith. Returns
    `(hex, world, score)` for the best candidate, or a list of such tuples
    when `top` > 1."""
    from .findworld import ERITH, find_worlds

    matches = find_worlds(sector, profile or ERITH, limit=max(pool, top))
    scored = [(match.hex, match.body, earthlike_score(match.body))
              for match in matches]
    scored = [entry for entry in scored if entry[2] > 0]
    scored.sort(key=lambda item: (-item[2], item[0]))

    if not scored:
        return None if top == 1 else []
    return scored[0] if top == 1 else scored[:top]


# ------------------------------------------------------ surface synthesis

def generate_planet_surface(world: Any, width: int = 2048, height: int = 1024,
                            seed: Optional[int] = None) -> Dict[str, Any]:
    """Builds the full surface model for a world.

    Returns a dict carrying the equirectangular `surface_texture` (H, W, 3
    uint8) plus the fields the renderers need: elevation, land mask, sea
    level, ice, clouds, specular mask and surface normals. The keys used by
    `planet_projections` are present, so the same texture drives the
    Traveller net maps."""
    label = _world_label(world)
    if seed is None:
        seed = abs(hash(label)) % (2 ** 31)

    uwp = getattr(world, 'uwp', None)
    hyd = Utils.from_eHex(getattr(world, 'hydrographics_code', None)
                          or (uwp.hydrographics if uwp else 7))
    atm = Utils.from_eHex(getattr(world, 'atmosphere_code', None)
                          or (uwp.atmosphere if uwp else 6))
    size = Utils.from_eHex(getattr(world, 'size_code', None)
                           or (uwp.size if uwp else 8))
    mean_temp = getattr(world, 'mean_temperature', 0.0) or 288.0
    tilt = getattr(world, 'axial_tilt', 23.5) or 23.5
    plates = getattr(world, 'tectonic_plates', 8) or 8
    biomass = getattr(world, 'biomass_rating', 0) or 0
    pressure = getattr(world, 'atmos_pressure_bar', 0.0) or (1.0 if atm >= 4 else 0.0)

    noise = SphereNoise(seed)
    x, y, z, lat, lon = _sphere_grid(width, height)

    # --- elevation ------------------------------------------------------
    # Continent scale follows plate count: few plates, few large landmasses.
    continent_freq = max(1.2, min(4.0, plates * 0.35))
    continents = noise.fbm(x * continent_freq, y * continent_freq,
                           z * continent_freq, octaves=4, gain=0.55)

    detail = noise.fbm(x * continent_freq * 4 + 11.7,
                       y * continent_freq * 4 + 5.3,
                       z * continent_freq * 4 + 19.1, octaves=5, gain=0.5)

    # Ridged noise makes mountain chains rather than random bumps
    ridges = noise.fbm(x * continent_freq * 2.2 + 41.0,
                       y * continent_freq * 2.2 + 7.0,
                       z * continent_freq * 2.2 + 3.0,
                       octaves=5, gain=0.55, ridged=True)

    elevation = continents + detail * 0.28 + (ridges - 0.5) * 0.35
    elevation = (elevation - elevation.min()) / max(1e-9, np.ptp(elevation))

    # --- sea level ------------------------------------------------------
    # Hydrographics is a percentage of the surface under liquid, so the sea
    # level is simply that percentile of the elevation field.
    water_fraction = float(np.clip(hyd / 10.0, 0.0, 1.0))
    if water_fraction <= 0.0:
        sea_level = -1.0
    elif water_fraction >= 1.0:
        sea_level = 2.0
    else:
        sea_level = float(np.quantile(elevation, water_fraction))

    land_mask = elevation > sea_level
    ocean_depth = np.clip((sea_level - elevation) / max(1e-6, sea_level), 0, 1)
    land_height = np.clip((elevation - sea_level) / max(1e-6, 1 - sea_level), 0, 1)

    # --- climate --------------------------------------------------------
    # Latitude drives the temperature band. The profile is tuned so a world
    # with Terra's mean of 288K reads about 302K at the equator and 240K at
    # the poles, matching the real distribution; axial tilt widens the warm
    # belt at the expense of the caps.
    tropic_width = np.clip(abs(tilt) / 90.0, 0.05, 0.9)
    equator_bonus = 14.0 + 6.0 * tropic_width
    pole_penalty = 62.0 + 20.0 * (1.0 - tropic_width)
    temperature = (mean_temp + equator_bonus
                   - pole_penalty * np.sin(lat) ** 2
                   - land_height * 30.0)          # lapse rate with altitude

    moisture = noise.fbm(x * 2.4 + 60.0, y * 2.4 + 21.0, z * 2.4 + 88.0,
                         octaves=4, gain=0.5)
    moisture = (moisture - moisture.min()) / max(1e-9, np.ptp(moisture))
    # Coastal land is wetter than continental interiors
    moisture = np.clip(moisture * 0.65 + (1.0 - land_height) * 0.35, 0, 1)
    if water_fraction < 0.15:
        moisture *= 0.35            # a dry world stays dry

    ice = (temperature < 268.0) & (atm > 0)
    permanent_ice = temperature < 250.0

    # --- colouring ------------------------------------------------------
    texture = np.zeros((height, width, 3), dtype=np.float32)

    if atm == 0 or biomass == 0 and water_fraction < 0.05:
        # Airless or dead rock: greys and dust, cratered rather than green
        base = np.stack([0.42 + elevation * 0.22,
                         0.40 + elevation * 0.20,
                         0.38 + elevation * 0.19], axis=-1)
        texture = base
    else:
        deep = np.array([0.031, 0.098, 0.235], dtype=np.float32)
        shallow = np.array([0.106, 0.361, 0.545], dtype=np.float32)
        sand = np.array([0.784, 0.714, 0.525], dtype=np.float32)
        grass = np.array([0.243, 0.478, 0.208], dtype=np.float32)
        forest = np.array([0.106, 0.290, 0.129], dtype=np.float32)
        desert = np.array([0.800, 0.639, 0.376], dtype=np.float32)
        tundra = np.array([0.529, 0.549, 0.463], dtype=np.float32)
        rock = np.array([0.412, 0.396, 0.376], dtype=np.float32)
        snow = np.array([0.945, 0.961, 0.980], dtype=np.float32)

        # Ocean: depth-graded blue
        depth_t = ocean_depth[..., None]
        texture = shallow + (deep - shallow) * depth_t

        # Land: moisture and temperature choose the biome
        veg_strength = np.clip(biomass / 8.0, 0.0, 1.0)
        # Biomes turn temperate a little above freezing rather than easing
        # in across the whole thermal range - otherwise a garden world's
        # mid latitudes come out tundra-grey.
        warm = np.clip((temperature - 265.0) / 26.0, 0, 1)[..., None]
        wet = moisture[..., None]

        arid = desert + (sand - desert) * 0.35
        vegetated = grass + (forest - grass) * np.clip(wet * 1.3, 0, 1)
        living = arid + (vegetated - arid) * np.clip(wet * veg_strength * 1.6, 0, 1)
        cold_land = tundra + (rock - tundra) * 0.4
        land_colour = cold_land + (living - cold_land) * warm

        # Shorelines, then bare rock on the high peaks
        shore = np.clip(1.0 - land_height / 0.035, 0, 1)[..., None]
        land_colour = land_colour + (sand - land_colour) * shore * 0.65
        alpine = np.clip((land_height - 0.55) / 0.45, 0, 1)[..., None]
        land_colour = land_colour + (rock - land_colour) * alpine

        # Blend across the waterline rather than switching at it. A hard
        # step aliases into visible stair-stepping once the texture is
        # magnified onto the globe, and a real shoreline has a surf zone.
        coast = np.clip((elevation - sea_level) / 0.006, 0, 1)[..., None]
        texture = texture + (land_colour - texture) * coast

        # Ice: caps and pack ice, softened at the margin
        ice_t = np.clip((268.0 - temperature) / 16.0, 0, 1)[..., None]
        texture = texture + (snow - texture) * ice_t * 0.92
        texture = np.where(permanent_ice[..., None],
                           snow[None, None, :] * np.ones_like(texture), texture)

    texture = np.clip(texture, 0, 1)

    # --- clouds ---------------------------------------------------------
    # Banded by latitude the way a rotating atmosphere organises them, and
    # thicker where the surface is wet.
    cloud_cover = 0.0
    clouds = np.zeros((height, width), dtype=np.float32)
    if pressure > 0.05 and atm >= 2:
        bands = np.sin(lat * 3.0) * 0.5 + 0.5
        cloud_noise = noise.fbm(x * 3.1 + 200.0, y * 3.1 + 91.0, z * 3.1 + 55.0,
                                octaves=5, gain=0.55)
        cloud_noise = (cloud_noise - cloud_noise.min()) / max(1e-9, np.ptp(cloud_noise))
        clouds = cloud_noise * (0.55 + 0.45 * bands)
        clouds = clouds * np.clip(0.35 + moisture * 0.9, 0, 1.4)
        # More atmosphere, more cloud
        cover_target = np.clip(0.25 + pressure * 0.28, 0.1, 0.85)
        threshold = float(np.quantile(clouds, 1.0 - cover_target))
        clouds = np.clip((clouds - threshold) / max(1e-6, clouds.max() - threshold), 0, 1)
        clouds = clouds ** 1.3
        cloud_cover = float(clouds.mean())

    # --- surface normals, for relief shading ----------------------------
    dzdx = np.gradient(elevation, axis=1)
    dzdy = np.gradient(elevation, axis=0)
    relief_scale = 28.0 * max(0.4, size / 8.0)
    normals = np.stack([-dzdx * relief_scale, -dzdy * relief_scale,
                        np.ones_like(elevation)], axis=-1)
    normals /= np.linalg.norm(normals, axis=-1, keepdims=True)

    # A little relief shading baked into the texture, so the flat net maps
    # read as terrain rather than as colour fields
    relief = np.clip(0.5 + (normals[..., 0] * 0.6 + normals[..., 1] * 0.5), 0.55, 1.35)
    shaded = np.clip(texture * relief[..., None], 0, 1)

    return {
        'world_name': label,
        'surface_texture': (shaded * 255).astype(np.uint8),
        'albedo': texture,
        'heightmap': elevation,
        'land_mask': land_mask,
        'sea_level': sea_level,
        'hydro_fraction': water_fraction,
        'temperature_map': temperature,
        'moisture_map': moisture,
        'ice_mask': ice,
        'clouds': clouds,
        'cloud_cover': cloud_cover,
        'normals': normals,
        'width': width,
        'height': height,
        'seed': seed,
    }


# ------------------------------------------------- orbital rendering

def _sample_equirect(field: np.ndarray, lat: np.ndarray, lon: np.ndarray):
    """Bilinear sample of an equirectangular field at given lat/lon."""
    h, w = field.shape[0], field.shape[1]
    u = (lon + np.pi) / (2 * np.pi) * w - 0.5
    v = (np.pi / 2 - lat) / np.pi * h - 0.5

    u0 = np.floor(u).astype(np.int32)
    v0 = np.floor(v).astype(np.int32)
    fu = (u - u0)[..., None] if field.ndim == 3 else (u - u0)
    fv = (v - v0)[..., None] if field.ndim == 3 else (v - v0)

    u0m, u1m = u0 % w, (u0 + 1) % w
    v0m = np.clip(v0, 0, h - 1)
    v1m = np.clip(v0 + 1, 0, h - 1)

    c00 = field[v0m, u0m]
    c10 = field[v0m, u1m]
    c01 = field[v1m, u0m]
    c11 = field[v1m, u1m]
    top = c00 + (c10 - c00) * fu
    bottom = c01 + (c11 - c01) * fu
    return top + (bottom - top) * fv


def render_orbital_view(surface: Dict[str, Any], size: int = 1024,
                        sub_observer: Tuple[float, float] = (18.0, 0.0),
                        sun_direction: Tuple[float, float] = (25.0, -35.0),
                        altitude_radii: float = 3.2,
                        show_clouds: bool = True,
                        show_atmosphere: bool = True,
                        city_lights: bool = True,
                        population: int = 0,
                        starfield: bool = True,
                        exposure: float = 1.0) -> np.ndarray:
    """Renders the world as seen from orbit.

    `sub_observer` is the (latitude, longitude) beneath the camera and
    `sun_direction` the (latitude, longitude) beneath the sun, both in
    degrees. `altitude_radii` is the camera distance in planetary radii, so
    smaller values give a closer, more curved horizon.

    Returns an (size, size, 3) uint8 array."""
    albedo = surface['albedo']
    land_mask = surface['land_mask']
    normals = surface['normals']
    clouds = surface.get('clouds')
    ice_mask = surface.get('ice_mask')

    # Camera ray directions across the image plane.
    #
    # With the camera at distance d from the centre of a unit sphere, the
    # limb sits where a ray grazes the surface: tan(theta_max) = 1/sqrt(d^2-1).
    # The frame is scaled so the disc fills a fixed fraction of it, which
    # keeps framing stable as the altitude changes.
    d = max(1.05, altitude_radii)
    edge_tan = 1.0 / math.sqrt(d * d - 1.0)
    disc_fraction = 0.74
    span = edge_tan / disc_fraction

    coords = np.linspace(-1.0, 1.0, size, dtype=np.float32)
    px, py = np.meshgrid(coords, -coords)
    # Perspective: solve where each ray meets the unit sphere
    ray_x = px * span
    ray_y = py * span
    ray_z = np.full_like(ray_x, -1.0)
    norm = np.sqrt(ray_x ** 2 + ray_y ** 2 + ray_z ** 2)
    ray_x, ray_y, ray_z = ray_x / norm, ray_y / norm, ray_z / norm

    # Camera sits at (0, 0, d) looking toward the origin
    b = 2.0 * (d * ray_z)
    c = d * d - 1.0
    disc = b * b - 4.0 * c
    hit = disc >= 0.0

    sqrt_disc = np.sqrt(np.maximum(disc, 0.0))
    t = (-b - sqrt_disc) / 2.0

    # Surface point in camera space, then its normal
    sx = ray_x * t
    sy = ray_y * t
    sz = d + ray_z * t
    n = np.stack([sx, sy, sz], axis=-1)
    n_len = np.linalg.norm(n, axis=-1, keepdims=True)
    n = n / np.maximum(n_len, 1e-9)

    # Rotate the sphere so the requested sub-observer point faces the camera
    obs_lat = math.radians(sub_observer[0])
    obs_lon = math.radians(sub_observer[1])

    cos_p, sin_p = math.cos(-obs_lat), math.sin(-obs_lat)
    nx, ny, nz = n[..., 0], n[..., 1], n[..., 2]
    ny2 = ny * cos_p - nz * sin_p
    nz2 = ny * sin_p + nz * cos_p

    lat = np.arcsin(np.clip(ny2, -1, 1))
    lon = np.arctan2(nx, nz2) + obs_lon
    lon = (lon + np.pi) % (2 * np.pi) - np.pi

    # Sun direction as a vector in the same camera space
    sun_lat = math.radians(sun_direction[0])
    sun_lon = math.radians(sun_direction[1] - sub_observer[1])
    sun = np.array([
        math.cos(sun_lat) * math.sin(sun_lon),
        math.sin(sun_lat) * math.cos(obs_lat) - math.cos(sun_lat) * math.cos(sun_lon) * math.sin(obs_lat),
        math.cos(sun_lat) * math.cos(sun_lon) * math.cos(obs_lat) + math.sin(sun_lat) * math.sin(obs_lat),
    ], dtype=np.float32)
    sun /= max(1e-9, np.linalg.norm(sun))

    # --- surface shading ------------------------------------------------
    base = _sample_equirect(albedo, lat, lon)
    land = _sample_equirect(land_mask.astype(np.float32), lat, lon)
    surf_n = _sample_equirect(normals, lat, lon)

    # Perturb the sphere normal by the terrain normal for relief
    relief = np.stack([n[..., 0], n[..., 1], n[..., 2]], axis=-1)
    relief = relief + surf_n * 0.16
    relief /= np.maximum(np.linalg.norm(relief, axis=-1, keepdims=True), 1e-9)

    lambert = np.clip(
        relief[..., 0] * sun[0] + relief[..., 1] * sun[1] + relief[..., 2] * sun[2],
        -1, 1)

    # Soften the terminator: real ones are gradual, not a hard edge
    day = np.clip((lambert + 0.06) / 0.30, 0.0, 1.0)
    diffuse = np.clip(lambert, 0.0, 1.0) ** 0.85

    colour = base * (0.012 + 0.988 * diffuse[..., None])

    # --- specular sun-glint on water ------------------------------------
    view = np.stack([-ray_x, -ray_y, -ray_z], axis=-1)
    half = sun[None, None, :] + view
    half /= np.maximum(np.linalg.norm(half, axis=-1, keepdims=True), 1e-9)
    spec_angle = np.clip((n * half).sum(axis=-1), 0, 1)
    water = np.clip(1.0 - land, 0, 1)
    ice_here = _sample_equirect(ice_mask.astype(np.float32), lat, lon) if ice_mask is not None else 0.0
    glint = (spec_angle ** 260.0) * water * (1.0 - ice_here * 0.85) * day
    colour += glint[..., None] * np.array([1.0, 0.97, 0.88], dtype=np.float32) * 0.55

    # --- clouds ---------------------------------------------------------
    if show_clouds and clouds is not None and clouds.max() > 0:
        # The deck sits above the surface, so it is offset slightly and lit
        # a touch more brightly than the ground
        cloud_alpha = _sample_equirect(clouds, lat, lon * 1.0 + 0.02)
        cloud_alpha = np.clip(cloud_alpha, 0, 1)
        cloud_lit = (0.025 + 0.975 * np.clip(lambert, 0, 1) ** 0.7)
        cloud_rgb = np.array([1.0, 1.0, 0.99], dtype=np.float32) * cloud_lit[..., None]
        a = (cloud_alpha * 0.80)[..., None]
        colour = colour * (1 - a) + cloud_rgb * a

    # --- night side -----------------------------------------------------
    night = 1.0 - day
    if city_lights and population >= 5:
        # Lights cluster on land, and only where there are people to build them
        density = np.clip((population - 4) / 6.0, 0, 1)
        light_noise = _sample_equirect(surface['moisture_map'], lat, lon)
        lights = (light_noise > (1.0 - 0.22 * density)) * land
        glow = lights * night * density
        colour += glow[..., None] * np.array([1.0, 0.82, 0.52], dtype=np.float32) * 0.55

    # A dim ambient so the night side is not pure black
    colour += night[..., None] * base * 0.012

    # --- atmosphere -----------------------------------------------------
    image = np.zeros((size, size, 3), dtype=np.float32)

    if starfield:
        rng = np.random.default_rng(surface.get('seed', 0) ^ 0x5EED)
        star_field = rng.random((size, size))
        stars = np.clip((star_field - 0.9992) * 900, 0, 1)
        twinkle = rng.random((size, size)) * 0.5 + 0.5
        image += (stars * twinkle)[..., None] * np.array([0.9, 0.93, 1.0],
                                                          dtype=np.float32)

    if show_atmosphere:
        atmos_thickness = float(np.clip(
            surface.get('cloud_cover', 0.3) * 0.5 + 0.35, 0.15, 0.9))
        # Rim brightening: grazing angles look through more air
        facing = np.clip((n * np.stack([-ray_x, -ray_y, -ray_z], axis=-1)
                          ).sum(axis=-1), 0, 1)
        # Confined to a narrow band at the limb: a shallow falloff washes
        # the whole sunward third of the disc out to white.
        rim = np.clip(1.0 - facing, 0, 1) ** 3.6
        sky = np.array([0.32, 0.53, 0.92], dtype=np.float32)
        colour = colour + rim[..., None] * sky * day[..., None] * atmos_thickness * 0.9

        # Halo just beyond the limb, where the atmosphere is seen edge-on.
        # Distance is measured against the true limb radius, so the glow is a
        # thin shell hugging the disc rather than a wash across the frame.
        radial = np.sqrt(px ** 2 + py ** 2) * span
        shell = (0.035 + 0.045 * atmos_thickness) * edge_tan
        limb = np.clip((radial - edge_tan) / max(shell, 1e-6), 0, 8)
        halo = np.exp(-limb * 1.8) * (~hit)

        # Brightest on the sunward side of the disc
        sun_side = np.clip(
            (px * sun[0] + py * sun[1]) / np.maximum(
                np.sqrt(px ** 2 + py ** 2), 1e-6) * 1.05 + 0.12, 0, 1)
        image += (halo * sun_side)[..., None] * sky * atmos_thickness * 2.2

    image = np.where(hit[..., None], colour, image)

    # Exposure and a gentle filmic roll-off, so highlights do not clip flat
    image = image * exposure
    image = image / (1.0 + image * 0.55)
    image = np.clip(image, 0, 1) ** (1 / 2.2)

    return (image * 255).astype(np.uint8)


def render_orbital_sequence(surface: Dict[str, Any], frames: int = 4,
                            size: int = 512, **kwargs):
    """Renders several views around the world, one per equal step of
    longitude - useful for a contact sheet or an animation."""
    views = []
    for i in range(frames):
        lon = -180.0 + 360.0 * i / frames
        views.append(render_orbital_view(
            surface, size=size, sub_observer=(kwargs.pop('lat', 15.0), lon)
            if False else (kwargs.get('lat', 15.0), lon),
            **{k: v for k, v in kwargs.items() if k != 'lat'}))
    return views


# ------------------------------------------------- polyhedral net maps

# Rotation of the two hub pentagons in the printed net. The ring faces sit
# on the hub's edge normals, half a face further round.
_NET_HUB_ROTATION = 36.0

# Gnomonic scale: page distance in face radii -> tangent-plane distance, so
# that a face projected from the centre of the sphere covers exactly its own
# pentagon and no more. An edge midpoint sits halfway between two adjacent
# face centres, which subtend arccos(1/sqrt(5)); the face's circumradius is
# that apothem over cos(36 degrees). Fudging this factor is what leaves
# terrain jumping across the fold lines.
_NET_GNOMONIC_SCALE = (math.tan(math.acos(1.0 / math.sqrt(5.0)) / 2.0)
                       / math.cos(math.pi / 5))


def _rotate_about(axis: np.ndarray, vector: np.ndarray, degrees: float):
    """Rodrigues rotation of `vector` about a unit `axis`."""
    theta = math.radians(degrees)
    cos_t, sin_t = math.cos(theta), math.sin(theta)
    return (vector * cos_t + np.cross(axis, vector) * sin_t
            + axis * float(np.dot(axis, vector)) * (1.0 - cos_t))


def _face_frame(centre: np.ndarray, reference: np.ndarray = None,
                azimuth: float = 0.0):
    """An (east, north) basis for the tangent plane at a face centre.

    With no `reference` the basis is anchored to the world's polar axis.
    Given one, the basis is turned so that tangent direction sits at
    `azimuth` degrees - which is how each face of the net is aligned to its
    neighbours."""
    if reference is None:
        up = np.array([0.0, 0.0, 1.0])
        if abs(float(np.dot(centre, up))) > 0.95:
            up = np.array([0.0, 1.0, 0.0])
        east = np.cross(up, centre)
    else:
        tangent = reference - centre * float(np.dot(reference, centre))
        east = _rotate_about(centre, tangent, -azimuth)
    east = east / np.linalg.norm(east)
    return east, np.cross(centre, east)


# The dual of an icosahedron: a dodecahedron's face centres are the
# icosahedron's twelve vertices, (0, +-1, +-phi) and its cyclic rotations.
def _dodecahedron_vertices():
    phi = (1 + math.sqrt(5)) / 2
    raw = []
    for s1 in (1, -1):
        for s2 in (1, -1):
            raw.append((0.0, s1 * 1.0, s2 * phi))
            raw.append((s1 * 1.0, s2 * phi, 0.0))
            raw.append((s1 * phi, 0.0, s2 * 1.0))
    return [np.array(c) / np.linalg.norm(c) for c in raw]


def _net_faces(face_radius: float, gap: float = 2.6):
    """Lays out the twelve faces of the printed dodecahedral net.

    Each entry is `(centre, east, north, x, y, rotation)`: where the face
    sits on the sphere, the tangent basis its texture is sampled in, and
    where it is drawn on the page.

    The net is two hemispheres, each a hub pentagon with its five true
    neighbours folded off its edges. Every face's tangent basis is pinned
    to the direction of the fold it shares, rather than to the world's
    polar axis, so terrain runs continuously across each fold line - which
    is what makes the printed sheet actually fold into the world."""
    points = _dodecahedron_vertices()
    adjacent_cos = 1.0 / math.sqrt(5.0)

    def neighbours_of(index):
        return [j for j, q in enumerate(points)
                if j != index
                and abs(float(np.dot(points[index], q)) - adjacent_cos) < 1e-6]

    hub_indices = [0, min(range(len(points)),
                          key=lambda j: float(np.dot(points[0], points[j])))]

    radius = face_radius
    ring_distance = 2.0 * radius * math.cos(math.pi / 5)
    theta = _NET_HUB_ROTATION
    faces = []

    for half, hub in enumerate(hub_indices):
        origin_x = half * (ring_distance * 2.0 + radius * gap)
        centre = points[hub]

        # Wind the neighbours counter-clockwise from an arbitrary first one,
        # measured in the hub's own tangent plane.
        ring = neighbours_of(hub)
        seed_east, seed_north = _face_frame(centre, reference=points[ring[0]])
        ring.sort(key=lambda j: math.atan2(
            float(np.dot(points[j], seed_north)),
            float(np.dot(points[j], seed_east))) % (2 * math.pi))

        # Ring face i is drawn on the hub's i-th edge normal. The sampler
        # turns face coordinates by the face's rotation before projecting,
        # so a screen angle A shows up at tangent azimuth A + rotation.
        screen = [theta - 90.0 + 36.0 + 72.0 * i for i in range(5)]
        east, north = _face_frame(centre, reference=points[ring[0]],
                                  azimuth=screen[0] + theta)
        faces.append((centre, east, north, origin_x, 0.0, theta))

        for i, j in enumerate(ring):
            angle = math.radians(screen[i])
            x = origin_x + ring_distance * math.cos(angle)
            y = ring_distance * math.sin(angle)
            # Seen from the ring face, the hub lies back the way we came.
            ring_rotation = theta + 36.0
            back = screen[i] + 180.0 + ring_rotation
            r_east, r_north = _face_frame(points[j], reference=centre,
                                          azimuth=back)
            faces.append((points[j], r_east, r_north, x, y, ring_rotation))

    return faces


def _dodecahedron_face_centres():
    """The twelve face centres, in the order the net draws them."""
    return [tuple(face[0]) for face in _net_faces(1.0)]


def render_dodecahedral_net(surface: Dict[str, Any], face_radius: float = 120.0,
                            name: str = None, samples: int = 26) -> str:
    """Renders the world as a flattened dodecahedral net.

    Note that the Traveller standard, and the World Builder's Handbook
    (p.135), uses a twenty-triangle *icosahedral* net - use
    `render_icosahedral_net_svg` for that. This twelve-pentagon net is
    offered because a dodecahedron gives larger, less distorted faces.

    The net is the usual two halves: a hub pentagon ringed by the five
    faces that really adjoin it on the sphere. Two pentagons sharing a fold
    have their centres 2 x apothem apart, with the neighbour turned half a
    face against the hub."""
    name = name or surface.get('world_name', 'World')
    albedo = surface['albedo']

    r = face_radius
    faces = _net_faces(r)
    positions = [(x, y, rotation) for _, _, _, x, y, rotation in faces]

    xs = [p[0] for p in positions]
    ys = [p[1] for p in positions]
    pad = r * 1.4
    min_x, max_x = min(xs) - pad, max(xs) + pad
    min_y, max_y = min(ys) - pad, max(ys) + pad
    width = max_x - min_x
    top = min_y - 96
    height = (max_y - min_y) + 96 + 40

    style = (
        "<style>\n"
        "    .dn-bg { fill: #fdfcf8; }\n"
        "    .dn-face { stroke: #222; stroke-width: 1.4; fill: none; }\n"
        "    .dn-title { font-family: Helvetica, Arial, sans-serif;"
        " font-weight: bold; fill: #000; }\n"
        "    .dn-sub { font-family: Helvetica, Arial, sans-serif; fill: #444; }\n"
        "</style>"
    )

    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" '
           f'viewBox="{min_x:.0f} {top:.0f} {width:.0f} {height:.0f}" '
           f'width="100%" height="100%">']
    svg.append(style)
    svg.append(f'<rect x="{min_x:.0f}" y="{top:.0f}" width="{width:.0f}" '
               f'height="{height:.0f}" class="dn-bg" />')
    svg.append(f'<text x="{min_x + 18:.0f}" y="{top + 40:.0f}" class="dn-title" '
               f'font-size="26">{name.upper()}</text>')
    svg.append(f'<text x="{min_x + 18:.0f}" y="{top + 64:.0f}" class="dn-sub" '
               f'font-size="12">Dodecahedral surface net &#183; '
               f'12 pentagonal faces</text>')

    # Clip paths keep every sampled patch inside its own face
    svg.append('<defs>')
    for index, (cx, cy, rot) in enumerate(positions):
        outline = " ".join(f"{x:.2f},{y:.2f}"
                           for x, y in _pentagon_points(cx, cy, r, rot))
        svg.append(f'<clipPath id="dnface{index}">'
                   f'<polygon points="{outline}" /></clipPath>')
    svg.append('</defs>')

    patch = 2.0 * r / samples
    bleed = patch * 1.06
    for index, (centre, east, north, cx, cy, rot) in enumerate(faces):
        theta = math.radians(rot)
        cos_t, sin_t = math.cos(theta), math.sin(theta)

        # crispEdges suppresses the pale antialiasing seam that otherwise
        # shows between every pair of abutting patches.
        svg.append(f'<g clip-path="url(#dnface{index})" '
                   f'shape-rendering="crispEdges">')
        for i in range(samples):
            for j in range(samples):
                u = (i + 0.5) / samples * 2 - 1
                v = (j + 0.5) / samples * 2 - 1
                # The pentagon reaches the full circumradius at its
                # vertices, so cull only the square's far corners; the
                # clip path trims whatever else falls outside.
                if u * u + v * v > 2.05:
                    continue
                ur = u * cos_t - v * sin_t
                vr = u * sin_t + v * cos_t
                # Gnomonic projection of the face plane onto the sphere
                scale = _NET_GNOMONIC_SCALE
                p = centre + east * (ur * scale) + north * (vr * scale)
                p = p / np.linalg.norm(p)
                lat = np.array([[math.asin(float(np.clip(p[2], -1, 1)))]],
                               dtype=np.float32)
                lon = np.array([[math.atan2(float(p[1]), float(p[0]))]],
                               dtype=np.float32)
                colour = _sample_equirect(albedo, lat, lon)[0, 0]
                rgb = tuple(int(round(float(c) * 255)) for c in colour)
                # Patches overlap by a hair: abutting edges otherwise show
                # up as a grid of pale antialiasing seams.
                svg.append(
                    f'<rect x="{cx + u * r - bleed / 2:.2f}" '
                    f'y="{cy + v * r - bleed / 2:.2f}" '
                    f'width="{bleed:.2f}" height="{bleed:.2f}" '
                    f'fill="rgb{rgb}" />')
        svg.append('</g>')

        outline = " ".join(f"{x:.2f},{y:.2f}"
                           for x, y in _pentagon_points(cx, cy, r, rot))
        svg.append(f'<polygon points="{outline}" class="dn-face" />')

    svg.append('</svg>')
    return "\n".join(svg)


def _pentagon_points(cx: float, cy: float, r: float, rotation_deg: float):
    """The five vertices of a regular pentagon."""
    return [(cx + r * math.cos(math.radians(rotation_deg - 90 + k * 72)),
             cy + r * math.sin(math.radians(rotation_deg - 90 + k * 72)))
            for k in range(5)]


def render_icosahedral_net_svg(surface: Dict[str, Any], face_size: float = 150.0,
                               name: str = None) -> str:
    """Renders the Traveller-standard twenty-triangle icosahedral net
    (WBH p.135) from the surface texture, as SVG.

    `planet_projections.render_traveller_icosahedral_net` produces the same
    net as a raster image and needs OpenCV; this one needs only numpy."""
    from .worldmap import render_world_map_svg, TERRAIN

    # Classify the surface into the terrain vocabulary the net renderer uses
    terrain = classify_surface_terrain(surface)
    name = name or surface.get('world_name', 'World')

    class _Shim:
        pass

    shim = _Shim()
    shim.name = name
    shim.uwp = surface.get('uwp', '')
    return render_world_map_svg(shim, terrain, name=name)


def icosahedron_faces():
    """The twenty faces of the Traveller map icosahedron, as unit vectors.

    Ordered to match `worldmap.render_world_map_svg`: faces 0-4 are the north
    cap, 5-14 the equatorial band alternating up and down, 15-19 the south
    cap."""
    alpha = math.asin(1.0 / math.sqrt(5.0))
    north = np.array([0.0, 0.0, 1.0])
    south = np.array([0.0, 0.0, -1.0])

    upper, lower = [], []
    for k in range(5):
        theta = k * 2 * math.pi / 5
        upper.append(np.array([math.cos(theta) * math.cos(alpha),
                               math.sin(theta) * math.cos(alpha),
                               math.sin(alpha)]))
        theta2 = (k + 0.5) * 2 * math.pi / 5
        lower.append(np.array([math.cos(theta2) * math.cos(alpha),
                               math.sin(theta2) * math.cos(alpha),
                               -math.sin(alpha)]))

    faces = []
    for k in range(5):                                    # north cap
        faces.append((north, upper[k], upper[(k + 1) % 5]))
    for k in range(5):                                    # equatorial band
        faces.append((upper[k], lower[k], upper[(k + 1) % 5]))
        faces.append((lower[k], lower[(k + 1) % 5], upper[(k + 1) % 5]))
    for k in range(5):                                    # south cap
        faces.append((south, lower[(k + 1) % 5], lower[k]))
    return faces


def _subtriangle_barycentres(hexes_per_edge: int):
    """Barycentric centroids of the sub-triangles, in the same order that
    `worldmap._face_cells` emits them."""
    n = hexes_per_edge
    centres = []

    def bary(t_row, t_col):
        """Barycentric weights of the lattice point at (t_row, t_col)."""
        if t_row == 0:
            return (1.0, 0.0, 0.0)
        wa = 1.0 - t_row / n
        f = t_col / t_row
        return (wa, (t_row / n) * (1.0 - f), (t_row / n) * f)

    for row in range(n):
        for col in range(2 * row + 1):
            k = col // 2
            if col % 2 == 0:      # upward-pointing sub-triangle
                pts = [bary(row, k), bary(row + 1, k), bary(row + 1, k + 1)]
            else:                 # downward-pointing
                pts = [bary(row, k), bary(row, k + 1), bary(row + 1, k + 1)]
            centres.append(tuple(sum(p[i] for p in pts) / 3.0 for i in range(3)))
    return centres


def classify_surface_terrain(surface: Dict[str, Any], hexes_per_edge: int = None):
    """Samples the spherical surface into the twenty icosahedral faces used by
    `worldmap.render_world_map_svg`, so the net map and the globe show the
    same world.

    Each sub-triangle is sampled at its centroid, projected from the face's
    plane onto the sphere."""
    from .worldmap import DEFAULT_HEXES_PER_EDGE

    hexes_per_edge = hexes_per_edge or DEFAULT_HEXES_PER_EDGE
    faces = icosahedron_faces()
    barycentres = _subtriangle_barycentres(hexes_per_edge)

    land = surface['land_mask'].astype(np.float32)
    temp = surface['temperature_map']
    moisture = surface['moisture_map']
    height_field = surface['heightmap']
    sea_level = surface['sea_level']

    # Elevation clusters near sea level, so a fixed depth cut would make
    # almost every ocean cell read as shelf. Split on the median depth of the
    # actual sea floor instead.
    submerged = height_field[~surface['land_mask']]
    if submerged.size:
        deep_cut = float(np.median((sea_level - submerged)
                                   / max(1e-6, sea_level)))
    else:
        deep_cut = 0.35

    # Highlands are likewise a share of the land, not an absolute height: a
    # fixed cut leaves a low-relief world with no mountains at all. Roughly a
    # sixth of the land reads as mountain, near Earth's own proportion.
    emerged = height_field[surface['land_mask']]
    if emerged.size:
        alpine = float(np.percentile(emerged, 84.0))
    else:
        alpine = sea_level + (1.0 - sea_level) * 0.62

    out = []
    for va, vb, vc in faces:
        # Every sub-triangle centroid for this face, projected onto the sphere
        weights = np.array(barycentres, dtype=np.float32)
        points = (weights[:, 0:1] * va + weights[:, 1:2] * vb
                  + weights[:, 2:3] * vc)
        points /= np.maximum(np.linalg.norm(points, axis=1, keepdims=True), 1e-9)

        lat = np.arcsin(np.clip(points[:, 2], -1, 1)).astype(np.float32)
        lon = np.arctan2(points[:, 1], points[:, 0]).astype(np.float32)

        is_land = _sample_equirect(land, lat, lon) > 0.5
        t = _sample_equirect(temp, lat, lon)
        m = _sample_equirect(moisture, lat, lon)
        h = _sample_equirect(height_field, lat, lon)

        depth = (sea_level - h) / max(1e-6, sea_level)

        cells = np.where(
            t < 250, 'ice',
            np.where(~is_land,
                     np.where(depth > deep_cut, 'ocean', 'sea'),
                     np.where(h > alpine, 'mountain',
                              np.where((t > 303) & (m < 0.35), 'desert',
                                       np.where((m > 0.55) & (t > 273),
                                                'forest', 'plains')))))
        out.append([str(c) for c in cells])
    return out


# ------------------------------------------------------------- output

def save_png(array: np.ndarray, path: str) -> str:
    """Writes an image array to a PNG. Requires Pillow."""
    try:
        from PIL import Image
    except ImportError as exc:
        raise ImportError(
            "Saving PNGs needs Pillow: pip install pillow") from exc
    Image.fromarray(array).save(path)
    return path


def png_bytes(array: np.ndarray) -> bytes:
    """Encodes an image array as PNG data, for display without a file.

    `IPython.display.Image(data=png_bytes(view))` shows a rendered view in a
    notebook directly. Requires Pillow."""
    import io

    try:
        from PIL import Image
    except ImportError as exc:
        raise ImportError(
            "Encoding PNGs needs Pillow: pip install pillow") from exc
    buffer = io.BytesIO()
    Image.fromarray(array).save(buffer, format='PNG')
    return buffer.getvalue()


def render_planet_package(world: Any, out_dir: str = ".", size: int = 1024,
                          texture_size: Tuple[int, int] = (2048, 1024),
                          views: int = 3, seed: Optional[int] = None
                          ) -> Dict[str, Any]:
    """Generates everything for one world: surface model, equirectangular
    texture, Traveller net maps and orbital views, written to `out_dir`.

    Returns a dict of the in-memory products and the paths written."""
    import os

    surface = generate_planet_surface(world, width=texture_size[0],
                                      height=texture_size[1], seed=seed)
    name = surface['world_name']
    slug = "".join(ch for ch in name.lower() if ch.isalnum()) or "world"
    paths = {}

    os.makedirs(out_dir, exist_ok=True)

    paths['texture'] = save_png(surface['surface_texture'],
                                os.path.join(out_dir, f"{slug}_texture.png"))

    population = 0
    uwp = getattr(world, 'uwp', None)
    if uwp is not None:
        population = Utils.from_eHex(uwp.population)

    orbital = []
    for i in range(max(1, views)):
        lon = -140.0 + 280.0 * i / max(1, views - 1) if views > 1 else 20.0
        image = render_orbital_view(
            surface, size=size, sub_observer=(16.0, lon),
            sun_direction=(12.0, lon + 38.0), population=population)
        path = os.path.join(out_dir, f"{slug}_orbit_{i + 1}.png")
        save_png(image, path)
        orbital.append(image)
        paths[f'orbit_{i + 1}'] = path

    ico = render_icosahedral_net_svg(surface, name=name)
    ico_path = os.path.join(out_dir, f"{slug}_icosahedral_net.svg")
    with open(ico_path, 'w') as handle:
        handle.write(ico)
    paths['icosahedral_net'] = ico_path

    dodeca = render_dodecahedral_net(surface, name=name)
    dodeca_path = os.path.join(out_dir, f"{slug}_dodecahedral_net.svg")
    with open(dodeca_path, 'w') as handle:
        handle.write(dodeca)
    paths['dodecahedral_net'] = dodeca_path

    return {'surface': surface, 'orbital_views': orbital,
            'icosahedral_net_svg': ico, 'dodecahedral_net_svg': dodeca,
            'paths': paths}


def render_erith(sector: Any, out_dir: str = ".", name: str = "Erith",
                 culture_family: str = None, size: int = 1024,
                 texture_size: Tuple[int, int] = (2048, 1024),
                 views: int = 3, seed: Optional[int] = None,
                 proprietary: bool = True) -> Optional[Dict[str, Any]]:
    """Finds the sector's Erith, makes it Erith, and renders it.

    `findworld.make_erith` does the finding: it searches for the closest
    Earth-like world, imposes the Erith profile so the world really matches
    rather than merely coming close, rebuilds its nations and records the
    proprietor. This then builds the surface model and writes both foldable
    nets and the orbital views.

    Returns the `render_planet_package` result with the `findworld.Match`
    added under `match`, or None if the sector holds no candidate."""
    from .findworld import make_erith

    match = make_erith(sector, name=name, culture_family=culture_family,
                       proprietary=proprietary)
    if match is None:
        return None

    package = render_planet_package(match.body, out_dir=out_dir, size=size,
                                    texture_size=texture_size, views=views,
                                    seed=seed)
    package['match'] = match
    return package
