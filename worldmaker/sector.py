import random
import math
from typing import List, Dict, Any, Tuple, Optional

from .classes import Sector, StellarSystem, Wave, Sophont, PlanetaryBody, Satellite
from .utils import Utils
from .generator import generate_full_system
from .polity import define_polities, generate_bases, generate_travel_zones
from .sophont import get_major_race, generate_minor_race
from .stellar import generate_world_name

def hex_to_coords(hex_coord: str) -> Tuple[int, int]:
    """Converts a hex coordinate string (e.g., '0101') to (col, row) integers."""
    col = int(hex_coord[:2])
    row = int(hex_coord[2:])
    return col, row

def _to_cube(col: int, row: int) -> Tuple[int, int, int]:
    """Offset (Traveller column-staggered) coordinates to cube coordinates."""
    x = col
    z = row - (col + (col % 2)) // 2
    y = -x - z
    return x, y, z

def hex_distance(hex1: str, hex2: str) -> int:
    """Distance in parsecs (hexes) between two hex coordinates."""
    a = _to_cube(*hex_to_coords(hex1))
    b = _to_cube(*hex_to_coords(hex2))
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]), abs(a[2] - b[2]))

def is_adjacent(hex1: str, hex2: str) -> bool:
    """Calculates if two hexes are adjacent in a flat-topped hex grid."""
    return hex_distance(hex1, hex2) == 1

def hex_neighbors(col: int, row: int) -> Dict[str, Tuple[int, int]]:
    """The six neighbours of a hex, keyed by compass direction. Even-numbered
    columns are staggered half a hex down (Traveller map convention)."""
    if col % 2 == 1:  # odd printed column
        return {'N': (col, row - 1), 'S': (col, row + 1),
                'NE': (col + 1, row - 1), 'SE': (col + 1, row),
                'NW': (col - 1, row - 1), 'SW': (col - 1, row)}
    return {'N': (col, row - 1), 'S': (col, row + 1),
            'NE': (col + 1, row), 'SE': (col + 1, row + 1),
            'NW': (col - 1, row), 'SW': (col - 1, row + 1)}

def calculate_population_dm(hex_coord: str, sector: Sector) -> int:
    """Calculates the population DM for a given hex based on native sophonts and settlement waves."""
    population_dm = 0

    # Apply DM for native sophonts (+6 for homeworlds)
    if hex_coord in sector.native_sophonts:
        population_dm += 6

    # Apply DM for settlement waves (SCG p.22: thin wave DM-5 +1/century,
    # thick wave DM-3 +1/century; the penalty decays to zero, never a bonus)
    for wave in sector.settlement_waves:
        distance = hex_distance(hex_coord, wave.origin_hex)
        if distance <= (wave.propagation_rate * wave.age_centuries):
            if wave.wave_type == "thin":
                population_dm += min(0, -5 + wave.age_centuries)
            elif wave.wave_type == "thick":
                population_dm += min(0, -3 + wave.age_centuries)

    return population_dm

def define_settlement_waves(sector: Sector):
    """Defines settlement waves for the sector."""
    wave1 = Wave(
        name="First Wave",
        origin_hex="0101",
        age_centuries=10,
        wave_type="thick",
        propagation_rate=1.0
    )
    sector.settlement_waves.append(wave1)

def place_native_sophonts(sector: Sector):
    """Places native sophonts in the sector using the hybrid Major/Minor generator."""
    def random_hex():
        return f"{random.randint(1, sector.width):02d}{random.randint(1, sector.height):02d}"

    # Place a Major Race homeworld
    aslan_homeworld = get_major_race("Aslan", random_hex())
    sector.native_sophonts[aslan_homeworld.homeworld_hex] = aslan_homeworld

    # Place procedurally generated Minor Race homeworlds (~1 per 2 subsectors)
    num_minor = max(1, (sector.width * sector.height) // 160)
    for _ in range(num_minor):
        hex_coord = random_hex()
        if hex_coord in sector.native_sophonts:
            continue
        minor_race = generate_minor_race(hex_coord)
        sector.native_sophonts[hex_coord] = minor_race

def _mainworld_of(system: StellarSystem):
    """The system's mainworld, which may be a planet or a significant moon."""
    return system.mainworld

def calculate_routes(sector: Sector):
    """Calculates trade routes between adjacent systems."""
    systems_list = list(sector.systems.items())
    for i in range(len(systems_list)):
        hex1, sys1 = systems_list[i]
        mw1 = _mainworld_of(sys1)
        if not mw1: continue

        for j in range(i + 1, len(systems_list)):
            hex2, sys2 = systems_list[j]
            mw2 = _mainworld_of(sys2)
            if not mw2: continue

            if not is_adjacent(hex1, hex2):
                continue

            def get_wtn(mw):
                sp_val = {'A': 5, 'B': 4, 'C': 3, 'D': 2, 'E': 1, 'X': 0}.get(mw.uwp.starport, 0)
                pop_val = Utils.from_eHex(mw.uwp.population)
                return sp_val + (pop_val / 2)

            wtn1 = get_wtn(mw1)
            wtn2 = get_wtn(mw2)
            trade_potential = wtn1 + wtn2

            route_type = None
            if trade_potential >= 13:
                route_type = "major"
            elif trade_potential >= 9:
                route_type = "minor"

            if route_type:
                sector.routes.append((hex1, hex2, route_type))

def calculate_xboat_routes(sector: Sector, max_jump: int = 4):
    """Builds the express boat (Xboat) network: a minimal set of links, each
    at most jump-4, spanning the Class A and B starports - the heavy solid
    route lines of the classic sector maps."""
    hubs = []
    for hex_coord, system in sector.systems.items():
        mw = _mainworld_of(system)
        if mw and mw.uwp.starport in ('A', 'B'):
            hubs.append(hex_coord)

    if len(hubs) < 2:
        return

    # Kruskal's algorithm restricted to jump-range edges
    parent = {h: h for h in hubs}

    def find(h):
        while parent[h] != h:
            parent[h] = parent[parent[h]]
            h = parent[h]
        return h

    edges = []
    for i in range(len(hubs)):
        for j in range(i + 1, len(hubs)):
            d = hex_distance(hubs[i], hubs[j])
            if d <= max_jump:
                edges.append((d, hubs[i], hubs[j]))
    edges.sort()

    for d, h1, h2 in edges:
        r1, r2 = find(h1), find(h2)
        if r1 != r2:
            parent[r1] = r2
            sector.routes.append((h1, h2, "xboat"))

def _generate_systems(sector: Sector, density_target: int = 4):
    """Rolls system presence per hex (1D >= density_target) and generates
    systems with unique mainworld names."""
    used_names = set()
    for col in range(1, sector.width + 1):
        for row in range(1, sector.height + 1):
            hex_coord = f"{col:02d}{row:02d}"
            population_dm = calculate_population_dm(hex_coord, sector)

            if Utils.D6() >= density_target:
                name = generate_world_name(used_names)
                system = generate_full_system(name, population_dm)
                mainworld = _mainworld_of(system)
                if mainworld:
                    mainworld.name = name
                sector.systems[hex_coord] = system

def generate_sector(width=8, height=10):
    """Generates a subsector-sized (default 8x10) region of systems."""
    sector = Sector(width=width, height=height)

    # Population and Sophont waves
    define_settlement_waves(sector)
    place_native_sophonts(sector)

    _generate_systems(sector)

    define_polities(sector)
    generate_travel_zones(sector)
    generate_bases(sector)
    calculate_routes(sector)
    calculate_xboat_routes(sector)

    return sector

def name_subsectors(sector: Sector):
    """Names the sixteen subsectors A-P, conventionally after a notable world
    in each."""
    if sector.width != 32 or sector.height != 40:
        return
    for idx in range(16):
        letter = chr(ord('A') + idx)
        scol, srow = (idx % 4) * 8, (idx // 4) * 10
        best = None
        best_score = -1
        for c in range(scol + 1, scol + 9):
            for r in range(srow + 1, srow + 11):
                system = sector.systems.get(f"{c:02d}{r:02d}")
                mw = system.mainworld if system else None
                if mw is None:
                    continue
                score = (Utils.from_eHex(mw.uwp.population) * 2
                         + Utils.from_eHex(mw.uwp.tech_level))
                if score > best_score:
                    best_score = score
                    best = mw
        sector.subsector_names[letter] = best.name if best else f"Subsector {letter}"


def generate_full_sector(name="Generated Sector", width=32, height=40, density_target=4):
    """Generates a complete sector (default 32x40 hexes) in a single pass so
    polities, sophonts, settlement waves, routes and names are coherent
    across all sixteen subsectors."""
    sector = Sector(name=name, width=width, height=height)

    define_settlement_waves(sector)
    place_native_sophonts(sector)

    _generate_systems(sector, density_target)

    define_polities(sector)
    generate_travel_zones(sector)
    generate_bases(sector)
    calculate_routes(sector)
    calculate_xboat_routes(sector)
    name_subsectors(sector)

    return sector

def merge_subsectors(subsectors: List[Sector], name="Generated Sector") -> Sector:
    """Stitches sixteen independently generated 8x10 subsectors into one
    32x40 Sector (legacy support for pre-generate_full_sector data)."""
    merged = Sector(name=name, width=32, height=40)
    for idx, sub in enumerate(subsectors[:16]):
        scol, srow = (idx % 4) * 8, (idx // 4) * 10
        for hex_coord, system in sub.systems.items():
            c, r = hex_to_coords(hex_coord)
            merged.systems[f"{scol + c:02d}{srow + r:02d}"] = system
        for h1, h2, rtype in sub.routes:
            c1, r1 = hex_to_coords(h1)
            c2, r2 = hex_to_coords(h2)
            merged.routes.append((f"{scol + c1:02d}{srow + r1:02d}",
                                  f"{scol + c2:02d}{srow + r2:02d}", rtype))
        merged.polities = merged.polities or sub.polities
    return merged


# --------------------------------------------------------------------------
# Classic 1981-style map rendering
#
# Conventions follow the GDW Classic Traveller maps (the 1981 Deluxe boxset
# foldout of the Spinward Marches and the Supplement-format subsector pages):
# black ink on white; flat-topped hexes in staggered vertical columns; a small
# four-digit hex number at the top of every hex; the starport class letter
# above the world symbol; a solid disc for worlds with free-standing water and
# an open circle for dry worlds; a scatter of dots for asteroid-belt
# mainworlds; a small filled circle at the upper right when a gas giant is
# present; naval base (star) and scout base (triangle) glyphs at the left;
# world name beneath, in capitals for high-population (Pop 9+) worlds; travel
# zones as a broken (Amber) or solid (Red) ring around the hex contents;
# Xboat routes as heavy solid lines; polity borders as dashed lines; and a
# boxed legend.
# --------------------------------------------------------------------------

_SQRT3 = math.sqrt(3)

_CLASSIC_STYLE = '''<style>
    .cm-bg { fill: #fdfcf8; }
    .cm-hex { stroke: #1a1a1a; stroke-width: 0.9; fill: none; }
    .cm-hex-group { cursor: pointer; }
    .cm-hex-group:hover .cm-hex { stroke: #0284c7; stroke-width: 2.2; }
    .cm-frame { stroke: #000; stroke-width: 2.5; fill: none; }
    .cm-subgrid { stroke: #000; stroke-width: 1.6; fill: none; }
    .cm-title { font-family: Helvetica, Arial, sans-serif; font-weight: bold; fill: #000; }
    .cm-subtitle { font-family: Helvetica, Arial, sans-serif; fill: #333; }
    .cm-hexnum { font-family: Helvetica, Arial, sans-serif; fill: #666; text-anchor: middle; }
    .cm-port { font-family: Helvetica, Arial, sans-serif; font-weight: bold; fill: #000; text-anchor: middle; }
    .cm-name { font-family: Helvetica, Arial, sans-serif; fill: #000; text-anchor: middle; }
    .cm-base { font-family: Helvetica, Arial, sans-serif; fill: #000; text-anchor: middle; }
    .cm-world { fill: #000; stroke: #000; }
    .cm-world-dry { fill: #fdfcf8; stroke: #000; }
    .cm-belt { fill: #000; stroke: none; }
    .cm-gg { fill: #000; stroke: none; }
    .cm-zone-amber { fill: none; stroke: #b22222; }
    .cm-zone-red { fill: none; stroke: #b22222; }
    .cm-xboat { stroke: #000; fill: none; }
    .cm-border { stroke: #8b0000; fill: none; }
    .cm-legend-box { stroke: #000; stroke-width: 1.2; fill: #fdfcf8; }
    .cm-legend-text { font-family: Helvetica, Arial, sans-serif; fill: #000; }
    .cm-sslabel { font-family: Helvetica, Arial, sans-serif; fill: #999; }
    .cm-ssname { font-family: Helvetica, Arial, sans-serif; fill: #aaa; letter-spacing: 0.08em; }
</style>
'''

def _hex_center(col_idx: int, row_idx: int, radius: float,
                ox: float, oy: float) -> Tuple[float, float]:
    """Centre of the hex at 0-based (col_idx, row_idx); even printed columns
    (odd 0-based index) are staggered half a hex down."""
    row_h = _SQRT3 * radius
    x = ox + radius + 1.5 * radius * col_idx
    y = oy + row_h * row_idx + row_h / 2
    if col_idx % 2 == 1:
        y += row_h / 2
    return x, y

def _hex_vertices(x: float, y: float, radius: float) -> List[Tuple[float, float]]:
    return [(x + radius * math.cos(math.pi / 3 * i),
             y + radius * math.sin(math.pi / 3 * i)) for i in range(6)]

# Which pair of vertex indices forms the hex edge facing each direction
_EDGE_OF = {'SE': (0, 1), 'S': (1, 2), 'SW': (2, 3),
            'NW': (3, 4), 'N': (4, 5), 'NE': (5, 0)}

def _escape(text: str) -> str:
    """Escapes text for use inside an SVG element."""
    return (str(text).replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;'))


def _hex_tooltip(hex_coord: str, system: Optional[StellarSystem]) -> str:
    """The hover tooltip for a hex, shown by browsers as a native tooltip."""
    if system is None:
        return f"Hex {hex_coord}: empty"

    mw = _mainworld_of(system)
    if mw is None:
        return f"Hex {hex_coord}: {system.name}"

    lines = [
        f"Hex {hex_coord}: {mw.name}",
        f"UWP: {mw.uwp}",
        f"Allegiance: {system.allegiance}",
        f"Bases: {', '.join(system.bases) if system.bases else 'None'}",
        f"Gas giants: {system.gas_giant_count}",
        f"Trade codes: {', '.join(mw.trade_codes) if mw.trade_codes else 'None'}",
    ]
    if system.travel_zone:
        lines.append("Travel zone: "
                     + ("Amber" if system.travel_zone == 'A' else "Red"))
    return _escape("\n".join(lines))


def _world_glyphs(svg: List[str], system: StellarSystem, x: float, y: float,
                  R: float, scale: float):
    """Emits the in-hex system markings shared by both map scales."""
    mainworld = _mainworld_of(system)
    if not mainworld:
        return

    wr = 0.17 * R  # world symbol radius

    # Travel zone ring surrounds the hex contents
    if system.travel_zone == "A":
        svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{0.72*R:.1f}" '
                   f'class="cm-zone-amber" stroke-width="{1.6*scale:.1f}" '
                   f'stroke-dasharray="{4*scale:.1f},{3*scale:.1f}" />')
    elif system.travel_zone == "R":
        svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{0.72*R:.1f}" '
                   f'class="cm-zone-red" stroke-width="{2.2*scale:.1f}" />')

    # World symbol: belt glyph for Size 0, open circle if dry, disc if wet
    if mainworld.uwp.size == '0':
        for dx, dy, r in ((-0.9, -0.5, 0.45), (0.4, -0.9, 0.35), (0.9, 0.3, 0.4),
                          (-0.3, 0.7, 0.35), (-0.05, -0.1, 0.5)):
            svg.append(f'<circle cx="{x + dx*wr:.1f}" cy="{y + dy*wr:.1f}" '
                       f'r="{r*wr:.1f}" class="cm-belt" />')
    elif Utils.from_eHex(mainworld.uwp.hydrographics) > 0:
        svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{wr:.1f}" class="cm-world" />')
    else:
        svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{wr:.1f}" '
                   f'class="cm-world-dry" stroke-width="{1.2*scale:.1f}" />')

    # Starport class letter above the world symbol
    svg.append(f'<text x="{x:.1f}" y="{y - 0.32*R:.1f}" class="cm-port" '
               f'font-size="{0.30*R:.1f}">{mainworld.uwp.starport}</text>')

    # Gas giant: small filled circle at upper right
    if system.gas_giant_count > 0:
        svg.append(f'<circle cx="{x + 0.52*R:.1f}" cy="{y - 0.30*R:.1f}" '
                   f'r="{0.07*R:.1f}" class="cm-gg" />')

    # Bases at the left: naval star above, scout triangle below
    if any(b in system.bases for b in ("Naval", "Zhodani Naval")):
        svg.append(f'<text x="{x - 0.52*R:.1f}" y="{y - 0.18*R:.1f}" class="cm-base" '
                   f'font-size="{0.26*R:.1f}">&#9733;</text>')
    if "Scout" in system.bases:
        svg.append(f'<text x="{x - 0.52*R:.1f}" y="{y + 0.16*R:.1f}" class="cm-base" '
                   f'font-size="{0.22*R:.1f}">&#9650;</text>')

    # World name beneath; capitals for a billion or more inhabitants
    name = mainworld.name[:9]
    if Utils.from_eHex(mainworld.uwp.population) >= 9:
        name = name.upper()
        weight = ' font-weight="bold"'
    else:
        name = name.capitalize()
        weight = ''
    svg.append(f'<text x="{x:.1f}" y="{y + 0.48*R:.1f}" class="cm-name" '
               f'font-size="{0.21*R:.1f}"{weight}>{name}</text>')

def _draw_routes(svg: List[str], sector: Sector, R: float, ox: float, oy: float,
                 window: Tuple[int, int, int, int], scale: float):
    """Xboat route lines (drawn beneath the hex grid)."""
    c0, r0, c1, r1 = window

    def in_window(h):
        c, r = hex_to_coords(h)
        return c0 <= c <= c1 and r0 <= r <= r1

    for h1, h2, rtype in sector.routes:
        if rtype != "xboat" or not in_window(h1) or not in_window(h2):
            continue
        ca, ra = hex_to_coords(h1)
        cb, rb = hex_to_coords(h2)
        xa, ya = _hex_center(ca - c0, ra - r0, R, ox, oy)
        xb, yb = _hex_center(cb - c0, rb - r0, R, ox, oy)
        svg.append(f'<line x1="{xa:.1f}" y1="{ya:.1f}" x2="{xb:.1f}" y2="{yb:.1f}" '
                   f'class="cm-xboat" stroke-width="{2.6*scale:.1f}" />')

def _draw_borders(svg: List[str], sector: Sector, R: float, ox: float, oy: float,
                  window: Tuple[int, int, int, int], scale: float):
    """Dashed polity border lines.

    Edges are collected first and then chained head-to-tail into continuous
    polylines, so a border reads as one sweeping line rather than a chain of
    disconnected dashes."""
    c0, r0, c1, r1 = window
    territory: Dict[Tuple[int, int], str] = {}
    for polity in sector.polities:
        for h in polity.controlled_systems:
            territory[hex_to_coords(h)] = polity.allegiance_code

    # Collect the boundary edges of each polity separately
    by_polity: Dict[str, List[Tuple[Tuple[float, float], Tuple[float, float]]]] = {}
    for (col, row), alleg in territory.items():
        if not (c0 <= col <= c1 and r0 <= row <= r1):
            continue
        x, y = _hex_center(col - c0, row - r0, R, ox, oy)
        verts = _hex_vertices(x, y, R)
        for direction, neighbor in hex_neighbors(col, row).items():
            if territory.get(neighbor) == alleg:
                continue
            i, j = _EDGE_OF[direction]
            a = (round(verts[i][0], 2), round(verts[i][1], 2))
            b = (round(verts[j][0], 2), round(verts[j][1], 2))
            by_polity.setdefault(alleg, []).append((a, b))

    dash = f'{5 * scale:.1f},{3 * scale:.1f}'
    width = f'{1.8 * scale:.1f}'

    for edges in by_polity.values():
        for chain in _chain_edges(edges):
            pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in chain)
            svg.append(f'<polyline points="{pts}" class="cm-border" '
                       f'stroke-width="{width}" stroke-dasharray="{dash}" />')


def _chain_edges(edges: List[Tuple[Tuple[float, float], Tuple[float, float]]]
                 ) -> List[List[Tuple[float, float]]]:
    """Chains a set of undirected edges into the longest possible polylines."""
    adjacency: Dict[Tuple[float, float], List[Tuple[float, float]]] = {}
    remaining = set()
    for a, b in edges:
        if a == b:
            continue
        key = (a, b) if a <= b else (b, a)
        if key in remaining:
            continue
        remaining.add(key)
        adjacency.setdefault(a, []).append(b)
        adjacency.setdefault(b, []).append(a)

    chains = []
    while remaining:
        a, b = next(iter(remaining))
        remaining.discard((a, b))
        chain = [a, b]

        # Extend forward, then backward, consuming edges as we go
        for _ in range(2):
            while True:
                tail = chain[-1]
                nxt = None
                for candidate in adjacency.get(tail, []):
                    key = (tail, candidate) if tail <= candidate else (candidate, tail)
                    if key in remaining:
                        nxt = candidate
                        remaining.discard(key)
                        break
                if nxt is None:
                    break
                chain.append(nxt)
            chain.reverse()

        chains.append(chain)

    return chains


_LEGEND_ITEMS = ["world_wet", "world_dry", "belt", "gg", "naval", "scout",
                 "amber", "red", "xboat", "border"]
_LEGEND_LABELS = {
    "world_wet": "World (water present)", "world_dry": "World (no water)",
    "belt": "Asteroid belt", "gg": "Gas giant", "naval": "Naval base",
    "scout": "Scout base", "amber": "Amber zone", "red": "Red zone",
    "xboat": "Xboat route", "border": "Polity border",
}

def _legend_layout(width: float, font: float) -> Tuple[int, int, float]:
    """Column/row count and box height for the legend at a given width."""
    cols = max(1, min(5, int(width // (font * 15))))
    rows = math.ceil(len(_LEGEND_ITEMS) / cols)
    row_h = font * 2.4
    return cols, rows, rows * row_h + font * 1.6

def _draw_legend(svg: List[str], x: float, y: float, width: float, font: float):
    """Boxed map legend, laid out in as many columns as fit."""
    cols, rows, height = _legend_layout(width, font)
    row_h = font * 2.4
    svg.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" '
               f'height="{height:.1f}" class="cm-legend-box" />')
    cell_w = width / cols
    for idx, item in enumerate(_LEGEND_ITEMS):
        cx = x + (idx % cols) * cell_w + font * 1.6
        cy = y + font * 1.4 + (idx // cols) * row_h + row_h / 2 - font * 0.5
        g = font * 0.55  # glyph radius
        if item == "world_wet":
            svg.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{g:.1f}" class="cm-world cm-legend-glyph" />')
        elif item == "world_dry":
            svg.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{g:.1f}" class="cm-world-dry cm-legend-glyph" stroke-width="1.2" />')
        elif item == "belt":
            for dx, dy, r in ((-0.8, -0.4, 0.4), (0.5, -0.7, 0.35), (0.7, 0.5, 0.4), (-0.3, 0.6, 0.35)):
                svg.append(f'<circle cx="{cx + dx*g:.1f}" cy="{cy + dy*g:.1f}" r="{r*g:.1f}" class="cm-belt cm-legend-glyph" />')
        elif item == "gg":
            svg.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{g*0.5:.1f}" class="cm-gg cm-legend-glyph" />')
        elif item == "naval":
            svg.append(f'<text x="{cx:.1f}" y="{cy + g*0.8:.1f}" class="cm-base cm-legend-glyph" font-size="{font*1.3:.1f}">&#9733;</text>')
        elif item == "scout":
            svg.append(f'<text x="{cx:.1f}" y="{cy + g*0.8:.1f}" class="cm-base cm-legend-glyph" font-size="{font*1.1:.1f}">&#9650;</text>')
        elif item == "amber":
            svg.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{g:.1f}" class="cm-zone-amber cm-legend-glyph" stroke-width="1.6" stroke-dasharray="3,2.4" />')
        elif item == "red":
            svg.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{g:.1f}" class="cm-zone-red cm-legend-glyph" stroke-width="2" />')
        elif item == "xboat":
            svg.append(f'<line x1="{cx - g:.1f}" y1="{cy:.1f}" x2="{cx + g:.1f}" y2="{cy:.1f}" class="cm-xboat cm-legend-glyph" stroke-width="2.4" />')
        elif item == "border":
            svg.append(f'<line x1="{cx - g:.1f}" y1="{cy:.1f}" x2="{cx + g:.1f}" y2="{cy:.1f}" class="cm-border cm-legend-glyph" stroke-width="1.8" stroke-dasharray="4,2.5" />')
        svg.append(f'<text x="{cx + font*1.3:.1f}" y="{cy + font*0.4:.1f}" '
                   f'class="cm-legend-text" font-size="{font:.1f}">{_LEGEND_LABELS[item]}</text>')

def _render_window(sector: Sector, name: str, window: Tuple[int, int, int, int],
                   R: float, title_size: float, subsector_grid: bool) -> str:
    """Shared classic-style renderer for any rectangular hex window."""
    c0, r0, c1, r1 = window
    n_cols = c1 - c0 + 1
    n_rows = r1 - r0 + 1
    row_h = _SQRT3 * R
    scale = R / 32.0

    grid_w = 1.5 * R * n_cols + 0.5 * R
    grid_h = row_h * n_rows + row_h / 2
    ox, oy = 55.0, title_size * 3.2
    legend_font = max(8.0, title_size * 0.42)
    _, _, legend_h = _legend_layout(grid_w, legend_font)
    svg_w = grid_w + ox * 2
    svg_h = oy + grid_h + 30 + legend_h + 25

    svg: List[str] = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" '
               f'viewBox="0 0 {svg_w:.0f} {svg_h:.0f}" width="100%" height="100%">')
    svg.append(_CLASSIC_STYLE)
    svg.append(f'<rect x="0" y="0" width="{svg_w:.0f}" height="{svg_h:.0f}" class="cm-bg" />')

    # Title block
    svg.append(f'<text x="{ox:.1f}" y="{title_size * 1.6:.1f}" class="cm-title" '
               f'font-size="{title_size:.1f}">{name.upper()}</text>')
    svg.append(f'<text x="{ox:.1f}" y="{title_size * 2.5:.1f}" class="cm-subtitle" '
               f'font-size="{title_size * 0.38:.1f}">'
               f'Hexes {c0:02d}{r0:02d} &#8211; {c1:02d}{r1:02d} &#183; '
               f'1 hex = 1 parsec</text>')

    # Layer 1: Xboat routes beneath everything
    _draw_routes(svg, sector, R, ox, oy, window, scale)

    # Layer 2: hex grid and system contents
    for ci in range(n_cols):
        for ri in range(n_rows):
            col, row = c0 + ci, r0 + ri
            hex_coord = f"{col:02d}{row:02d}"
            x, y = _hex_center(ci, ri, R, ox, oy)
            system = sector.systems.get(hex_coord)
            pts = " ".join(f"{px:.1f},{py:.1f}" for px, py in _hex_vertices(x, y, R))
            # Each hex is a group carrying a <title>, so hovering it in a
            # browser shows the system's details.
            svg.append(f'<g class="cm-hex-group"><title>'
                       f'{_hex_tooltip(hex_coord, system)}</title>')
            svg.append(f'<polygon class="cm-hex" points="{pts}" />')
            svg.append(f'<text x="{x:.1f}" y="{y - 0.62*R:.1f}" class="cm-hexnum" '
                       f'font-size="{0.20*R:.1f}">{hex_coord}</text>')
            if system:
                _world_glyphs(svg, system, x, y, R, scale)
            svg.append('</g>')

    # Layer 3: polity borders over the grid
    _draw_borders(svg, sector, R, ox, oy, window, scale)

    # Layer 4: subsector division lines and letters (sector maps only)
    if subsector_grid:
        for k in range(1, 4):
            gx = ox + 1.5 * R * (8 * k) + 0.25 * R
            svg.append(f'<line x1="{gx:.1f}" y1="{oy:.1f}" x2="{gx:.1f}" '
                       f'y2="{oy + grid_h:.1f}" class="cm-subgrid" opacity="0.55" />')
            gy = oy + row_h * 10 * k + row_h / 4
            svg.append(f'<line x1="{ox:.1f}" y1="{gy:.1f}" x2="{ox + grid_w:.1f}" '
                       f'y2="{gy:.1f}" class="cm-subgrid" opacity="0.55" />')
        names = getattr(sector, 'subsector_names', None) or {}
        for idx in range(16):
            sc, sr = idx % 4, idx // 4
            letter = chr(ord("A") + idx)
            lx = ox + 1.5 * R * (8 * sc) + 0.75 * R
            ly = oy + row_h * 10 * sr + row_h * 0.9
            svg.append(f'<text x="{lx:.1f}" y="{ly:.1f}" class="cm-sslabel" '
                       f'font-size="{row_h * 0.85:.1f}">{letter}</text>')
            label = names.get(letter)
            if label:
                svg.append(f'<text x="{lx + row_h * 0.75:.1f}" y="{ly:.1f}" '
                           f'class="cm-ssname" font-size="{row_h * 0.34:.1f}">'
                           f'{label.upper()}</text>')

    # Frame and legend
    svg.append(f'<rect x="{ox:.1f}" y="{oy:.1f}" width="{grid_w:.1f}" '
               f'height="{grid_h:.1f}" class="cm-frame" />')
    _draw_legend(svg, ox, oy + grid_h + 25, grid_w, legend_font)

    svg.append('</svg>')
    return "\n".join(svg)

def subsector_letter(origin_col: int, origin_row: int) -> str:
    """The A-P letter of the subsector whose top-left hex is given."""
    idx = ((origin_row - 1) // 10) * 4 + ((origin_col - 1) // 8)
    return chr(ord('A') + idx) if 0 <= idx < 16 else '?'


def generate_subsector_svg(sector, name="Subsector Map", origin_col=1, origin_row=1):
    """Renders one 8x10 subsector in the classic Supplement-page style.
    Pass a subsector-sized Sector directly, or a full Sector plus the
    origin hex column/row of the subsector window (e.g. origin_col=9,
    origin_row=11 for subsector F)."""
    window = (origin_col, origin_row,
              min(origin_col + 7, sector.width),
              min(origin_row + 9, sector.height))
    return _render_window(sector, name, window, R=34.0, title_size=24.0,
                          subsector_grid=False)

def generate_sector_svg(sector, name=None):
    """Renders a full sector map in the style of the 1981 Deluxe boxset
    foldout. Accepts a Sector from generate_full_sector(), or (for legacy
    callers) a list of sixteen 8x10 subsector Sectors, which are stitched
    together first."""
    if isinstance(sector, list):
        sector = merge_subsectors(sector, name or "Generated Sector")
    window = (1, 1, sector.width, sector.height)
    return _render_window(sector, name or sector.name, window, R=15.0,
                          title_size=30.0, subsector_grid=(sector.width == 32
                                                           and sector.height == 40))
