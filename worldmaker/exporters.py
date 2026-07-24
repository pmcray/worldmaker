import pandas as pd
from typing import List, Dict, Any

from .classes import StellarSystem, Sector, PlanetaryBody
from .utils import Utils
from .adventure import generate_system_adventure_seeds

def create_system_dataframe(system: StellarSystem) -> pd.DataFrame:
    """Creates a Pandas DataFrame summarizing all worlds in a stellar system ( Sol System Overview style)."""
    rows = []
    
    # Traverse through stars and worlds in orbital sequence
    for star in system.stars:
        if star.is_composite: continue
        
        for world in star.orbiting_bodies:
            uwp_str = str(world.uwp) if world.uwp.starport else "N/A"
            moons_count = len([s for s in world.satellites if not s.is_ring])
            rings_count = len([s for s in world.satellites if s.is_ring])
            
            sat_summary = []
            if moons_count > 0: sat_summary.append(f"{moons_count} Moons")
            if rings_count > 0: sat_summary.append("Rings")
            sat_str = ", ".join(sat_summary) if sat_summary else "None"
            
            # Expanded tech sub-fields
            tech_matrix = f"S:{world.uwp.tl_spaceflight} E:{world.uwp.tl_energy} T:{world.uwp.tl_transport} M:{world.uwp.tl_medical} V:{world.uwp.tl_environment} P:{world.uwp.tl_personal}" if world.is_mainworld else "N/A"
            
            row = {
                "Primary Star": star.designation,
                "Designation": world.designation,
                "Name": world.name,
                "Type": world.body_type,
                "Orbit#": world.orbit_num,
                "AU": round(world.orbit_au, 4),
                "Eccentricity": world.eccentricity,
                "Period (Yr)": round(world.period_years, 3),
                "UWP": uwp_str,
                "Sub-Tech Matrix": tech_matrix,
                "Satellites": sat_str,
                "Density": world.density,
                "Gravity (G)": world.gravity,
                "Mean Temp (K)": world.mean_temperature,
                "Climate": world.climate_zone if world.body_type == 'Terrestrial' else "N/A"
            }
            rows.append(row)
            
            # Add major moons as sub-rows if desired
            for sat in world.satellites:
                if sat.is_ring: continue
                sat_uwp = str(sat.uwp) if sat.uwp.starport else "N/A"
                row_sat = {
                    "Primary Star": star.designation,
                    "Designation": sat.designation,
                    "Name": f"↳ Moon: {sat.size_code}",
                    "Type": "Satellite",
                    "Orbit#": "",
                    "AU": "",
                    "Eccentricity": "",
                    "Period (Yr)": "",
                    "UWP": sat_uwp,
                    "Sub-Tech Matrix": "",
                    "Satellites": "",
                    "Density": sat.density,
                    "Gravity (G)": round(sat.gravity, 2),
                    "Mean Temp (K)": round(sat.mean_temperature, 1),
                    "Climate": "N/A"
                }
                rows.append(row_sat)
                
    return pd.DataFrame(rows)

def export_system_markdown(system: StellarSystem) -> str:
    """Returns a highly detailed markdown dossier for a stellar system including advanced WBH outputs."""
    md = []
    md.append(f"# Stellar Dossier: {system.name}")
    md.append(f"* **Estimated Age**: {system.age_gyr} Gyr")
    md.append(f"* **Stellar Configuration**: {', '.join([f'{s.designation} ({s.spectral_type})' for s in system.stars if not s.is_composite])}")
    md.append("")
    
    md.append("## Star Breakdown")
    for star in system.stars:
        if star.is_composite: continue
        md.append(f"### Star {star.designation} ({star.spectral_type})")
        md.append(f"* **Mass**: {round(star.mass, 3)} Solar Masses")
        md.append(f"* **Diameter**: {round(star.diameter, 3)} Solar Diameters")
        md.append(f"* **Luminosity**: {round(star.luminosity, 4)} Solar Luminosities")
        md.append(f"* **Temperature**: {int(star.temp_k)} K")
        md.append(f"* **Habitable Zone Center Orbit (HZCO)**: Orbit {round(star.hzco, 2)} ({round(Utils.orbit_to_au(star.hzco), 3)} AU)")
        md.append(f"* **Minimum Allowable Orbit (MAO)**: Orbit {round(star.mao, 2)}")
        md.append("")

    md.append("## Planetary Bodies Profile")
    for world in system.all_worlds:
        md.append(f"### {world.designation}: {world.name} ({world.body_type})")
        md.append(f"* **Orbit #**: {world.orbit_num} ({round(world.orbit_au, 4)} AU)")
        md.append(f"* **Eccentricity**: {world.eccentricity}")
        md.append(f"* **Period**: {round(world.period_years, 3)} standard years")
        
        if world.body_type == 'Terrestrial':
            md.append(f"* **Physical Statistics**:")
            md.append(f"  * Size Code: {world.size_code} ({int(world.diameter_km)} km diameter)")
            md.append(f"  * Composition/Core: {world.core_composition} (Density: {world.density} Earth average)")
            md.append(f"  * Surface Gravity: {world.gravity} G (Escape Velocity: {world.escape_velocity_kms} km/s)")
            md.append(f"  * Gases Retained: {', '.join(world.gases_retained)}")
            md.append(f"  * Rotation Period (Day Length): {world.rotation_period_hours} hours")
            md.append(f"  * Axial Tilt: {round(world.axial_tilt, 1)} degrees")
            md.append(f"  * Climate Zone: {world.climate_zone} (Mean Equilibrium Temperature: {world.mean_temperature} K)")
            md.append(f"  * Primary Biomes: {', '.join(world.biomes)}")
            md.append(f"  * Surface Hydrology: {world.surface_features}")
            md.append(f"  * Biosphere Rating: {world.life_details}")
            
            if world.is_mainworld:
                md.append(f"* **Mainworld Universal World Profile**: `{world.uwp}`")
                md.append(f"  * Trade Codes: `{', '.join(world.trade_codes)}`")
                md.append(f"  * Expanded 6-Field Technology levels:")
                md.append(f"    * Spaceflight: TL {world.uwp.tl_spaceflight}")
                md.append(f"    * Energy: TL {world.uwp.tl_energy}")
                md.append(f"    * Transport: TL {world.uwp.tl_transport}")
                md.append(f"    * Medical: TL {world.uwp.tl_medical}")
                md.append(f"    * Environment: TL {world.uwp.tl_environment}")
                md.append(f"    * Personal Gear: TL {world.uwp.tl_personal}")
        
        elif world.body_type == 'Gas Giant':
            md.append(f"* **Jovian Statistics**:")
            md.append(f"  * Category: {world.size_code[:2]} (Size Code: {world.size_code[2:]})")
            md.append(f"  * Mass: {world.mass_terran} Earth masses")
            md.append(f"  * Estimated Diameter: {int(world.diameter_km)} km")
            
        if world.satellites:
            md.append(f"* **Satellite System ({len(world.satellites)} bodies)**:")
            for sat in world.satellites:
                ring_marker = " (Ring System)" if sat.is_ring else ""
                sat_uwp = f" - UWP: `{sat.uwp}`" if sat.uwp.starport and not sat.is_ring else ""
                md.append(f"  * {sat.designation}: Size {sat.size_code}{ring_marker}{sat_uwp}")
                if sat.notes:
                    md.append(f"    * *Notes*: {'; '.join(sat.notes)}")
        
        if world.notes:
            md.append(f"* **Notes/POI**:")
            for note in world.notes:
                md.append(f"  * *{note}*")
        md.append("")
        
    return "\n".join(md)

def export_sector_sec_file(sector: Sector) -> str:
    """Returns standard Travellermap-compliant .sec file data lines."""
    lines = []
    # Header format
    lines.append(f"# Sector Data for {sector.name}")
    lines.append("# Hex Name         UWP       Bases   Allegiance  Notes")
    lines.append("# ---- ------------ --------- ------- ----------- -----")
    
    for hex_coord, system in sector.systems.items():
        mainworld = next((w for w in system.all_worlds if w.is_mainworld), None)
        if not mainworld: continue
        
        # Format spacing to match standard .sec layout
        # Col 1: Hex (4 chars)
        # Col 6: Name (12 chars)
        # Col 19: UWP (9 chars)
        # Col 29: Bases (2 chars)
        # Col 37: Allegiance (2 chars)
        name_str = system.name.ljust(12)
        uwp_str = str(mainworld.uwp).ljust(9)
        
        base_char = ""
        if "Naval" in system.bases or "Zhodani Naval" in system.bases: base_char += "N"
        if "Scout" in system.bases: base_char += "S"
        base_str = base_char.ljust(7)
        
        alleg_str = system.allegiance.ljust(11)
        
        tcodes_str = " ".join(mainworld.trade_codes)
        
        lines.append(f"{hex_coord} {name_str} {uwp_str} {base_str} {alleg_str} {tcodes_str}")
        
    return "\n".join(lines)

def export_system_html(system: StellarSystem) -> str:
    """Returns a rich, CSS-styled HTML card presentation of a stellar system suitable for IPython/Jupyter rendering."""
    primary = system.primary_star
    mainworld = next((w for w in system.all_worlds if w.is_mainworld), None)
    
    html = []
    html.append("""
<style>
.tm-container {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #0f172a;
    color: #f8fafc;
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
    max-width: 900px;
    margin: 16px auto;
    border: 1px solid #1e293b;
}
.tm-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 2px solid #334155;
    padding-bottom: 16px;
    margin-bottom: 20px;
}
.tm-title {
    font-size: 1.65rem;
    font-weight: 700;
    color: #38bdf8;
    margin: 0;
}
.tm-subtitle {
    font-size: 0.9rem;
    color: #94a3b8;
    margin-top: 4px;
}
.tm-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-right: 6px;
}
.badge-blue { background: #0284c7; color: #fff; }
.badge-green { background: #16a34a; color: #fff; }
.badge-purple { background: #9333ea; color: #fff; }
.badge-amber { background: #d97706; color: #fff; }
.badge-rose { background: #e11d48; color: #fff; }

.tm-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 16px;
    margin-bottom: 20px;
}
.tm-card {
    background: #1e293b;
    border-radius: 8px;
    padding: 16px;
    border: 1px solid #334155;
}
.tm-card-title {
    font-size: 1.05rem;
    font-weight: 600;
    color: #f1f5f9;
    margin-top: 0;
    margin-bottom: 12px;
    border-bottom: 1px solid #334155;
    padding-bottom: 6px;
}
.tm-uwp-display {
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: 1.4rem;
    letter-spacing: 3px;
    color: #38bdf8;
    background: #0f172a;
    padding: 8px 12px;
    border-radius: 6px;
    display: inline-block;
    margin: 8px 0;
    border: 1px solid #0284c7;
}
.tm-tech-bar-container {
    margin: 6px 0;
}
.tm-tech-label {
    display: flex;
    justify-content: space-between;
    font-size: 0.8rem;
    color: #cbd5e1;
    margin-bottom: 2px;
}
.tm-tech-bar {
    height: 6px;
    background: #334155;
    border-radius: 3px;
    overflow: hidden;
}
.tm-tech-fill {
    height: 100%;
    background: linear-gradient(90deg, #38bdf8, #818cf8);
}
.tm-alert {
    background: rgba(245, 158, 11, 0.15);
    border-left: 4px solid #f59e0b;
    padding: 10px 14px;
    border-radius: 4px;
    color: #fbbf24;
    font-size: 0.85rem;
    margin-bottom: 16px;
}
.tm-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;
    margin-top: 12px;
}
.tm-table th {
    background: #1e293b;
    color: #94a3b8;
    text-align: left;
    padding: 10px;
    border-bottom: 2px solid #334155;
}
.tm-table td {
    padding: 10px;
    border-bottom: 1px solid #334155;
    color: #e2e8f0;
}
.tm-table tr:hover {
    background: #1e293b;
}
</style>
""")

    html.append('<div class="tm-container">')
    
    # Header
    html.append('  <div class="tm-header">')
    html.append('    <div>')
    html.append(f'      <h2 class="tm-title">System: {system.name}</h2>')
    short_prof = f"{system.gas_giant_count}-{system.planetoid_belt_count}-{system.terrestrial_planet_count}-{system.baseline_number}-{round(system.spread, 1)}"
    html.append(f'      <div class="tm-subtitle">Stellar Age: {system.age_gyr} Gyr &bull; Profile: <code>{short_prof}</code></div>')
    html.append('    </div>')
    html.append('    <div>')
    html.append(f'      <span class="tm-badge badge-blue">Allegiance: {system.allegiance}</span>')
    if system.bases:
        for b in system.bases:
            html.append(f'      <span class="tm-badge badge-purple">{b} Base</span>')
    html.append('    </div>')
    html.append('  </div>')

    # POI Alert
    poi_notes = [w.notes for w in system.all_worlds if w.notes]
    if poi_notes:
        html.append('  <div class="tm-alert">')
        html.append('    <strong>Points of Interest Flagged:</strong><br>')
        for notes in poi_notes:
            for n in notes:
                html.append(f'    &bull; {n}<br>')
        html.append('  </div>')

    # Grid Section: Primary Star & Mainworld
    html.append('  <div class="tm-grid">')

    # Card 1: Primary Star
    html.append('    <div class="tm-card">')
    html.append('      <h3 class="tm-card-title">Stellar Primary</h3>')
    if primary:
        html.append(f'      <div><strong>Spectral Type:</strong> <span class="tm-badge badge-amber">{primary.spectral_type}</span></div>')
        html.append(f'      <div style="margin-top:8px;"><strong>Mass:</strong> {round(primary.mass, 3)} M<sub>&odot;</sub></div>')
        html.append(f'      <div><strong>Luminosity:</strong> {round(primary.luminosity, 4)} L<sub>&odot;</sub></div>')
        html.append(f'      <div><strong>Habitable Zone (HZCO):</strong> Orbit {round(primary.hzco, 2)} ({round(Utils.orbit_to_au(primary.hzco), 2)} AU)</div>')
        html.append(f'      <div><strong>Minimum Orbit (MAO):</strong> Orbit {round(primary.mao, 2)}</div>')
    html.append('    </div>')

    # Card 2: Mainworld UWP & Trade Codes
    html.append('    <div class="tm-card">')
    html.append('      <h3 class="tm-card-title">Mainworld Profile</h3>')
    if mainworld and mainworld.uwp:
        uwp = mainworld.uwp
        html.append(f'      <div><strong>Designation:</strong> {mainworld.designation} ({mainworld.name})</div>')
        html.append(f'      <div class="tm-uwp-display">{uwp.uwp_string}</div>')
        
        # Trade Codes Badges
        if mainworld.trade_codes:
            html.append('<div style="margin-top:6px;">')
            for tc in mainworld.trade_codes:
                html.append(f'<span class="tm-badge badge-green">{tc}</span>')
            html.append('</div>')
    else:
        html.append('<div>No Mainworld Established</div>')
    html.append('    </div>')

    # Card 3: Expanded Tech Matrix
    if mainworld and mainworld.uwp:
        uwp = mainworld.uwp
        html.append('    <div class="tm-card">')
        html.append('      <h3 class="tm-card-title">Expanded Tech Matrix (WBH)</h3>')

        techs = [
            ("Spaceflight", uwp.tl_spaceflight),
            ("Energy", uwp.tl_energy),
            ("Transport", uwp.tl_transport),
            ("Medical", uwp.tl_medical),
            ("Environment", uwp.tl_environment),
            ("Personal Gear", uwp.tl_personal)
        ]
        for name, val in techs:
            pct = min(100, int((val / 16) * 100))
            html.append('      <div class="tm-tech-bar-container">')
            html.append(f'        <div class="tm-tech-label"><span>{name}</span><span>TL {val}</span></div>')
            html.append(f'        <div class="tm-tech-bar"><div class="tm-tech-fill" style="width: {pct}%;"></div></div>')
            html.append('      </div>')
        html.append('    </div>')

    # Card 4: Adventure Seeds & Starport Rumors (WBH Ch. 15)
    adv = generate_system_adventure_seeds(system)
    html.append('    <div class="tm-card">')
    html.append('      <h3 class="tm-card-title">Adventure Seeds & Rumors (WBH Ch. 15)</h3>')
    
    if adv["starport_rumors"]:
        html.append('      <div style="font-size:0.85rem; color:#e2e8f0; margin-bottom:8px;"><strong>Starport Rumors:</strong></div>')
        for r in adv["starport_rumors"]:
            html.append(f'      <div style="font-size:0.8rem; color:#cbd5e1; margin-bottom:4px;">&bull; <em>"{r}"</em></div>')

    if adv["plot_hooks"]:
        html.append('      <div style="font-size:0.85rem; color:#e2e8f0; margin-top:8px; margin-bottom:4px;"><strong>Referee Plot Hooks:</strong></div>')
        for h in adv["plot_hooks"]:
            html.append(f'      <div style="font-size:0.8rem; color:#38bdf8; margin-bottom:4px;">&bull; {h}</div>')

    html.append('    </div>')

    html.append('  </div>') # End tm-grid

    # Table of All Orbits & Satellites
    html.append('  <h3 style="color:#f1f5f9; margin-top:20px; font-size:1.1rem;">System Orbital Architecture</h3>')
    html.append('  <table class="tm-table">')
    html.append('    <thead><tr><th>Designation</th><th>Name</th><th>Type</th><th>Orbit#</th><th>AU</th><th>Period (Yr)</th><th>UWP / Details</th><th>Satellites</th></tr></thead>')
    html.append('    <tbody>')

    for world in system.all_worlds:
        uwp_display = f"<code>{world.uwp}</code>" if world.uwp and world.uwp.starport else world.body_type
        moons = [s for s in world.satellites if not s.is_ring]
        rings = [s for s in world.satellites if s.is_ring]
        sat_text = f"{len(moons)} moons" if moons else "—"
        if rings: sat_text += " + rings"

        row_style = ' style="font-weight:600; background:rgba(2, 132, 199, 0.1);"' if world.is_mainworld else ""
        html.append(f'    <tr{row_style}>')
        html.append(f'      <td>{world.designation}</td>')
        html.append(f'      <td>{world.name}</td>')
        html.append(f'      <td>{world.body_type}</td>')
        html.append(f'      <td>{world.orbit_num}</td>')
        html.append(f'      <td>{round(world.orbit_au, 3)}</td>')
        html.append(f'      <td>{round(world.period_years, 2)}</td>')
        html.append(f'      <td>{uwp_display}</td>')
        html.append(f'      <td>{sat_text}</td>')
        html.append('    </tr>')

        # Sub-rows for satellites
        for sat in world.satellites:
            sat_uwp = f"<code>{sat.uwp}</code>" if sat.uwp and sat.uwp.starport else f"Size {sat.size_code}"
            html.append(f'    <tr style="color:#94a3b8; font-size:0.8rem;">')
            html.append(f'      <td style="padding-left:20px;">↳ {sat.designation}</td>')
            html.append(f'      <td>Satellite</td>')
            html.append(f'      <td>Moon</td>')
            html.append(f'      <td>—</td>')
            html.append(f'      <td>—</td>')
            html.append(f'      <td>—</td>')
            html.append(f'      <td>{sat_uwp}</td>')
            html.append(f'      <td>—</td>')
            html.append('    </tr>')

    html.append('    </tbody>')
    html.append('  </table>')
    html.append('</div>')

    return "".join(html)

