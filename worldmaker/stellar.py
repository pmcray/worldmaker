import random
import math
from typing import List, Dict, Any, Tuple, Optional

from .classes import Star, StellarSystem
from .utils import Utils
from .data import DATA

def _interpolate_stellar_data(spectral_str, class_v_data):
    """Helper to interpolate mass, temp, etc. between subtypes."""
    s_type = spectral_str[0]
    s_subtype = int(spectral_str[1])

    types = ['O', 'B', 'A', 'F', 'G', 'K', 'M']
    subtypes = [0, 5, 9] if s_type == 'M' else [0, 5]

    # Find bracketing subtypes
    lower_subtype = max([s for s in subtypes if s <= s_subtype])
    upper_subtype_list = [s for s in subtypes if s > s_subtype]
    upper_subtype = min(upper_subtype_list) if upper_subtype_list else -1

    if upper_subtype == -1: # At the end of a type (e.g. G9)
        current_type_index = types.index(s_type)
        if current_type_index + 1 >= len(types): return class_v_data[f"{s_type}{lower_subtype}"]
        next_type = types[current_type_index + 1]
        lower_key = f"{s_type}{lower_subtype}"
        upper_key = f"{next_type}0"
        span = 10 - lower_subtype
        pos = s_subtype - lower_subtype
    else:
        lower_key = f"{s_type}{lower_subtype}"
        upper_key = f"{s_type}{upper_subtype}"
        span = upper_subtype - lower_subtype
        pos = s_subtype - lower_subtype
    
    interp_ratio = pos / span if span > 0 else 0
    lower_val = class_v_data[lower_key]
    upper_val = class_v_data[upper_key]
    
    return lower_val + (upper_val - lower_val) * interp_ratio

def generate_world_name(used=None):
    """Generates a world name; pass a set as `used` to guarantee uniqueness."""
    prefixes = ["Ard", "Bor", "Cor", "Den", "Eth", "Fen", "Gor", "Hen", "Ish",
                "Jen", "Kel", "Lor", "Mor", "Nor", "Orr", "Per", "Quor", "Ren",
                "Sor", "Tor", "Ur", "Ver", "Wor", "Xen", "Yor", "Zor", "Al",
                "Bel", "Cal", "Dar", "Es", "Fal", "Gar", "Hal", "Iv", "Jor",
                "Kar", "Lan", "Mar", "Nal", "Ol", "Pal", "Ru", "Sal", "Tan",
                "Ul", "Van", "Wil", "Yal", "Zan"]
    mids = ["", "", "a", "e", "i", "o", "u", "an", "en", "in", "on", "un",
            "ar", "er", "ir", "or", "al", "el", "il", "ol"]
    suffixes = ["ia", "os", "a", "us", "is", "en", "or", "an", "el", "ar",
                "eth", "ax", "ine", "one", "ura", "esh", "im", "oth", "ave", "yr"]

    for _ in range(200):
        name = random.choice(prefixes) + random.choice(mids) + random.choice(suffixes)
        if used is None:
            return name
        if name not in used:
            used.add(name)
            return name
    # Pathological fallback: disambiguate with a numeral
    i = 2
    while f"{name} {i}" in used:
        i += 1
    name = f"{name} {i}"
    used.add(name)
    return name

def generate_primary_star(special_roll=None) -> Star:
    """Implements the primary star generation sequence."""
    primary = Star(designation="A")
    
    roll = special_roll if special_roll else Utils.D6(2)
    star_type_result = DATA['star_type_determination']['Type'].get(min(roll, 12))

    if star_type_result == 'Hot':
        hot_roll = Utils.D6(2)
        star_type_result = DATA['star_type_determination']['Hot'].get(hot_roll)
        primary.spectral_type = "V"
    elif star_type_result == 'Special':
        star_type_result = 'G' # Default to G-type for simplicity
        primary.spectral_type = "V"
    else:
        primary.spectral_type = "V"

    subtype_roll = Utils.D6(2)
    if star_type_result == 'M':
        subtype = DATA['star_subtype']['M-type'][subtype_roll]
    else:
        subtype = DATA['star_subtype']['Numeric'][subtype_roll]

    spectral_str = f"{star_type_result}{subtype}"
    primary.spectral_type = f"{spectral_str} {primary.spectral_type}"
    
    # Calculate physical properties
    lum_class = primary.spectral_type.split(' ')[1]
    primary.mass = _interpolate_stellar_data(spectral_str, DATA['star_mass'][lum_class])
    primary.temp_k = _interpolate_stellar_data(spectral_str, DATA['star_temp'][lum_class])
    primary.diameter = _interpolate_stellar_data(spectral_str, DATA['star_diameter'][lum_class])

    # Luminosity Formula from page 21
    temp_ratio = primary.temp_k / 5772
    primary.luminosity = (primary.diameter ** 2) * (temp_ratio ** 4)

    # HZCO and MAO
    primary.hzco = Utils.calculate_hzco(primary.luminosity)
    primary.mao = Utils.au_to_orbit(0.01 * primary.diameter) # Simplified Roche Limit
    
    return primary

def _determine_non_primary_star_type(parent_star: Star, orbit_class: str) -> dict:
    """Determines the type of a non-primary star based on its parent."""
    dm = 0
    if parent_star.spectral_type.split(' ')[1] in ['III', 'IV']: dm -= 1

    roll = Utils.D6(2) + dm
    category = 'Companion' if orbit_class == 'Companion' else 'Secondary'
    result = DATA['non_primary_star_determination'][min(12, max(2, roll))][category]
    return {'type': result, 'roll': roll}

def generate_stellar_system_stars(system: StellarSystem):
    """Generates all stars for a system, including primary, secondaries, and companions."""
    primary = generate_primary_star()
    system.stars.append(primary)

    # Determine number and type of other stars
    star_presense_dm = 0
    if primary.spectral_type[0] in ['O', 'B', 'A', 'F']: star_presense_dm += 1
    if primary.spectral_type[0] == 'M': star_presense_dm -= 1

    # Close Star
    if Utils.D6(2) + star_presense_dm >= 10:
        close_star = Star(designation="B", parent=primary, orbit_class="Close")
        system.stars.append(close_star)

    # Near Star
    if Utils.D6(2) + star_presense_dm >= 10:
        near_star = Star(designation="C", parent=primary, orbit_class="Near")
        system.stars.append(near_star)

    # Far Star
    if Utils.D6(2) + star_presense_dm >= 10:
        far_star = Star(designation="D", parent=primary, orbit_class="Far")
        system.stars.append(far_star)

    # Companions
    for star in system.stars[:]: # Iterate over a copy
        companion_dm = 0
        if star.spectral_type and star.spectral_type[0] in ['O', 'B', 'A', 'F']: companion_dm += 1
        if star.spectral_type and star.spectral_type[0] == 'M': companion_dm -= 1
        if Utils.D6(2) + companion_dm >= 10:
            companion = Star(designation=f"{star.designation}b", parent=star, orbit_class="Companion")
            star.designation = f"{star.designation}a"
            system.stars.append(companion)

    # Set stellar properties for non-primary stars
    for star in system.stars:
        if star.mass == 0.0 and star.parent: # If not primary
            result = _determine_non_primary_star_type(star.parent, star.orbit_class)
            star_type_info = result['type']

            if star_type_info == 'Random':
                new_star = generate_primary_star(special_roll=result['roll'])
                if new_star.mass > star.parent.mass:
                    star_type_info = 'Lesser' # Treat as lesser if more massive
                else:
                    star.spectral_type = new_star.spectral_type
                    star.mass = new_star.mass
                    star.diameter = new_star.diameter
                    star.luminosity = new_star.luminosity
                    star.temp_k = new_star.temp_k
            
            if star_type_info == 'Lesser':
                parent_type = star.parent.spectral_type[0]
                types = ['O', 'B', 'A', 'F', 'G', 'K', 'M']
                current_index = types.index(parent_type)
                if current_index + 1 < len(types):
                    new_type = types[current_index+1]
                    subtype = Utils.d10()
                    star.spectral_type = f"{new_type}{subtype} V"
                else:
                    star.spectral_type = f"M{Utils.d10()} V"

            elif star_type_info == 'Sibling':
                parent_type = star.parent.spectral_type.split(' ')[0]
                parent_subtype = int(parent_type[1:])
                new_subtype = parent_subtype - Utils.D6()
                new_type = parent_type[0]
                if new_subtype < 0:
                    types = ['O', 'B', 'A', 'F', 'G', 'K', 'M']
                    current_index = types.index(new_type)
                    if current_index + 1 < len(types):
                        new_type = types[current_index + 1]
                        new_subtype += 10
                    else:
                        new_subtype = 0 # Clamp to M0
                star.spectral_type = f"{new_type}{new_subtype} V"

            elif star_type_info == 'Twin':
                star.spectral_type = star.parent.spectral_type
                star.mass = star.parent.mass * (1 - (Utils.D6()-1)/100)
                star.diameter = star.parent.diameter * (1 - (Utils.D6()-1)/100)

            if star.mass == 0.0: # If not set by Twin or Random
                if not star.spectral_type:
                    star.spectral_type = "M0 V" # Default for unhandled cases
                lum_class = star.spectral_type.split(' ')[1]
                spectral_str = star.spectral_type.split(' ')[0]
                star.mass = _interpolate_stellar_data(spectral_str, DATA['star_mass'][lum_class])
                star.temp_k = _interpolate_stellar_data(spectral_str, DATA['star_temp'][lum_class])
                star.diameter = _interpolate_stellar_data(spectral_str, DATA['star_diameter'][lum_class])

            if star.luminosity == 0.0:
                temp_ratio = star.temp_k / 5772
                star.luminosity = (star.diameter ** 2) * (temp_ratio ** 4)

    # Create composite star groups (e.g., Aab)
    for star in system.stars[:]:
        if star.orbit_class == "Companion" and star.parent:
            parent = star.parent
            composite_designation = parent.designation[:-1] + 'ab'
            if not any(s.designation == composite_designation for s in system.stars):
                composite = Star(
                    designation=composite_designation,
                    is_composite=True,
                    components=[parent.designation, star.designation],
                    mass=parent.mass + star.mass,
                    luminosity=parent.luminosity + star.luminosity,
                    spectral_type=parent.spectral_type # Primary's type used for composite
                )
                composite.hzco = Utils.calculate_hzco(composite.luminosity)
                composite.mao = 0.5 + star.eccentricity # Rule 2, pg 38
                system.stars.append(composite)

    # System Age
    lifespan = 10 / (system.primary_star.mass ** 2.5) if system.primary_star.mass > 0 else 10
    if lifespan > 13.8: # Use small star age formula
        system.age_gyr = Utils.D6() * 2 + Utils.D3() - 1
    else:
        system.age_gyr = lifespan * (Utils.d10() / 10.0)
    system.age_gyr = round(max(0.1, min(system.age_gyr, 13.5)), 3)
