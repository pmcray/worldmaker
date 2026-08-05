import pandas as pd
from typing import List, Dict, Any

from .classes import StellarSystem, Sector, PlanetaryBody
from .utils import Utils
from .t5 import export_sector_t5_column, export_sector_t5_tab

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

def create_sector_dataframe(sector: Sector) -> pd.DataFrame:
    """One row per system in a sector: the map's own table, sortable and
    filterable. Includes the count of inhabited secondary worlds, which the
    UWP alone never shows."""
    from .t5 import t5_bases, t5_pbg, t5_stellar

    rows = []
    for hex_coord in sorted(sector.systems):
        system = sector.systems[hex_coord]
        mainworld = system.mainworld
        if mainworld is None:
            continue

        secondaries = [b for b in system.all_bodies
                       if getattr(b, 'is_secondary_world', False)]
        rows.append({
            "Hex": hex_coord,
            "Name": mainworld.name or system.name,
            "UWP": str(mainworld.uwp),
            "Bases": t5_bases(system),
            "Zone": system.travel_zone,
            "Allegiance": system.allegiance,
            "PBG": t5_pbg(system),
            "Trade codes": " ".join(mainworld.trade_codes),
            "Stars": t5_stellar(system),
            "Worlds": len(system.all_worlds),
            "Inhabited": 1 + len(secondaries),
            "Pop": mainworld.total_population,
            "Hab": mainworld.habitability_rating,
            "Temp K": mainworld.mean_temperature,
            "Nations": getattr(mainworld, 'nation_count', 0),
        })
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
    """Column-exact Traveller5 Second Survey sector data, as accepted by
    travellermap.com. See worldmaker.t5 for the format and the field
    derivations."""
    return export_sector_t5_column(sector)
