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

    # Resource Rating (WBH p. 102)
    world.resource_rating = max(0, Utils.D6(2) - 7 + Utils.from_eHex(world.size_code))

def assign_climate_zone(world: Any) -> None:
    """Assigns a climate zone and biome list from the world's final mean
    temperature and hydrographics."""
    temp = getattr(world, 'mean_temperature', 0.0) or 0.0
    hyd = Utils.from_eHex(getattr(world, 'hydrographics_code', 0) or 0)

    if temp < 200:
        world.climate_zone = "Cryogenic (Glacial)"
        world.biomes = ["Ice Cap", "Frozen Wasteland"]
    elif temp < 260:
        world.climate_zone = "Cold (Boreal)"
        world.biomes = ["Tundra", "Glacial Seas"]
    elif temp < 310:
        world.climate_zone = "Temperate"
        world.biomes = (["Grassland", "Forest", "Oceanic"] if hyd > 3
                        else ["Steppe", "Dry Shrubland"])
    elif temp < 350:
        world.climate_zone = "Hot (Tropical)"
        world.biomes = (["Jungle", "Wetlands", "Warm Seas"] if hyd > 4
                        else ["Savannah", "Arid Grassland"])
    else:
        world.climate_zone = "Torrid (Scorched)"
        world.biomes = ["Desert", "Volcanic Ashfields"]

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

ROCHE_LIMIT_PD = 1.537  # 1.22 x (2)^(1/3), WBH p.76 simplifying assumption
AU_KM = 149597870.9

def calculate_hill_sphere_pd(world: PlanetaryBody, system: StellarSystem) -> float:
    """Hill sphere radius of a world, in planetary diameters (WBH p.76).

    Hill Sphere (AU) = AU x (1 - ecc) x (m / (3M))^(1/3), where m is the
    world's mass in solar units and M the mass of the stars it orbits."""
    if world.diameter_km <= 0 or world.orbit_au <= 0:
        return 0.0

    star_mass = 0.0
    parent = next((s for s in system.stars
                   if s.designation == world.parent_star_group), None)
    if parent:
        if parent.is_composite:
            star_mass = sum(s.mass for s in system.stars
                            if s.designation in parent.components)
        else:
            star_mass = parent.mass
    if star_mass <= 0:
        star_mass = system.primary_star.mass if system.primary_star else 1.0
    if star_mass <= 0:
        return 0.0

    m_solar = max(1e-12, world.mass_terran * 0.000003)
    hill_au = (world.orbit_au * (1 - world.eccentricity)
               * (m_solar / (3 * star_mass)) ** (1 / 3))
    return hill_au * AU_KM / world.diameter_km

def _moon_orbit_pd(mor: float) -> float:
    """Rolls a moon's orbital distance in planetary diameters using the
    Moon Orbit Location table (WBH p.76)."""
    dm = 1 if mor < 60 else 0
    band = Utils.D6() + dm
    spread = Utils.D6(2) - 2
    if band <= 3:      # Inner sixth
        return spread * mor / 60 + 2
    elif band <= 5:    # Middle third
        return spread * mor / 30 + mor / 6 + 3
    else:              # Outer half
        return spread * mor / 20 + mor / 2 + 4

def _moon_period_hours(orbit_pd: float, planet_size_equiv: float,
                       planet_mass_terran: float) -> float:
    """Period (hours) = 0.176927 x sqrt((PD x Size)^3 / Mp) (WBH p.78)."""
    if planet_mass_terran <= 0 or orbit_pd <= 0 or planet_size_equiv <= 0:
        return 0.0
    return round(0.176927 * math.sqrt((orbit_pd * planet_size_equiv) ** 3
                                      / planet_mass_terran), 2)

def place_satellites(world: PlanetaryBody, system: StellarSystem):
    """Assigns orbital distances and periods to a world's satellites, and
    converts moons that cannot exist into rings (WBH pp.75-78).

    Moons live between the Roche limit (1.537 PD) and the Hill Sphere Moon
    Limit (half the Hill sphere). If that limit falls below 1.5 PD no
    significant moon can survive: the first becomes a ring and the rest are
    discarded. Below 0.55 PD not even rings persist."""
    if not world.satellites:
        return

    hill_pd = calculate_hill_sphere_pd(world, system)
    world.hill_sphere_pd = round(hill_pd, 3)
    moon_limit = hill_pd / 2.0
    world.hill_sphere_moon_limit_pd = round(moon_limit, 3)

    # Size equivalent in 1600km units, so Terra (12,742km) reads as ~8
    size_equiv = world.diameter_km / 1600.0
    mass = world.mass_terran

    if moon_limit < 0.55:
        # Nothing survives here at all
        world.notes.append("No moons or rings possible: Hill sphere moon limit "
                           f"{moon_limit:.2f} PD is at the surface")
        world.satellites = []
        return

    if moon_limit < 1.5:
        # Below the Roche limit: the first moon becomes a ring, rest are gone
        ring = next((s for s in world.satellites if s.is_ring), None)
        if ring is None:
            ring = world.satellites[0]
            ring.is_ring = True
            ring.size_code = 'R'
            ring.uwp.size = '0'
            ring.atmosphere_code = ''
            ring.hydrographics_code = ''
        ring.notes.append("Moon(s) reduced to a ring system inside the Roche limit")
        world.satellites = [ring]

    mor = math.floor(moon_limit) - 2
    if mor > 200:
        mor = 200 + len(world.satellites)
    mor = max(1.0, float(mor))

    for sat in world.satellites:
        if sat.is_ring:
            # Ring centre and width in PD (WBH p.78); kept inside the Roche
            # limit, which is where rings form.
            centre = 0.4 + ((Utils.D6() - 1) * 5 + (Utils.D6() - 1)) / 30.0
            width = random.randint(1, 100) / 100.0 * 0.5 + 0.07
            centre = min(centre, ROCHE_LIMIT_PD - width / 2)
            sat.orbit_pd = round(max(0.2, centre), 3)
            sat.ring_width_pd = round(width, 3)
            sat.period_hours = _moon_period_hours(sat.orbit_pd, size_equiv, mass)
            continue

        # Significant moons sit outside the Roche limit
        pd = _moon_orbit_pd(mor)
        pd += (Utils.D6(2) - 7) / 10.0 * 0.5  # optional linear variance
        pd = max(ROCHE_LIMIT_PD + 0.1, min(pd, moon_limit))
        sat.orbit_pd = round(pd, 3)
        sat.period_hours = _moon_period_hours(pd, size_equiv, mass)
        sat.eccentricity = round(max(0.0, (Utils.D6(2) - 2) / 100.0), 3)
        if Utils.D6(2) == 12:
            sat.retrograde = True
            sat.notes.append("Retrograde orbit")

def calculate_habitability_rating(world: Any, system: StellarSystem) -> int:
    """Habitability Rating = 10 + DMs (WBH pp.132-133), for Terragen life."""
    size = Utils.from_eHex(getattr(world, 'size_code', 0) or 0)
    atm = Utils.from_eHex(getattr(world, 'atmosphere_code', 0) or 0)
    hyd = Utils.from_eHex(getattr(world, 'hydrographics_code', 0) or 0)
    gravity = getattr(world, 'gravity', 0.0) or 0.0
    temp = getattr(world, 'mean_temperature', 0.0) or 0.0

    dm = 0

    # Size
    if size <= 4: dm -= 1
    elif size >= 9: dm += 1

    # Atmosphere
    if atm in (0, 1, 10): dm -= 8
    elif atm in (2, 14): dm -= 4
    elif atm in (3, 13): dm -= 3
    elif atm in (4, 9): dm -= 2
    elif atm in (5, 7, 8): dm -= 1
    elif atm == 11: dm -= 10
    elif atm == 12 or atm >= 15: dm -= 12

    # Hydrographics
    if hyd == 0: dm -= 4
    elif hyd <= 3: dm -= 2
    elif hyd == 9: dm -= 1
    elif hyd >= 10: dm -= 2

    # Tidal lock
    if any('Tidally Locked' in n for n in getattr(world, 'notes', [])):
        dm -= 2

    # Mean temperature
    if temp > 323: dm -= 4
    elif temp >= 304: dm -= 2
    elif temp < 273: dm -= 2

    # High and low temperature DMs, using the values computed in
    # temperature.py where available. The book's fallback (DM-2 hot/cold,
    # DM-6 frozen/boiling) applies only when they were never calculated.
    high = getattr(world, 'high_temperature', 0.0) or 0.0
    low = getattr(world, 'low_temperature', 0.0) or 0.0
    if high or low:
        if high > 323: dm -= 2
        if high and high < 279: dm -= 2
        if low and low < 200: dm -= 2
    elif temp > 0:
        if temp < 233 or temp > 373:   # Frozen or boiling
            dm -= 6
        elif temp < 273 or temp > 323: # Cold or hot
            dm -= 2

    # Gravity; take the worst DM at a boundary, per the book's footnote
    if gravity > 0:
        if gravity < 0.2: dm -= 4
        elif gravity <= 0.4: dm -= 2
        elif gravity <= 0.7: dm -= 1
        elif gravity <= 0.9: dm += 1
        elif gravity <= 1.1: dm += 0
        elif gravity <= 1.4: dm -= 1
        elif gravity <= 2.0: dm -= 3
        else: dm -= 6
    else:
        dm += 1 - abs(6 - size)

    # Miscellaneous surveyor adjustment
    dm += Utils.D3() - 1

    return max(0, min(12, 10 + dm))

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
