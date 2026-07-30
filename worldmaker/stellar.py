import random
import math
from typing import List, Dict, Any, Tuple, Optional

from .classes import Star, StellarSystem
from .utils import Utils
from .data import DATA

# Spectral types come in two shapes: "G2 V" for ordinary stars and a bare
# token ("D", "BD", "Pulsar", "Black Hole") for post-stellar and pre-stellar
# objects. These accessors keep the exotic cases from tripping the parsers.
EXOTIC_TYPES = {'D', 'D*', 'BD', 'Black Hole', 'Neutron Star', 'Pulsar',
                'Protostar', 'Nebula', 'Star Cluster'}

def is_exotic(spectral_type: str) -> bool:
    return spectral_type in EXOTIC_TYPES

def lum_class_of(spectral_type: str) -> str:
    """Luminosity class ("V", "III", ...), or "" for an exotic object."""
    if not spectral_type or is_exotic(spectral_type):
        return ""
    parts = spectral_type.split(' ')
    return parts[1] if len(parts) > 1 else ""

def spectral_str_of(spectral_type: str) -> str:
    """The type+subtype token ("G2"), or "" for an exotic object."""
    if not spectral_type or is_exotic(spectral_type):
        return ""
    return spectral_type.split(' ')[0]

def type_letter_of(spectral_type: str) -> str:
    """Spectral letter ("G"), or "" for an exotic object."""
    token = spectral_str_of(spectral_type)
    return token[0] if token else ""

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

    # Classes IV and VI are tabulated over a narrower type range than V, so a
    # bracketing key may be absent; fall back to whichever end is defined, or
    # to the nearest tabulated type along the spectral sequence.
    lower_val = class_v_data.get(lower_key)
    upper_val = class_v_data.get(upper_key)
    if lower_val is not None and upper_val is not None:
        return lower_val + (upper_val - lower_val) * interp_ratio
    if lower_val is not None:
        return lower_val
    if upper_val is not None:
        return upper_val
    return class_v_data[_nearest_tabulated_type(spectral_str, class_v_data)]

def _spectral_ordinal(key: str) -> int:
    """Position of a spectral type key along the O0..M9 sequence."""
    types = ['O', 'B', 'A', 'F', 'G', 'K', 'M']
    return types.index(key[0]) * 10 + int(key[1:])

def _nearest_tabulated_type(spectral_str: str, table: dict) -> str:
    """The key in `table` closest to `spectral_str` along the spectral
    sequence, for luminosity classes that omit part of the range."""
    target = _spectral_ordinal(spectral_str)
    return min(table, key=lambda k: abs(_spectral_ordinal(k) - target))

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

def _random_spectral_letter() -> str:
    """A spectral type letter for a star whose class came from the Special or
    Unusual tables; weighted toward the cooler, commoner types."""
    return random.choice(['B', 'A', 'F', 'G', 'G', 'K', 'K', 'M', 'M'])

# Physical properties of post-stellar and pre-stellar objects
# (WBH Special Circumstances, pp.224-231). Values are representative rather
# than rolled, which is enough for system generation to proceed.
_EXOTIC_PROPERTIES = {
    'D':            {'mass': 0.6,  'diameter': 0.012, 'temp_k': 12000.0, 'mao': 0.01},
    'D*':           {'mass': 0.9,  'diameter': 0.010, 'temp_k': 20000.0, 'mao': 0.01},
    'BD':           {'mass': 0.06, 'diameter': 0.10,  'temp_k': 1200.0,  'mao': 0.01},
    'Black Hole':   {'mass': 8.0,  'diameter': 0.0001, 'temp_k': 1.0,    'mao': 0.05},
    'Neutron Star': {'mass': 1.5,  'diameter': 0.00002, 'temp_k': 600000.0, 'mao': 0.05},
    'Pulsar':       {'mass': 1.4,  'diameter': 0.00002, 'temp_k': 800000.0, 'mao': 0.05},
    'Protostar':    {'mass': 1.0,  'diameter': 3.0,   'temp_k': 3000.0,  'mao': 0.5},
    'Nebula':       {'mass': 2.0,  'diameter': 5.0,   'temp_k': 2500.0,  'mao': 1.0},
    'Star Cluster': {'mass': 1.2,  'diameter': 1.2,   'temp_k': 5500.0,  'mao': 0.05},
}

def _apply_exotic_properties(star: Star, kind: str):
    """Fills in mass, diameter, temperature, luminosity, HZCO and MAO for a
    post-stellar or pre-stellar object."""
    props = _EXOTIC_PROPERTIES.get(kind, _EXOTIC_PROPERTIES['D'])
    star.mass = props['mass']
    star.diameter = props['diameter']
    star.temp_k = props['temp_k']
    temp_ratio = star.temp_k / 5772
    star.luminosity = max(1e-9, (star.diameter ** 2) * (temp_ratio ** 4))
    star.hzco = Utils.calculate_hzco(star.luminosity)
    star.mao = props['mao']

def generate_primary_star(special_roll=None) -> Star:
    """Implements the primary star generation sequence."""
    primary = Star(designation="A")
    
    roll = special_roll if special_roll else Utils.D6(2)
    star_type_result = DATA['star_type_determination']['Type'].get(min(roll, 12))
    lum_class = "V"

    if star_type_result == 'Hot':
        hot_roll = Utils.D6(2)
        star_type_result = DATA['star_type_determination']['Hot'].get(hot_roll)
    elif star_type_result == 'Special':
        # WBH p.15: a 2D roll of 2 leads to the Special table, which yields
        # subgiants, giants, supergiants and subdwarfs (and, via Unusual,
        # post-stellar and pre-stellar objects).
        special = DATA['star_type_determination']['Special'].get(Utils.D6(2))
        if special == 'Giants':
            lum_class = DATA['star_type_determination']['Giants'].get(Utils.D6(2), 'Class III')
            lum_class = lum_class.replace('Class ', '')
            star_type_result = _random_spectral_letter()
        elif special and special.startswith('Class'):
            lum_class = special.replace('Class ', '')
            star_type_result = _random_spectral_letter()
        else:
            # 'A' result on the Special table routes to the Unusual table
            unusual = DATA['star_type_determination']['Unusual'].get(Utils.D6(2))
            if unusual == 'Peculiar':
                peculiar = DATA['star_type_determination']['Peculiar'].get(Utils.D6())
                primary.spectral_type = peculiar
                _apply_exotic_properties(primary, peculiar)
                return primary
            if unusual in ('D', 'BD'):
                primary.spectral_type = unusual
                _apply_exotic_properties(primary, unusual)
                return primary
            if unusual == 'Giants':
                lum_class = DATA['star_type_determination']['Giants'].get(
                    Utils.D6(2), 'Class III').replace('Class ', '')
            elif unusual and unusual.startswith('Class'):
                lum_class = unusual.replace('Class ', '')
            star_type_result = _random_spectral_letter()

    primary.spectral_type = lum_class

    # Classes IV and VI are not tabulated across the whole type range; keep
    # the type inside the columns the physical-data tables actually define.
    valid_types = set(k[0] for k in DATA['star_mass'].get(lum_class, {}))
    if star_type_result not in valid_types:
        star_type_result = random.choice(sorted(valid_types)) if valid_types else 'G'

    subtype_roll = Utils.D6(2)
    if star_type_result == 'M':
        subtype = DATA['star_subtype']['M-type'][subtype_roll]
    else:
        subtype = DATA['star_subtype']['Numeric'][subtype_roll]

    spectral_str = f"{star_type_result}{subtype}"
    primary.spectral_type = f"{spectral_str} {primary.spectral_type}"
    
    # Calculate physical properties
    lum_class = lum_class_of(primary.spectral_type)
    primary.mass = _interpolate_stellar_data(spectral_str, DATA['star_mass'][lum_class])
    primary.temp_k = _interpolate_stellar_data(spectral_str, DATA['star_temp'][lum_class])
    primary.diameter = _interpolate_stellar_data(spectral_str, DATA['star_diameter'][lum_class])

    # Luminosity Formula from page 21
    temp_ratio = primary.temp_k / 5772
    primary.luminosity = (primary.diameter ** 2) * (temp_ratio ** 4)

    # HZCO and MAO
    primary.hzco = Utils.calculate_hzco(primary.luminosity)
    primary.mao = _lookup_mao(primary.spectral_type)

    return primary

def _lookup_mao(spectral_type: str) -> float:
    """Minimum Allowable Orbit# from the WBH p.39 table, interpolated between
    subtypes. Falls back to the Class V column for classes the table omits."""
    try:
        spectral_str, lum_class = spectral_str_of(spectral_type), lum_class_of(spectral_type)
    except IndexError:
        return 0.02
    table = DATA['star_mao'].get(lum_class) or DATA['star_mao']['V']
    try:
        return round(_interpolate_stellar_data(spectral_str, table), 3)
    except (KeyError, ValueError, IndexError):
        # Type outside this class's tabulated range (e.g. M-type subgiant)
        return 0.02

def _roll_stellar_eccentricity() -> float:
    """Eccentricity for a non-primary star: the standard eccentricity table
    with the DM+2 that WBH p.26 applies to star eccentricities."""
    roll = min(12, max(5, Utils.D6(2) + 2))
    data = DATA['eccentricity_values'].get(roll)
    if not data:
        return 0.0
    return round(max(0.0, min(0.95, data['base'] + data['roll']())), 3)

def assign_stellar_orbits(system: StellarSystem):
    """Assigns Orbit#, eccentricity and orbital period to every non-primary
    star (WBH p.27 Stellar Orbit# Ranges, p.30 for periods). Companions orbit
    their parent; Close/Near/Far stars orbit the primary."""
    primary = system.primary_star
    if not primary:
        return

    for star in system.stars:
        if star.is_composite or not star.parent:
            continue

        orbit_class = star.orbit_class
        if orbit_class == 'Companion':
            parent_class = lum_class_of(star.parent.spectral_type)
            if parent_class in ('Ia', 'Ib', 'II', 'III'):
                # Companions of giants sit outside the giant's own MAO
                star.orbit_num = round(Utils.D6() * max(0.01, star.parent.mao), 3)
            else:
                star.orbit_num = round(DATA['stellar_orbit_ranges']['Companion'](), 3)
        elif orbit_class in DATA['stellar_orbit_ranges']:
            base = DATA['stellar_orbit_ranges'][orbit_class]()
            # Optional fractional variance (recommended by the book for
            # greater system variation)
            star.orbit_num = round(base + Utils.d10() / 10.0, 3)
        else:
            continue

        star.orbit_num = max(0.05, star.orbit_num)
        star.eccentricity = _roll_stellar_eccentricity()
        star.mao = _lookup_mao(star.spectral_type)

        # Orbital period: P = sqrt(AU^3 / total mass of the pair)
        au = Utils.orbit_to_au(star.orbit_num)
        total_mass = star.parent.mass + star.mass
        if au > 0 and total_mass > 0:
            star.period_years = round(math.sqrt(au ** 3 / total_mass), 4)

    # Resolve crossing stellar orbits by pushing the outer star out one full
    # Orbit# until the conflict clears (WBH p.29).
    orbiters = sorted(
        [s for s in system.stars
         if s.parent is primary and s.orbit_class in ('Close', 'Near', 'Far')],
        key=lambda s: s.orbit_num)
    for i in range(1, len(orbiters)):
        inner, outer = orbiters[i - 1], orbiters[i]
        guard = 0
        while outer.orbit_num - inner.orbit_num < 1.0 and guard < 25:
            outer.orbit_num = round(outer.orbit_num + 1.0, 3)
            guard += 1
        au = Utils.orbit_to_au(outer.orbit_num)
        total_mass = primary.mass + outer.mass
        if au > 0 and total_mass > 0:
            outer.period_years = round(math.sqrt(au ** 3 / total_mass), 4)

def _determine_non_primary_star_type(parent_star: Star, orbit_class: str) -> dict:
    """Determines the type of a non-primary star based on its parent."""
    dm = 0
    if lum_class_of(parent_star.spectral_type) in ['III', 'IV']: dm -= 1

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
    if type_letter_of(primary.spectral_type) in ['O', 'B', 'A', 'F']: star_presense_dm += 1
    if type_letter_of(primary.spectral_type) == 'M': star_presense_dm -= 1

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
        if type_letter_of(star.spectral_type) in ['O', 'B', 'A', 'F']: companion_dm += 1
        if type_letter_of(star.spectral_type) == 'M': companion_dm -= 1
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
                parent_type = type_letter_of(star.parent.spectral_type) or 'M'
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
                lum_class = lum_class_of(star.spectral_type)
                spectral_str = star.spectral_type.split(' ')[0]
                star.mass = _interpolate_stellar_data(spectral_str, DATA['star_mass'][lum_class])
                star.temp_k = _interpolate_stellar_data(spectral_str, DATA['star_temp'][lum_class])
                star.diameter = _interpolate_stellar_data(spectral_str, DATA['star_diameter'][lum_class])

            if star.luminosity == 0.0:
                temp_ratio = star.temp_k / 5772
                star.luminosity = (star.diameter ** 2) * (temp_ratio ** 4)

    # Place the non-primary stars in their orbits (WBH p.27) before building
    # composite groups, whose MAO depends on companion eccentricity.
    assign_stellar_orbits(system)

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
