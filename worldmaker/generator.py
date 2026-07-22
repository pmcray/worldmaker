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
    generate_life
)
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
    calculate_available_orbits(system, model='physics')
    calculate_baseline_and_spread(system)
    handle_anomalies_and_empties(system)
    
    # Generate slots
    orbital_slots = generate_orbital_slots(system)
    
    # Phase 3: World Placement
    place_worlds(system, orbital_slots)
    
    # Phase 4: Detailing
    detail_placed_worlds(system)
    
    # Designate a mainworld among Terrestrial bodies (typically the most habitable or first)
    terrestrial_worlds = [w for w in system.all_worlds if w.body_type == 'Terrestrial']
    mainworld = None
    if terrestrial_worlds:
        mainworld = terrestrial_worlds[0] # Pick the first terrestrial as mainworld
        mainworld.is_mainworld = True
        # Generate full society UWP for mainworld
        mainworld.uwp = generate_mainworld_uwp(population_dm)
        mainworld.size_code = mainworld.uwp.size
        mainworld.atmosphere_code = mainworld.uwp.atmosphere
        mainworld.hydrographics_code = mainworld.uwp.hydrographics
        
        # Calculate WBH 6-field technological matrix
        generate_expanded_tech_matrix(mainworld.uwp, mainworld)
    
    for world in system.all_worlds:
        if world.body_type == 'Terrestrial':
            size_val = Utils.from_eHex(world.size_code)
            if not world.atmosphere_code:
                atm_val = generate_atmosphere(size_val)
                world.atmosphere_code = Utils.eHex(atm_val)
            else:
                atm_val = Utils.from_eHex(world.atmosphere_code)

            if not world.hydrographics_code:
                hydro_val = generate_hydrographics(size_val, atm_val)
                world.hydrographics_code = Utils.eHex(hydro_val)

            generate_geophysics(world, system)
            generate_rotation_period(world, system)
            world.mean_temperature = calculate_mean_temperature(world, system)
            world.surface_features = generate_surface_features(world)
            world.life_details = generate_life(world)
            generate_trade_codes(world)
            if world.is_mainworld:
                generate_social_details(world)

        # Detail Satellites
        for sat in world.satellites:
            if sat.size_code in ['S', 'R']: continue
            
            tilt_roll = Utils.D6(2)
            sat.axial_tilt = DATA['axial_tilt'].get(min(10, max(2, tilt_roll)))()
            sat.rotation_period_hours = Utils.D6(2) * 24
            
            # Physics-based temperature for satellites
            sat.mean_temperature = calculate_mean_temperature(sat, system)
            sat.surface_features = generate_surface_features(sat)
            sat.life_details = generate_life(sat)
            generate_trade_codes(sat)

    assign_final_designations(system)
    flag_points_of_interest(system)

    return system
