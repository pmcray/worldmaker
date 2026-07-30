"""World surface mapping (WBH pp.134-146).

Traveller world maps are based on a 20-triangle icosahedron approximation of a
sphere, each triangle subdivided into hexagons. This module generates the
terrain for such a map from the world's hydrographics, climate and tectonics,
and renders it as an SVG in the flattened icosahedral net the book uses.
"""
import math
import random
from typing import Any, Dict, List, Tuple

from .utils import Utils

# Terrain types and the ink used to draw them
TERRAIN = {
    'ocean':     {'label': 'Ocean',      'fill': '#b8cfe0'},
    'sea':       {'label': 'Shallow sea', 'fill': '#d2e2ee'},
    'ice':       {'label': 'Ice',        'fill': '#f2f7fa'},
    'desert':    {'label': 'Desert',     'fill': '#f0e2c0'},
    'plains':    {'label': 'Plains',     'fill': '#e6ecd2'},
    'forest':    {'label': 'Forest',     'fill': '#cbdcbc'},
    'mountain':  {'label': 'Mountain',   'fill': '#d8cfc4'},
    'barren':    {'label': 'Barren rock', 'fill': '#dedad4'},
}

# Standard map: seven hexagons across the base of each of the 20 triangles
DEFAULT_HEXES_PER_EDGE = 7


def _triangle_hex_count(hexes_per_edge: int) -> int:
    """A triangle subdivided with n hexes along its base holds n^2 of them."""
    return hexes_per_edge * hexes_per_edge


def generate_world_terrain(world: Any, hexes_per_edge: int = DEFAULT_HEXES_PER_EDGE
                           ) -> List[List[str]]:
    """Generates terrain for the 20 icosahedral faces of a world.

    Hydrographics sets how much of the surface is liquid, the climate zone
    decides whether that liquid is ice, and the tectonic plate count drives
    how mountainous the land is. Returns a list of 20 faces, each a flat list
    of terrain keys."""
    hyd = Utils.from_eHex(getattr(world, 'hydrographics_code', 0)
                          or world.uwp.hydrographics)
    atm = Utils.from_eHex(getattr(world, 'atmosphere_code', 0)
                          or world.uwp.atmosphere)
    temp = getattr(world, 'mean_temperature', 288.0) or 288.0
    plates = getattr(world, 'tectonic_plates', 6) or 6
    biomass = getattr(world, 'biomass_rating', 0) or 0

    per_face = _triangle_hex_count(hexes_per_edge)
    total = 20 * per_face

    water_fraction = min(1.0, hyd / 10.0)
    n_water = int(round(total * water_fraction))

    # Cold worlds freeze their water; hot dry worlds turn to desert
    frozen = temp < 260
    airless = atm in (0, 1)

    # Build a latitude value for every hex so oceans and ice sit plausibly.
    # Faces 0-4 are the north cap, 5-14 the equatorial band, 15-19 the south.
    cells: List[Tuple[int, int, float]] = []
    for face in range(20):
        if face < 5:
            base_lat = 0.8
        elif face < 15:
            base_lat = 0.0 if face % 2 == 0 else 0.2
        else:
            base_lat = -0.8
        for i in range(per_face):
            # Position within the face nudges latitude a little
            jitter = (i / per_face - 0.5) * 0.35
            cells.append((face, i, base_lat + jitter))

    # Seed a few ocean basins and let them grow, so water forms bodies rather
    # than speckle
    terrain: Dict[Tuple[int, int], str] = {}
    if n_water > 0 and not airless:
        n_basins = max(1, min(8, plates // 2 + 1))
        basin_centres = random.sample(cells, min(n_basins, len(cells)))
        remaining = n_water
        # Grow basins by proximity in the (face, index) ordering, weighted so
        # low latitudes fill first
        ordered = sorted(
            cells,
            key=lambda c: min(abs(c[0] - b[0]) * per_face + abs(c[1] - b[1])
                              for b in basin_centres))
        for cell in ordered:
            if remaining <= 0:
                break
            key = (cell[0], cell[1])
            if key in terrain:
                continue
            lat = abs(cell[2])
            if frozen or lat > 0.75:
                terrain[key] = 'ice'
            else:
                terrain[key] = 'ocean' if remaining > n_water * 0.35 else 'sea'
            remaining -= 1

    # Everything else is land, shaped by climate and tectonics
    mountain_chance = min(0.35, 0.05 + plates * 0.02)
    for face, i, lat in cells:
        key = (face, i)
        if key in terrain:
            continue
        if airless:
            terrain[key] = 'barren'
            continue
        if abs(lat) > 0.85 and temp < 300:
            terrain[key] = 'ice'
        elif random.random() < mountain_chance:
            terrain[key] = 'mountain'
        elif temp > 330 or hyd <= 1:
            terrain[key] = 'desert'
        elif biomass >= 6 and random.random() < 0.5:
            terrain[key] = 'forest'
        elif temp < 273:
            terrain[key] = 'ice' if random.random() < 0.4 else 'plains'
        else:
            terrain[key] = 'plains'

    return [[terrain[(f, i)] for i in range(per_face)] for f in range(20)]


def _triangle_points(cx: float, cy: float, size: float, pointing_up: bool
                     ) -> List[Tuple[float, float]]:
    h = size * math.sqrt(3) / 2
    if pointing_up:
        return [(cx, cy - h * 2 / 3), (cx - size / 2, cy + h / 3),
                (cx + size / 2, cy + h / 3)]
    return [(cx, cy + h * 2 / 3), (cx - size / 2, cy - h / 3),
            (cx + size / 2, cy - h / 3)]


def _face_cells(points: List[Tuple[float, float]], hexes_per_edge: int,
                pointing_up: bool) -> List[List[Tuple[float, float]]]:
    """Subdivides a triangle into n^2 smaller triangles, returned as polygon
    point lists in the same order as the terrain list."""
    (ax, ay), (bx, by), (cx, cy) = points
    cells = []
    n = hexes_per_edge
    for row in range(n):
        for col in range(2 * row + 1):
            up = (col % 2 == 0)
            i = row + 1 if up else row
            # Barycentric interpolation down the triangle
            def lerp(t_row, t_col):
                top = ((ax + (bx - ax) * t_row / n),
                       (ay + (by - ay) * t_row / n))
                bot = ((ax + (cx - ax) * t_row / n),
                       (ay + (cy - ay) * t_row / n))
                if t_row == 0:
                    return top
                f = t_col / t_row
                return (top[0] + (bot[0] - top[0]) * f,
                        top[1] + (bot[1] - top[1]) * f)

            if up:
                p1 = lerp(row, col // 2)
                p2 = lerp(row + 1, col // 2)
                p3 = lerp(row + 1, col // 2 + 1)
            else:
                p1 = lerp(row, col // 2)
                p2 = lerp(row, col // 2 + 1)
                p3 = lerp(row + 1, col // 2 + 1)
            cells.append([p1, p2, p3])
    return cells


def render_world_map_svg(world: Any, terrain: List[List[str]] = None,
                         hexes_per_edge: int = DEFAULT_HEXES_PER_EDGE,
                         name: str = None) -> str:
    """Renders a world's surface as the flattened icosahedral net used by
    Traveller world map templates (WBH p.135)."""
    if terrain is None:
        terrain = generate_world_terrain(world, hexes_per_edge)

    name = name or getattr(world, 'name', 'World')
    size = 110.0
    h = size * math.sqrt(3) / 2

    margin_x, margin_y = 40.0, 90.0
    width = margin_x * 2 + size * 5.5
    height = margin_y + h * 3 + 120

    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" '
           f'viewBox="0 0 {width:.0f} {height:.0f}" width="100%" height="100%">']
    svg.append('''<style>
    .wm-bg { fill: #fdfcf8; }
    .wm-cell { stroke: #999; stroke-width: 0.3; }
    .wm-face { stroke: #333; stroke-width: 1.1; fill: none; }
    .wm-title { font-family: Helvetica, Arial, sans-serif; font-weight: bold; fill: #000; }
    .wm-sub { font-family: Helvetica, Arial, sans-serif; fill: #444; }
    .wm-legend { font-family: Helvetica, Arial, sans-serif; fill: #000; }
    .wm-legend-box { stroke: #000; stroke-width: 1; fill: #fdfcf8; }
</style>''')
    svg.append(f'<rect x="0" y="0" width="{width:.0f}" height="{height:.0f}" class="wm-bg" />')

    uwp = str(getattr(world, 'uwp', ''))
    svg.append(f'<text x="{margin_x:.0f}" y="34" class="wm-title" '
               f'font-size="21">{name.upper()}</text>')
    svg.append(f'<text x="{margin_x:.0f}" y="55" class="wm-sub" font-size="11">'
               f'{uwp} &#183; icosahedral surface map &#183; '
               f'{20 * _triangle_hex_count(hexes_per_edge)} cells</text>')

    # The net: 5 upward faces (north cap), 10 alternating (equator),
    # 5 downward (south cap)
    def draw_face(face_index, cx, cy, pointing_up):
        pts = _triangle_points(cx, cy, size, pointing_up)
        cells = _face_cells(pts, hexes_per_edge, pointing_up)
        face_terrain = terrain[face_index]
        for i, cell in enumerate(cells):
            if i >= len(face_terrain):
                break
            fill = TERRAIN[face_terrain[i]]['fill']
            pstr = " ".join(f"{x:.1f},{y:.1f}" for x, y in cell)
            svg.append(f'<polygon points="{pstr}" class="wm-cell" fill="{fill}" />')
        pstr = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        svg.append(f'<polygon points="{pstr}" class="wm-face" />')

    # In an icosahedral net each band is one triangle-height tall. An
    # up-pointing face has its apex at the top of its band (centre 2h/3 down);
    # a down-pointing face has its apex at the bottom (centre h/3 down). The
    # equatorial band alternates the two so they interlock along shared edges.
    band_north = margin_y
    band_mid = margin_y + h
    band_south = margin_y + h * 2

    for i in range(5):
        draw_face(i, margin_x + size * (i + 1.0), band_north + h * 2 / 3, True)
    for i in range(10):
        up = (i % 2 == 0)
        cx = margin_x + size * (i * 0.5 + 0.5)
        cy = band_mid + (h * 2 / 3 if up else h / 3)
        draw_face(5 + i, cx, cy, up)
    for i in range(5):
        draw_face(15 + i, margin_x + size * (i + 0.5),
                  band_south + h / 3, False)

    # Legend of the terrain actually used
    used = []
    for face in terrain:
        for t in face:
            if t not in used:
                used.append(t)
    legend_y = height - 78
    box_w = min(width - margin_x * 2, 150 * ((len(used) + 1) // 2))
    svg.append(f'<rect x="{margin_x:.0f}" y="{legend_y:.0f}" '
               f'width="{box_w:.0f}" height="58" class="wm-legend-box" />')
    for i, key in enumerate(used):
        col, row = i % ((len(used) + 1) // 2 or 1), i // ((len(used) + 1) // 2 or 1)
        lx = margin_x + 14 + col * 150
        ly = legend_y + 20 + row * 22
        svg.append(f'<rect x="{lx:.0f}" y="{ly - 9:.0f}" width="14" height="12" '
                   f'fill="{TERRAIN[key]["fill"]}" stroke="#666" stroke-width="0.5" />')
        svg.append(f'<text x="{lx + 20:.0f}" y="{ly:.0f}" class="wm-legend" '
                   f'font-size="11">{TERRAIN[key]["label"]}</text>')

    svg.append('</svg>')
    return "\n".join(svg)


def terrain_summary(terrain: List[List[str]]) -> Dict[str, float]:
    """The percentage of the surface given over to each terrain type."""
    counts: Dict[str, int] = {}
    total = 0
    for face in terrain:
        for t in face:
            counts[t] = counts.get(t, 0) + 1
            total += 1
    if not total:
        return {}
    return {k: round(100.0 * v / total, 1) for k, v in sorted(counts.items())}
