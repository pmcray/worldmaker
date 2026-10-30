import random
import math
import html
from typing import List, Dict, Any, Tuple, Optional

from .classes import Sector, StellarSystem, Wave, Sophont, PlanetaryBody, Satellite
from .utils import Utils
from .generator import generate_full_system
from .polity import define_polities, generate_bases
from .sophont import get_major_race, generate_minor_race

def hex_to_coords(hex_coord: str) -> Tuple[int, int]:
    """Converts a hex coordinate string (e.g., '0101') to (col, row) integers."""
    col = int(hex_coord[:2])
    row = int(hex_coord[2:])
    return col, row

def hex_distance(hex1: str, hex2: str) -> float:
    """Calculates the Euclidean distance between two hex coordinates."""
    col1, row1 = hex_to_coords(hex1)
    col2, row2 = hex_to_coords(hex2)
    # Euclidean approximation
    return math.sqrt((col1 - col2)**2 + (row1 - row2)**2)

def is_adjacent(hex1: str, hex2: str) -> bool:
    """Calculates if two hexes are adjacent in a flat-topped hex grid."""
    col1, row1 = hex_to_coords(hex1)
    col2, row2 = hex_to_coords(hex2)
    
    dc = col1 - col2
    dr = row1 - row2
    
    if dc == 0:
        return abs(dr) == 1
    elif abs(dc) == 1:
        if col1 % 2 == 1: # 1-based odd (01, 03, 05...)
            return dr in [0, 1]
        else: # 1-based even (02, 04, 06...)
            return dr in [-1, 0]
    return False

def calculate_population_dm(hex_coord: str, sector: Sector) -> int:
    """Calculates the population DM for a given hex based on native sophonts and settlement waves."""
    population_dm = 0

    # Apply DM for native sophonts (+6 for homeworlds)
    if hex_coord in sector.native_sophonts:
        population_dm += 6

    # Apply DM for settlement waves
    for wave in sector.settlement_waves:
        distance = hex_distance(hex_coord, wave.origin_hex)
        if distance <= (wave.propagation_rate * wave.age_centuries):
            if wave.wave_type == "thin":
                population_dm += (-5 + wave.age_centuries) # DM-5 + 1 per century
            elif wave.wave_type == "thick":
                population_dm += (-3 + wave.age_centuries) # DM-3 + 1 per century

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
    # Place a Major Race homeworld
    aslan_homeworld = get_major_race("Aslan", "0805")
    sector.native_sophonts[aslan_homeworld.homeworld_hex] = aslan_homeworld

    # Place a procedurally generated Minor Race homeworld
    minor_race = generate_minor_race("0308")
    sector.native_sophonts[minor_race.homeworld_hex] = minor_race

def calculate_routes(sector: Sector):
    """Calculates trade routes between adjacent systems."""
    systems_list = list(sector.systems.items())
    for i in range(len(systems_list)):
        hex1, sys1 = systems_list[i]
        mw1 = next((w for w in sys1.all_worlds if w.is_mainworld), None)
        if not mw1: continue
        
        for j in range(i + 1, len(systems_list)):
            hex2, sys2 = systems_list[j]
            mw2 = next((w for w in sys2.all_worlds if w.is_mainworld), None)
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

def generate_sector(width=8, height=10):
    """Generates a sector/subsector of systems."""
    sector = Sector(width=width, height=height)
    
    # Population and Sophont waves
    define_settlement_waves(sector)
    place_native_sophonts(sector)

    for col in range(1, width + 1):
        for row in range(1, height + 1):
            hex_coord = f"{col:02d}{row:02d}"
            population_dm = calculate_population_dm(hex_coord, sector)

            # Roll for system presence (50% density standard)
            if Utils.D6() >= 4:
                sys_name = f"System {hex_coord}"
                system = generate_full_system(sys_name, population_dm)
                sector.systems[hex_coord] = system
                
    define_polities(sector)
    generate_bases(sector)
    calculate_routes(sector)

    from .analogues import (
        find_solar_analogues,
        find_solar_system_analogues,
        find_earth_analogues,
    )
    sector.solar_analogues = find_solar_analogues(sector, top_n=10)
    if sector.solar_analogues:
        sector.solar_analogue_hex = sector.solar_analogues[0]["hex_coord"]
    sector.solar_system_analogues = find_solar_system_analogues(sector, top_n=10)
    if sector.solar_system_analogues:
        sector.solar_system_analogue_hex = sector.solar_system_analogues[0]["hex_coord"]
    sector.earth_analogues = find_earth_analogues(sector, top_n=10)
    if sector.earth_analogues and not sector.erith_hex:
        sector.erith_hex = sector.earth_analogues[0]["hex_coord"]
    
    return sector

def generate_sector_svg(subsectors, full_sector: Optional[Sector] = None):
    """Renders a combined sector vector map of Traveller systems using mathematically exact flat-topped hexes."""
    grid_cols = 32
    grid_rows = 40
    
    hex_radius = 20
    row_height = math.sqrt(3) * hex_radius
    col_width = 1.5 * hex_radius
    
    svg_width = grid_cols * col_width + 0.5 * hex_radius
    svg_height = grid_rows * row_height + row_height / 2
    
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_width} {svg_height}" width="100%" height="100%">\n'
    
    svg += '''<style>
    .hex { stroke: #888; stroke-width: 0.5; fill: #fff; transition: all 0.15s ease; }
    .hex-fill-Im { fill: #ffe0e0; }
    .hex-fill-Cs { fill: #ffd6d6; }
    .hex-fill-Zh { fill: #e0e4ff; }
    .hex-fill-Av { fill: #ffeec0; }
    .hex-fill-He { fill: #f3d1ff; }
    .hex-fill-Fe { fill: #d4f7dc; }
    .hex-fill-Hl { fill: #e8f5c8; }
    .hex-fill-Tl { fill: #ffdcc4; }
    .hex-fill-Na { fill: #ffffff; }
    .hex-group { cursor: pointer; }
    .hex-group:hover .hex { stroke: #0284c7 !important; stroke-width: 2 !important; fill: #38bdf8 !important; }
    .hex_text { font-family: "Courier New", monospace; font-size: 5.5px; text-anchor: middle; fill: #222; }
    .coord_text { font-size: 4.8px; fill: #666; }
    .uwp_text { font-size: 4.8px; fill: #111; font-weight: bold; }
    .world-icon { stroke: #333; stroke-width: 0.5; }
    .gas-giant { fill: #444; stroke: none; }
    .base-icon { font-size: 7px; fill: #222; }
    .zone-amber { fill: none; stroke: #f59e0b; stroke-width: 1.2; stroke-dasharray: 2, 1; }
    .zone-red { fill: none; stroke: #dc2626; stroke-width: 1.4; }
    .route-major { stroke: #16a34a; stroke-width: 1.8; opacity: 0.65; pointer-events: none; }
    .route-minor { stroke: #0284c7; stroke-width: 1.0; stroke-dasharray: 2, 2; opacity: 0.5; pointer-events: none; }
    .subsector-grid { stroke: #334155; stroke-width: 1.2; stroke-dasharray: 4, 3; fill: none; opacity: 0.55; pointer-events: none; }
    .subsector-watermark { font-family: "Georgia", serif; font-size: 16px; font-weight: bold; fill: #1e293b; opacity: 0.16; text-anchor: middle; pointer-events: none; }
</style>
'''
    
    palette = {
        'Wa': '#4287f5', 'Ga': '#42f569', 'De': '#f5e042', 'Va': '#d1d1d1',
        'Ic': '#e0f7fa', 'As': '#5e5e5e', 'In': '#f55742', 'He': '#f55742'
    }

    def get_hex_center(col_idx, row_idx):
        x = col_idx * col_width + hex_radius
        y = row_idx * row_height + row_height / 2
        if col_idx % 2 == 1:
            y += row_height / 2
        return x, y

    # 1. Draw Routes
    all_routes = []
    if full_sector and full_sector.routes:
        for h1, h2, rtype in full_sector.routes:
            c1, r1 = hex_to_coords(h1)
            c2, r2 = hex_to_coords(h2)
            x1, y1 = get_hex_center(c1 - 1, r1 - 1)
            x2, y2 = get_hex_center(c2 - 1, r2 - 1)
            all_routes.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="route-{rtype}" />')
    else:
        for subsector_row in range(4):
            for subsector_col in range(4):
                subsector_index = subsector_row * 4 + subsector_col
                if subsector_index >= len(subsectors): continue
                subsector = subsectors[subsector_index]
                
                for h1, h2, rtype in subsector.routes:
                    c1, r1 = hex_to_coords(h1)
                    c2, r2 = hex_to_coords(h2)
                    
                    g_c1 = subsector_col * 8 + (c1 - 1)
                    g_r1 = subsector_row * 10 + (r1 - 1)
                    g_c2 = subsector_col * 8 + (c2 - 1)
                    g_r2 = subsector_row * 10 + (r2 - 1)
                    
                    x1, y1 = get_hex_center(g_c1, g_r1)
                    x2, y2 = get_hex_center(g_c2, g_r2)
                    
                    all_routes.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="route-{rtype}" />')

    # 2. Draw Hexes & Systems
    valid_allegiances = {'Im', 'Cs', 'Zh', 'Av', 'He', 'Fe', 'Hl', 'Tl'}
    for subsector_row in range(4):
        for subsector_col in range(4):
            subsector_index = subsector_row * 4 + subsector_col
            if subsector_index >= len(subsectors): continue
            
            subsector = subsectors[subsector_index]
            for row in range(subsector.height):
                for col in range(subsector.width):
                    hex_col = subsector_col * 8 + col
                    hex_row = subsector_row * 10 + row
                    hex_coord = f"{hex_col + 1:02d}{hex_row + 1:02d}"
                    
                    x, y = get_hex_center(hex_col, hex_row)

                    system_hex_coord = f"{col+1:02d}{row+1:02d}"
                    system = subsector.systems.get(system_hex_coord)
                    
                    fill_class = "hex-fill-Na"
                    if system:
                        fill_class = f"hex-fill-{system.allegiance}" if system.allegiance in valid_allegiances else "hex-fill-Na"

                    # Hex corners (flat-topped)
                    points = []
                    for i in range(6):
                        angle = math.pi / 3 * i
                        px = x + hex_radius * math.cos(angle)
                        py = y + hex_radius * math.sin(angle)
                        points.append(f"{px},{py}")

                    tooltip_title = f"Hex {hex_coord}"
                    if system:
                        mw = next((w for w in system.all_worlds if w.is_mainworld), None)
                        secondary_count = max(0, len(system.all_worlds) - 1)
                        moon_count = sum(len([s for s in w.satellites if not s.is_ring]) for w in system.all_worlds)
                        if mw:
                            tooltip_title += (
                                f": {mw.name}\n"
                                f"Subsector: {system.subsector_code or ''} ({system.subsector_name or subsector.name})\n"
                                f"UWP: {mw.uwp} | PBG: {system.pbg or 'N/A'}\n"
                                f"Allegiance: {system.allegiance} | Zone: {system.travel_zone or 'Green'}\n"
                                f"Bases: {', '.join(system.bases) if system.bases else 'None'}\n"
                                f"Stars: {', '.join(s.spectral_type for s in system.stars if not s.is_composite)}\n"
                                f"Secondary Worlds: {secondary_count} (Gas Giants: {system.gas_giant_count}, Belts: {system.planetoid_belt_count}, Moons: {moon_count})\n"
                                f"Trade Codes: {', '.join(mw.trade_codes) if mw.trade_codes else 'None'}\n"
                                f"Settlement: {system.settlement_epoch} - {system.settlement_wave}"
                            )
                            if system.historical_notes:
                                tooltip_title += f"\nLore: {system.historical_notes[0]}"

                    svg += f'<g class="hex-group"><title>{html.escape(tooltip_title)}</title>\n'
                    svg += f'<polygon class="hex {fill_class}" points="{" ".join(points)}"/>\n'
                    
                    # Coordinate text at top
                    svg += f'<text x="{x}" y="{y - 8}" class="hex_text coord_text">{html.escape(str(hex_coord))}</text>\n'
                    
                    # Details
                    if system:
                        if system.travel_zone == "R":
                            svg += f'<circle cx="{x}" cy="{y}" r="14" class="zone-red" />\n'
                        elif system.travel_zone == "A":
                            svg += f'<circle cx="{x}" cy="{y}" r="14" class="zone-amber" />\n'

                        mainworld = next((w for w in system.all_worlds if w.is_mainworld), None)
                        if mainworld:
                            # 1. World Icon
                            world_color = '#f2f2f2'
                            for code, color in palette.items():
                                if code in mainworld.trade_codes:
                                    world_color = color
                                    break
                            svg += f'<circle cx="{x}" cy="{y}" r="3" class="world-icon" fill="{world_color}" />\n'
                            
                            # 2. Gas Giant Indicator
                            if system.gas_giant_count > 0:
                                svg += f'<circle cx="{x+6}" cy="{y-5}" r="1.5" class="gas-giant" />\n'
                            
                            # 3. Bases
                            base_symbol = ""
                            if "Naval" in system.bases or "Zhodani Naval" in system.bases: base_symbol += "★"
                            if "Scout" in system.bases: base_symbol += "▲"
                            if "Military" in system.bases or "Zhodani Base" in system.bases: base_symbol += "■"
                            if "Pirate" in system.bases: base_symbol += "☠"
                            if base_symbol:
                                svg += f'<text x="{x-9}" y="{y-4}" class="base-icon">{base_symbol}</text>\n'

                            # 4. Name and UWP
                            svg += f'<text x="{x}" y="{y+6}" class="hex_text">{html.escape(mainworld.name[:9].upper())}</text>\n'
                            svg += f'<text x="{x}" y="{y+12}" class="hex_text uwp_text">{html.escape(str(mainworld.uwp))}</text>\n'

                    svg += '</g>\n'

            # Subsector watermark label
            sub_cx, sub_cy = get_hex_center(subsector_col * 8 + 3.5, subsector_row * 10 + 4.5)
            svg += f'<text x="{sub_cx}" y="{sub_cy}" class="subsector-watermark">{html.escape(subsector.name.upper())}</text>\n'

    # Overlay routes so they are visible above opaque hex fills without blocking hover tooltips
    svg += '\n'.join(all_routes) + '\n'
    svg += '</svg>'
    return svg

def generate_subsector_svg(subsector, name="Subsector Map", subsector_col: int = 0, subsector_row: int = 0):
    """Renders a single subsector in the classic 1981 Traveller De Luxe print style."""
    grid_cols = 8
    grid_rows = 10
    
    hex_radius = 28 # Slightly larger for individual subsector maps
    row_height = math.sqrt(3) * hex_radius
    col_width = 1.5 * hex_radius
    
    left_padding = 50
    top_padding = 80
    
    grid_width = grid_cols * col_width + 0.5 * hex_radius
    grid_height = grid_rows * row_height + row_height / 2
    
    svg_width = grid_width + left_padding * 2
    svg_height = grid_height + top_padding + 50
    
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_width} {svg_height}" width="100%" height="100%" style="background-color: #faf8f5;">\n'
    
    # Styles for vintage paper/black ink print aesthetic with interactive tooltips
    svg += '''<style>
    .subsector-title { font-family: "Georgia", serif; font-size: 18px; font-weight: bold; fill: #000; text-anchor: middle; }
    .subsector-subtitle { font-family: "Georgia", serif; font-style: italic; font-size: 11px; fill: #555; text-anchor: middle; }
    .classic-hex { stroke: #000; stroke-width: 0.8; fill: none; transition: all 0.2s ease; }
    .classic-hex-filled { fill: #fcfbfa; fill-opacity: 0.75; }
    .hex-group { cursor: pointer; }
    .hex-group:hover .classic-hex { stroke: #0284c7 !important; stroke-width: 2.5 !important; fill: #e0f2fe !important; }
    .hex-group:hover .classic-world-dot { fill: #0284c7 !important; r: 5; }
    .grid-border { stroke: #000; stroke-width: 2.5; fill: none; }
    .grid-label { font-family: "Courier New", monospace; font-size: 10px; font-weight: bold; fill: #000; text-anchor: middle; dominant-baseline: middle; }
    .classic-text { font-family: "Courier New", monospace; font-size: 7px; text-anchor: middle; fill: #000; font-weight: bold; }
    .classic-coord { font-size: 6px; fill: #555; font-weight: normal; }
    .classic-uwp { font-size: 6px; fill: #333; font-weight: bold; }
    .classic-alleg { font-size: 5.5px; fill: #444; font-weight: normal; }
    .classic-world-dot { fill: #000; stroke: #000; stroke-width: 1; transition: all 0.2s ease; }
    .classic-gas-ring { fill: none; stroke: #000; stroke-width: 1; }
    .classic-zone-amber { fill: none; stroke: #d97706; stroke-width: 1.5; stroke-dasharray: 3, 2; }
    .classic-zone-red { fill: none; stroke: #b91c1c; stroke-width: 1.8; }
    .classic-base { font-family: "Courier New", monospace; font-size: 8px; fill: #000; font-weight: bold; }
    .classic-route-major { stroke: #000; stroke-width: 1.5; fill: none; }
    .classic-route-minor { stroke: #000; stroke-width: 0.8; stroke-dasharray: 2, 2; fill: none; }
</style>
'''
    
    # Title Block
    svg += f'<text x="{svg_width / 2}" y="35" class="subsector-title">{html.escape(name.upper())}</text>\n'
    svg += f'<text x="{svg_width / 2}" y="52" class="subsector-subtitle">Foreven Sector (Iakr) — Year 1107 IISS Survey Grid</text>\n'

    def get_hex_center(col_idx, row_idx):
        x = col_idx * col_width + hex_radius + left_padding
        y = row_idx * row_height + row_height / 2 + top_padding
        if col_idx % 2 == 1:
            y += row_height / 2
        return x, y

    # 1. Draw Routes
    for h1, h2, rtype in subsector.routes:
        c1, r1 = hex_to_coords(h1)
        c2, r2 = hex_to_coords(h2)
        
        x1, y1 = get_hex_center(c1 - 1, r1 - 1)
        x2, y2 = get_hex_center(c2 - 1, r2 - 1)
        
        svg += f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="classic-route-{rtype}" />\n'

    # 2. Draw Hexes & Systems
    for row in range(grid_rows):
        for col in range(grid_cols):
            x, y = get_hex_center(col, row)
            local_coord = f"{col + 1:02d}{row + 1:02d}"
            global_coord = f"{subsector_col * 8 + col + 1:02d}{subsector_row * 10 + row + 1:02d}"
            system = subsector.systems.get(local_coord)
            disp_coord = system.hex_coord if (system and system.hex_coord) else global_coord
            
            # Hex corners (flat-topped)
            points = []
            for i in range(6):
                angle = math.pi / 3 * i
                px = x + hex_radius * math.cos(angle)
                py = y + hex_radius * math.sin(angle)
                points.append(f"{px},{py}")
            
            fill_class = "classic-hex-filled" if system else ""
            
            tooltip_title = f"Hex {disp_coord}"
            if system:
                mw = next((w for w in system.all_worlds if w.is_mainworld), None)
                secondary_count = max(0, len(system.all_worlds) - 1)
                if mw:
                    tooltip_title += (
                        f": {mw.name}\n"
                        f"UWP: {mw.uwp} | Allegiance: {system.allegiance}\n"
                        f"Bases: {', '.join(system.bases) if system.bases else 'None'}\n"
                        f"Secondary Worlds: {secondary_count} (Gas Giants: {system.gas_giant_count}, Belts: {system.planetoid_belt_count})\n"
                        f"Trade Codes: {', '.join(mw.trade_codes) if mw.trade_codes else 'None'}\n"
                        f"History: {system.settlement_epoch} ({system.settlement_wave})"
                    )
                    if system.historical_notes:
                        tooltip_title += f"\nLore: {system.historical_notes[0]}"
            
            svg += f'<g class="hex-group"><title>{html.escape(tooltip_title)}</title>\n'
            svg += f'<polygon class="classic-hex {fill_class}" points="{" ".join(points)}"/>\n'
            
            # Draw tiny coordinate at top of hex
            svg += f'<text x="{x}" y="{y - hex_radius/1.6}" class="classic-text classic-coord">{html.escape(str(disp_coord))}</text>\n'
            
            if system:
                if system.travel_zone == "R":
                    svg += f'<circle cx="{x}" cy="{y}" r="19" class="classic-zone-red" />\n'
                elif system.travel_zone == "A":
                    svg += f'<circle cx="{x}" cy="{y}" r="19" class="classic-zone-amber" />\n'

                mainworld = next((w for w in system.all_worlds if w.is_mainworld), None)
                if mainworld:
                    # System dot: solid black circle
                    svg += f'<circle cx="{x}" cy="{y}" r="3.5" class="classic-world-dot" />\n'
                    
                    # Gas giant indicator: concentric outer ring
                    if system.gas_giant_count > 0:
                        svg += f'<circle cx="{x}" cy="{y}" r="6.5" class="classic-gas-ring" />\n'
                        
                    # Bases: star and triangle
                    base_str = ""
                    if "Naval" in system.bases or "Zhodani Naval" in system.bases:
                        base_str += "★"
                    if "Scout" in system.bases:
                        base_str += "▲"
                    if "Military" in system.bases or "Zhodani Base" in system.bases:
                        base_str += "■"
                    if base_str:
                        svg += f'<text x="{x - 14}" y="{y - 4}" class="classic-base">{base_str}</text>\n'
                    if system.allegiance:
                        svg += f'<text x="{x + 12}" y="{y - 4}" class="classic-text classic-alleg">{html.escape(str(system.allegiance))}</text>\n'
                        
                    # World name in ALL CAPS under center
                    world_name = mainworld.name.upper()[:11]
                    svg += f'<text x="{x}" y="{y + 11}" class="classic-text">{html.escape(world_name)}</text>\n'
                    
                    # UWP under name
                    svg += f'<text x="{x}" y="{y + 18}" class="classic-text classic-uwp">{html.escape(str(mainworld.uwp))}</text>\n'
            
            svg += '</g>\n'

    # 3. Outer Grid Bounding Frame & Labels
    svg += f'<rect x="{left_padding}" y="{top_padding}" width="{grid_width}" height="{grid_height}" class="grid-border" />\n'
    
    # Labels across top and bottom
    for col in range(grid_cols):
        cx = col * col_width + hex_radius + left_padding
        svg += f'<text x="{cx}" y="{top_padding - 12}" class="grid-label">{subsector_col * 8 + col + 1:02d}</text>\n'
        svg += f'<text x="{cx}" y="{top_padding + grid_height + 12}" class="grid-label">{subsector_col * 8 + col + 1:02d}</text>\n'
        
    # Labels down sides
    for row in range(grid_rows):
        cy = row * row_height + row_height / 2 + top_padding
        svg += f'<text x="{left_padding - 15}" y="{cy}" class="grid-label">{subsector_row * 10 + row + 1:02d}</text>\n'
        svg += f'<text x="{left_padding + grid_width + 15}" y="{cy}" class="grid-label">{subsector_row * 10 + row + 1:02d}</text>\n'
        
    svg += '</svg>'
    return svg
