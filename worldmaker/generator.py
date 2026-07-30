import random
import math
from typing import List, Dict, Any, Tuple, Optional

from .classes import StellarSystem, PlanetaryBody, Satellite, UWP
from .utils import Utils
from .data import DATA
from .stellar import generate_stellar_system_stars, generate_world_name
from .system import (
    determine_world_counts,
    calculate_available_orbits,
    calculate_baseline_and_spread,
    handle_anomalies_and_empties,
    generate_orbital_slots,
    place_worlds
)
from .geophysics import (
    detail_placed_worlds,
    generate_atmosphere,
    generate_hydrographics,
    generate_geophysics,
    generate_rotation_period,
    calculate_mean_temperature,
    generate_surface_features,
    generate_life,
    place_satellites,
    calculate_habitability_rating,
    assign_climate_zone
)
from .atmosphere import generate_atmosphere_details, refresh_scale_height
from .temperature import detail_temperatures
from .economics import generate_economics
from .government import generate_government_details
from .society import (
    generate_mainworld_uwp,
    generate_trade_codes,
    generate_social_details,
    generate_expanded_tech_matrix
)

def _to_roman_numeral(num: int) -> str:
    """Converts an integer to a Roman numeral string."""
    if num <= 0: return str(num)
    roman_map = {
        1000: 'M', 900: 'CM', 500: 'D', 400: 'CD', 100: 'C', 90: 'XC',
        50: 'L', 40: 'XL', 10: 'X', 9: 'IX', 5: 'V', 4: 'IV', 1: 'I'
    }
    roman_numeral = ""
    for value, numeral in roman_map.items():
        while num >= value:
            roman_numeral += numeral
            num -= value
    return roman_numeral

def assign_final_designations(system: StellarSystem):
    """Assigns standard Traveller designations to all bodies."""
    for star_group in system.stars:
        if star_group.is_composite: continue
        
        planet_counter = 1
        belt_counter = 1
        star_group.orbiting_bodies.sort(key=lambda x: x.orbit_num)
        
        for world in star_group.orbiting_bodies:
            if world.body_type == 'Planetoid Belt':
                world.designation = f"{star_group.designation} P{_to_roman_numeral(belt_counter)}"
                belt_counter += 1
            elif world.body_type in ['Terrestrial', 'Gas Giant']:
                world.designation = f"{star_group.designation} {_to_roman_numeral(planet_counter)}"
                planet_counter += 1
                
            # Designate moons
            moon_char_code = ord('a')
            for satellite in world.satellites:
                satellite.designation = f"{world.designation} {chr(moon_char_code)}"
                moon_char_code += 1

def flag_points_of_interest(system: StellarSystem):
    """Analyzes the generated system to flag points of interest."""
    primary_group = system.primary_star
    if not primary_group: return

    hz_min = primary_group.hzco - 1.0
    hz_max = primary_group.hzco + 1.0

    for world in system.all_worlds:
        if world.notes and 'Anomalous' in world.notes[0]:
            world.notes.append("Point of Interest: Anomalous orbit.")
            
        for satellite in world.satellites:
            is_large_moon = False
            try:
                if satellite.size_code.isdigit() and int(satellite.size_code) >= 4:
                    is_large_moon = True
            except ValueError:
                pass
            
            if is_large_moon and hz_min <= world.orbit_num <= hz_max:
                satellite.notes.append("Point of Interest: Large moon in Habitable Zone. Mainworld Candidate.")
                world.notes.append(f"Candidate moon {satellite.designation}")

def generate_short_profile(system: StellarSystem) -> str:
    """Generates a concise system summary in G-P-T-N-S format."""
    g = system.gas_giant_count
    p = system.planetoid_belt_count
    t = system.terrestrial_planet_count
    n = system.baseline_number
    s = round(system.spread, 1)
    return f"{g}-{p}-{t}-{n}-{s}"

def generate_long_profile(system: StellarSystem) -> str:
    """Generates a detailed system summary showing world types in orbital sequence."""
    profile_parts = []
    for star_group in system.stars:
        if star_group.is_composite: continue
        
        star_profile = f"{star_group.designation}-"
        world_types = []
        for world in star_group.orbiting_bodies:
            if world.body_type == 'Terrestrial':
                world_types.append('T')
            elif world.body_type == 'Gas Giant':
                world_types.append('G')
            elif world.body_type == 'Planetoid Belt':
                world_types.append('P')
            elif world.body_type == 'Empty':
                world_types.append('E')
        star_profile += '-'.join(world_types)
        profile_parts.append(star_profile)
    return ':'.join(profile_parts)

def generate_full_system(name="Random System", population_dm=0) -> StellarSystem:
    """Main function to orchestrate the entire stellar system generation process."""
    system = StellarSystem(name=name)
    
    # Phase 1: Stellar Generation
    generate_stellar_system_stars(system)
    
    # Phase 2: System Architecture & Population
    determine_world_counts(system)
    calculate_available_orbits(system, model='simple')
    calculate_baseline_and_spread(system)
    handle_anomalies_and_empties(system)
    
    # Generate slots
    orbital_slots = generate_orbital_slots(system)
    
    # Phase 3: World Placement
    place_worlds(system, orbital_slots)
    
    # Phase 4: Detailing
    detail_placed_worlds(system)
    
    # Phase 5: Physical detailing of every world, before any mainworld is
    # chosen - the choice depends on the physical results (WBH p.133).
    for world in system.all_worlds:
        if world.body_type == 'Terrestrial':
            size_val = Utils.from_eHex(world.size_code)
            atm_val = generate_atmosphere(size_val)
            world.atmosphere_code = Utils.eHex(atm_val)
            hydro_val = generate_hydrographics(size_val, atm_val)
            world.hydrographics_code = Utils.eHex(hydro_val)

            generate_geophysics(world, system)
            generate_rotation_period(world, system)
            # Atmosphere pressure first (albedo and greenhouse depend on it),
            # then the full temperature chain, then the values that depend on
            # the final temperature.
            generate_atmosphere_details(world)
            detail_temperatures(world, system)
            refresh_scale_height(world)
            assign_climate_zone(world)
            world.surface_features = generate_surface_features(world)
            world.life_details = generate_life(world)
            world.habitability_rating = calculate_habitability_rating(world, system)

        # Place and detail satellites
        place_satellites(world, system)
        for sat in world.satellites:
            if sat.is_ring or sat.size_code == 'S':
                continue

            tilt_roll = Utils.D6(2)
            sat.axial_tilt = DATA['axial_tilt'].get(min(10, max(2, tilt_roll)))()
            sat.rotation_period_hours = Utils.D6(2) * 24

            generate_atmosphere_details(sat)
            detail_temperatures(sat, system, is_moon=True)
            refresh_scale_height(sat)
            assign_climate_zone(sat)
            sat.surface_features = generate_surface_features(sat)
            sat.life_details = generate_life(sat)
            sat.habitability_rating = calculate_habitability_rating(sat, system)

    # Phase 6: Final mainworld determination (WBH p.133). Candidates are
    # terrestrial worlds and significant moons; the most habitable wins, with
    # resource rating breaking ties.
    mainworld = select_mainworld(system)
    if mainworld is not None:
        mainworld.is_mainworld = True
        # The UWP describes the world that was actually generated: Size,
        # Atmosphere and Hydrographics come from its physical characteristics,
        # and only the social codes are rolled here.
        mainworld.uwp = generate_mainworld_uwp(
            population_dm,
            size=Utils.from_eHex(mainworld.size_code),
            atmosphere=Utils.from_eHex(mainworld.atmosphere_code),
            hydrographics=Utils.from_eHex(mainworld.hydrographics_code),
        )
        generate_expanded_tech_matrix(mainworld.uwp, mainworld)
        generate_economics(mainworld)
        generate_government_details(mainworld)
        generate_social_details(mainworld)

    for world in system.all_worlds:
        if world.body_type == 'Terrestrial':
            generate_trade_codes(world)
        for sat in world.satellites:
            if not sat.is_ring:
                generate_trade_codes(sat)

    assign_final_designations(system)
    flag_points_of_interest(system)

    return system

def select_mainworld(system: StellarSystem):
    """Chooses the system mainworld by the WBH p.133 criteria: highest
    habitability rating, then highest resource rating. Significant moons are
    eligible alongside planets."""
    candidates = []
    for world in system.all_worlds:
        # Planetoid belts are legitimate mainworlds - Charted Space is full of
        # asteroid-belt settlements - but they are never habitable, so they win
        # only where nothing better exists.
        if world.body_type in ('Terrestrial', 'Planetoid Belt'):
            candidates.append(world)
        for sat in world.satellites:
            # Significant moons only: Size 1+ bodies, not rings or specks
            if sat.is_ring or sat.size_code in ('S', 'R', ''):
                continue
            if Utils.from_eHex(sat.size_code) >= 1:
                candidates.append(sat)

    if not candidates:
        # A gas-giant-only system still needs a body to carry the UWP
        return system.all_worlds[0] if system.all_worlds else None

    return max(candidates,
               key=lambda w: (getattr(w, 'habitability_rating', 0),
                              getattr(w, 'resource_rating', 0)))
