import random
import math
from typing import List, Dict, Any, Tuple, Optional

from .classes import UWP, Satellite, PlanetaryBody, StellarSystem
from .utils import Utils
from .data import DATA
from .stellar import generate_world_name

def generate_atmosphere(size: int) -> int:
    """Generates atmosphere code."""
    if size == 0:
        return 0
    return max(0, Utils.D6(2) - 7 + size)

def generate_hydrographics(size: int, atmosphere: int) -> int:
    """Generates hydrographics code."""
    if size <= 1:
        return 0
    hydro = Utils.D6(2) - 7 + atmosphere
    if atmosphere <= 1 or atmosphere >= 10:
        hydro -= 4
    return max(0, min(10, hydro))

def calculate_mean_temperature(world: Any, system: StellarSystem) -> float:
    """Calculates the physics-based mean temperature of a world in Kelvin (thermodynamic feedback)."""
    # Albedo calculation: ice/desert has high albedo, oceans have low albedo
    albedo = 0.3
    if hasattr(world, 'hydrographics_code') and world.hydrographics_code:
        hydro_val = Utils.from_eHex(world.hydrographics_code)
        if hydro_val > 5:
            albedo = 0.2  # Ocean absorption
        elif hydro_val < 2:
            albedo = 0.4  # Ice/dry rock reflection

    # Greenhouse factor calculation based on atmosphere thickness and composition
    greenhouse_factor = 0.0
    if hasattr(world, 'atmosphere_code') and world.atmosphere_code:
        atm_val = Utils.from_eHex(world.atmosphere_code)
        if atm_val in [4, 5, 14]: # Thin / Low pressure
            greenhouse_factor = 0.05
        elif atm_val in [6, 7, 8, 9]: # Standard / Dense
            greenhouse_factor = 0.15 * (atm_val - 5)
        elif atm_val in [10, 11, 12]: # Exotic / Corrosive / High pressure
            greenhouse_factor = 0.8
        elif atm_val == 13: # Extremely dense (Venusian runaway)
            greenhouse_factor = 2.5
    
    # Get parent star and orbital distance
    parent_group = getattr(world, 'parent_star_group', None)
    distance = getattr(world, 'orbit_au', 0.0)
    if not parent_group and hasattr(world, 'parent_body') and world.parent_body:
        parent_group = getattr(world.parent_body, 'parent_star_group', None)
        distance = getattr(world.parent_body, 'orbit_au', 0.0)
        
    parent_star_group = next((s for s in system.stars if s.designation == parent_group), None)
    if not parent_star_group:
        return 200.0 # Cold default fallback
    
    luminosity = parent_star_group.luminosity

    if distance <= 0:
        return 100.0

    # Stefan-Boltzmann equilibrium temperature with greenhouse feedback
    temperature = 279 * (luminosity * (1 - albedo) * (1 + greenhouse_factor) / distance**2)**0.25
    return round(temperature, 1)

def generate_geophysics(world: PlanetaryBody, system: StellarSystem):
    """Generates expanded physical characteristics (density, gravity, escape velocity, core, gases)."""
    if world.body_type != 'Terrestrial':
        return

    # Density (WBH page 71)
    dm = 0
    size_val = Utils.from_eHex(world.size_code) if isinstance(world.size_code, str) else world.size_code
    if size_val <= 4: dm -= 1
    elif size_val >= 6: dm += 1
    
    comp_roll = Utils.D6(2) + dm
    comp_data = DATA['terrestrial_composition']['table'].get(min(15, max(2, comp_roll)))
    world.density = comp_data['density']
    world.core_composition = comp_data['comp']
    
    # Diameter
    if not world.diameter_km:
        world.diameter_km = size_val * 1600 # Simple average
    
    # Gravity = (Density x Diameter) / Diameter(Terra) (Earth radius ~6371km, Earth average density ~5.51 g/cm3)
    world.gravity = round((world.density * world.diameter_km) / 12742, 2)
    
    # Mass = Density * (Diameter / Diameter(Terra))^3
    world.mass_terran = round(world.density * (world.diameter_km / 12742)**3, 3)

    # Escape Velocity (v_e = sqrt(2 * G * M / R)) -> v_escape = 11.186 * sqrt(M / R)
    rad_ratio = (world.diameter_km / 12742)
    if rad_ratio > 0:
        world.escape_velocity_kms = round(11.186 * math.sqrt(world.mass_terran / rad_ratio), 2)
    else:
        world.escape_velocity_kms = 0.0

    # Molecular Gas Retention (physics approximation based on escape velocity)
    gases = []
    v_e = world.escape_velocity_kms
    if v_e >= 11.2:
        gases.extend(["Hydrogen", "Helium", "Water Vapor", "Nitrogen", "Oxygen", "Carbon Dioxide"])
    elif v_e >= 9.0:
        gases.extend(["Water Vapor", "Nitrogen", "Oxygen", "Carbon Dioxide", "Argon"])
    elif v_e >= 5.0:
        gases.extend(["Nitrogen", "Oxygen", "Carbon Dioxide", "Argon"])
    elif v_e >= 3.0:
        gases.extend(["Carbon Dioxide", "Xenon"])
    else:
        gases.append("None (Vacuum)")
    world.gases_retained = gases

    # Axial Tilt (page 104)
    tilt_roll = Utils.D6(2)
    tilt_func = DATA['axial_tilt'].get(min(10, max(2, tilt_roll)))
    world.axial_tilt = tilt_func()

    # Climate Zones and Biomes based on Temperature & Moisture
    temp = world.mean_temperature
    if temp < 200:
        world.climate_zone = "Cryogenic (Glacial)"
        world.biomes = ["Ice Cap", "Frozen Wasteland"]
    elif temp < 260:
        world.climate_zone = "Cold (Boreal)"
        world.biomes = ["Tundra", "Glacial Seas"]
    elif temp < 310:
        world.climate_zone = "Temperate"
        world.biomes = ["Grassland", "Forest", "Oceanic"] if Utils.from_eHex(world.hydrographics_code) > 3 else ["Steppe", "Dry Shrubland"]
    elif temp < 350:
        world.climate_zone = "Hot (Tropical)"
        world.biomes = ["Jungle", "Wetlands", "Warm Seas"] if Utils.from_eHex(world.hydrographics_code) > 4 else ["Savannah", "Arid Grassland"]
    else:
        world.climate_zone = "Torrid (Scorched)"
        world.biomes = ["Desert", "Volcanic Ashfields"]

    # Resource Rating (WBH p. 102)
    world.resource_rating = max(0, Utils.D6(2) - 7 + Utils.from_eHex(world.size_code))

def generate_rotation_period(world: PlanetaryBody, system: StellarSystem):
    """Generates the rotation period (day length) for a world."""
    if world.body_type == 'Planetoid Belt':
        return

    # Basic Day Length (page 103)
    dm = 0
    if system.age_gyr > 2.0:
        dm += int(system.age_gyr // 2)
    
    base_hours = (Utils.D6(2) - 2) * 4 + 2 + Utils.D6() + dm
    world.rotation_period_hours = base_hours
    
    # Simplified Tidal Lock check (page 105)
    if world.orbit_num < 1.0:
        if Utils.D6(2) >= 10:
            world.rotation_period_hours = round(world.period_years * 8766, 1) # Locked to star
            world.notes.append("Tidally Locked to Star")

def generate_surface_features(world: Any) -> str:
    """Generates a description of the world's surface features."""
    if not world.hydrographics_code or not str(world.hydrographics_code).isalnum():
        return "No hydrographics data."

    hydro_val = Utils.from_eHex(world.hydrographics_code)
    
    if hydro_val == 0:
        return "No surface water, desert world."
    elif hydro_val == 10:
        return "Water world, almost entirely covered in deep oceans."

    # WBH continental variance
    surface_dist_roll = Utils.D6(2) - 2
    
    if hydro_val > 5: # Ocean dominant
        if surface_dist_roll < 3:
            return f"{hydro_val*10}% water coverage. Archipelago-rich surface with small islands and mini-continents."
        elif surface_dist_roll < 7:
            return f"{hydro_val*10}% water coverage. Standard planetary distribution with several stable continents."
        else:
            return f"{hydro_val*10}% water coverage. Single massive super-continent surrounded by world oceans."
    else: # Land dominant
        if surface_dist_roll < 3:
            return f"{hydro_val*10}% water coverage. Highly dispersed surface water in major lakes and small rift seas."
        elif surface_dist_roll < 7:
            return f"{hydro_val*10}% water coverage. Continental blocks with several large seas."
        else:
            return f"{hydro_val*10}% water coverage. Single super-ocean pocket on a dry continent."

def generate_life(world: Any) -> str:
    """Generates a description of the world's biosystem (complex life/biomass index WBH p. 110)."""
    if not world.atmosphere_code or not str(world.atmosphere_code).isalnum():
        return "No life data."

    atm_val = Utils.from_eHex(world.atmosphere_code)

    if atm_val < 4 or atm_val > 9:
        return "No significant native life (untenable atmosphere)."

    biomass_rating = Utils.D6(2)
    biocomplexity_rating = max(0, Utils.D6(2) - 7 + biomass_rating)
    
    if hasattr(world, 'biomass_rating'):
        world.biomass_rating = biomass_rating
        world.biocomplexity_rating = biocomplexity_rating

    if biocomplexity_rating <= 2:
        desc = "Single-cell microbial life only."
    elif biocomplexity_rating <= 5:
        desc = "Simple multicellular structures, fungi-analogues, and basic plants."
    elif biocomplexity_rating <= 8:
        desc = "Complex fauna, basic animal lifeforms, and complex biomes."
    else:
        desc = "Extremely complex, diverse biosphere with complex ecosystems and high biohazard risk."

    return f"Biomass Code: {biomass_rating}, Biocomplexity Code: {biocomplexity_rating}. {desc}"

def detail_placed_worlds(system: StellarSystem):
    """Generates size and satellite details for all placed worlds."""
    for world in system.all_worlds:
        if world.body_type == 'Terrestrial':
            roll_1d = Utils.D6()
            roll_type = DATA['terrestrial_world_sizing']['1D_roll'][roll_1d]
            
            if roll_type == '1D':
                size_roll = DATA['terrestrial_world_sizing']['size_ranges']['1D'][Utils.D6()]
            elif roll_type == '2D':
                size_roll = DATA['terrestrial_world_sizing']['size_ranges']['2D'][Utils.D6(2)]
            else: # 2D+3
                size_roll = DATA['terrestrial_world_sizing']['size_ranges']['2D+3'][Utils.D6(2) + 3]
            world.size_code = Utils.eHex(size_roll)
        
        elif world.body_type == 'Gas Giant':
            category_roll = Utils.D6()
            if category_roll <= 2: category = 'GS'
            elif category_roll <= 4: category = 'GM'
            else: category = 'GL'
            
            d_roll = DATA['gas_giant_sizing'][category]['d_roll']()
            world.diameter_km = d_roll * 12800
            world.mass_terran = DATA['gas_giant_sizing'][category]['m_roll']()
            world.size_code = f"{category}{Utils.eHex(d_roll)}"
        
        elif world.body_type == 'Planetoid Belt':
            world.size_code = '0'
            
        # Generate Satellites (page 55)
        num_moons = 0
        dm_moons = 0

        if world.orbit_num < 1.0: dm_moons += -1

        if world.body_type == 'Terrestrial':
            size_val = Utils.from_eHex(world.size_code)
            if size_val <= 2: # Size 1-2
                num_moons = max(0, DATA['significant_moon_quantity']['planet_size_1_2']() + dm_moons)
            elif size_val <= 9: # Size 3-9
                num_moons = max(0, DATA['significant_moon_quantity']['planet_size_3_9']() + dm_moons)
            else: # Size A-F
                num_moons = max(0, DATA['significant_moon_quantity']['planet_size_a_f']() + dm_moons)
        elif 'G' in world.size_code:
            if 'GS' in world.size_code: # Small Gas Giant
                num_moons = max(0, DATA['significant_moon_quantity']['small_gas_giant']() + dm_moons)
            else: # Medium or Large Gas Giant
                num_moons = max(0, DATA['significant_moon_quantity']['medium_large_gas_giant']() + dm_moons)
        
        for i in range(num_moons):
            sat = Satellite(parent_body=world)
            size_roll = Utils.D6()
            if size_roll <= 3: sat.size_code = 'S'
            elif size_roll <= 5:
                r_roll = Utils.D3() - 1
                sat.size_code = 'R' if r_roll == 0 else str(r_roll)
                sat.is_ring = (r_roll == 0)
            else: # 1D roll of 6
                if world.body_type == 'Terrestrial':
                    size_val = Utils.from_eHex(world.size_code)
                    sat_size = max(0, size_val - 1 - Utils.D6())
                    sat.size_code = Utils.eHex(sat_size)
                elif 'G' in world.size_code:
                    sat_size = Utils.D6()
                    sat.size_code = Utils.eHex(sat_size)
            
            # Calculate physical details for moons
            if sat.size_code in ['S', 'R']:
                sat.diameter_km = 100 if sat.size_code == 'S' else 0
                sat.mass_terran = 0.0001
                if sat.size_code == 'S':
                    sat.uwp.size = 'S'
                    sat.uwp.atmosphere = '0'
                    sat.uwp.hydrographics = '0'
                else:
                    sat.uwp.size = '0'
                    sat.uwp.atmosphere = '0'
                    sat.uwp.hydrographics = '0'
            else:
                try:
                    size_val = Utils.from_eHex(sat.size_code)
                    sat.diameter_km = size_val * 1600
                    density = 0.8
                    sat.mass_terran = density * (sat.diameter_km / 12742)**3
                    sat.gravity = (density * sat.diameter_km) / 12742
                    
                    sat.uwp.size = sat.size_code
                    if size_val >= 1:
                        atm_val = generate_atmosphere(size_val)
                        sat.atmosphere_code = Utils.eHex(atm_val)
                        sat.hydrographics_code = Utils.eHex(generate_hydrographics(size_val, atm_val))
                        sat.uwp.atmosphere = sat.atmosphere_code
                        sat.uwp.hydrographics = sat.hydrographics_code
                    else:
                        sat.uwp.atmosphere = '0'
                        sat.uwp.hydrographics = '0'
                except ValueError:
                    pass

            world.satellites.append(sat)
