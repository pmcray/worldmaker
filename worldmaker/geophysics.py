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
    
    # Precise diameter. Each Size code spans a range around its average of
    # Size x 1,600km: Size 5 covers 7,200-8,799km, and so on (WBH p.70).
    if not world.diameter_km:
        if world.size_code == 'S':
            world.diameter_km = random.randint(400, 799)
        elif size_val <= 0:
            world.diameter_km = 0
        else:
            average = size_val * 1600
            world.diameter_km = average + random.randint(-800, 799)
    
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

    # Axial Tilt & Extreme Axial Tilt sub-table (WBH p. 104)
    world.axial_tilt, world.axial_tilt_remarks = roll_axial_tilt()

    # Resource Rating (WBH p. 131)
    world.resource_rating = max(0, Utils.D6(2) - 7 + Utils.from_eHex(world.size_code))


def roll_axial_tilt(add_precision: bool = True) -> Tuple[float, str]:
    """Rolls axial tilt in degrees on the Axial Tilt and Extreme Axial Tilt
    tables (WBH p. 104), returning `(tilt_degrees, remarks)`.

    Tilts between 90° and 180° indicate retrograde rotation. Any value pushed
    above 180° by arcminute/arcsecond variation is reflected back below 180°."""
    roll_2d = min(12, max(2, Utils.D6(2)))
    entry = DATA['axial_tilt'][roll_2d]
    if entry == 'Extreme':
        ext_roll = min(6, max(1, Utils.D6()))
        ext_entry = DATA['extreme_axial_tilt'][ext_roll]
        base_tilt = float(ext_entry['roll']())
        remarks = ext_entry['remarks']
    else:
        base_tilt = float(entry())
        remarks = "Normal"

    if add_precision and base_tilt >= 1.0:
        minutes = min(59, (Utils.D6() - 1) * 10 + random.randint(0, 9))
        seconds = min(59, (Utils.D6() - 1) * 10 + random.randint(0, 9))
        base_tilt += minutes / 60.0 + seconds / 3600.0

    if base_tilt > 180.0:
        base_tilt = 360.0 - base_tilt
    base_tilt = max(0.0, min(180.0, base_tilt))
    return round(base_tilt, 2), remarks


def roll_basic_day_length(body_type: str = 'Terrestrial',
                          size_code: str = '5',
                          age_gyr: float = 4.5,
                          add_precision: bool = True) -> float:
    """Basic Rotation Rate (sidereal day in hours, WBH pp. 103-104):
    `(2D-2) * mult + 2 + 1D + floor(age_gyr / 2)`, where `mult` is 2 for gas
    giants and small bodies (Size 0 or S) and 4 for terrestrial worlds. On a
    roll of 40+ hours, rolls 1D and on 5+ adds another basic rotation roll,
    repeating while 5+ continues."""
    mult = 2 if (body_type == 'Gas Giant' or str(size_code) in ('0', 'S')) else 4
    dm = int(max(0.0, age_gyr) // 2) if age_gyr > 2.0 else 0

    def _single_roll() -> int:
        return (Utils.D6(2) - 2) * mult + 2 + Utils.D6() + dm

    roll = _single_roll()
    total_hours = float(roll)
    while roll >= 40 and Utils.D6() >= 5:
        roll = _single_roll()
        total_hours += float(roll)

    if add_precision:
        minutes = min(59, (Utils.D6() - 1) * 10 + random.randint(0, 9))
        seconds = min(59, (Utils.D6() - 1) * 10 + random.randint(0, 9))
        total_hours += minutes / 60.0 + seconds / 3600.0

    return round(total_hours, 2)


def _reroll_eccentricity_with_dm(dm: int = -2) -> float:
    """Rolls orbital eccentricity on the WBH p. 27 table with a DM."""
    roll = Utils.D6(2) + dm
    if roll <= 4:
        return 0.0
    capped = min(12, max(5, roll))
    entry = DATA['eccentricity_values'][capped]
    return round(max(0.0, entry['base'] + entry['roll']()), 4)


def calculate_tidal_lock_dm(body: Any, system: Optional[StellarSystem] = None,
                            case: str = 'star',
                            target_moon: Any = None) -> int:
    """Computes the total DM for the Tidal Lock Status table (WBH pp. 106-107).

    `case` is one of:
    - `'star'`: lock of a planet to its parent star(s)
    - `'planet'`: lock of a moon to its parent planet
    - `'moon'`: lock of a terrestrial planet to one of its locked moons
    """
    dm = 0
    size_str = str(getattr(body, 'size_code', '0') or '0')
    if size_str in ('0', 'S', 'R') or size_str.startswith('G'):
        size_val = 0
    else:
        size_val = Utils.from_eHex(size_str)

    # --- DMs for all cases (WBH p. 106) ---
    if size_val >= 1:
        dm += int(math.ceil(size_val / 3.0))

    ecc = getattr(body, 'eccentricity', 0.0) or 0.0
    if ecc > 0.1:
        dm -= int(math.floor(ecc * 10.0))

    tilt = getattr(body, 'axial_tilt', 0.0) or 0.0
    # Axial tilt DMs are additive (WBH p. 106)
    if tilt > 30.0:
        dm -= 2
    if 60.0 <= tilt <= 120.0:
        dm -= 4
    if 80.0 <= tilt <= 100.0:
        dm -= 4

    pressure = getattr(body, 'atmos_pressure_bar', 0.0) or 0.0
    if pressure > 2.5:
        dm -= 2

    age = getattr(system, 'age_gyr', 4.5) if system is not None else 4.5
    if age < 1.0:
        dm -= 2
    elif 5.0 <= age <= 10.0:
        dm += 2
    elif age > 10.0:
        dm += 4

    # --- Case-specific DMs ---
    if case == 'star':
        dm -= 4  # Base DM for planet to star
        orbit_num = getattr(body, 'orbit_num', 0.0) or 0.0
        if orbit_num < 1.0:
            dm += 4 + int(math.floor(10.0 * (1.0 - orbit_num)))
        elif orbit_num <= 2.0:
            dm += 4
        elif orbit_num <= 3.0:
            dm += 1
        else:
            dm -= int(math.floor(orbit_num)) * 2

        star_mass = 1.0
        num_stars = 1
        if system is not None and system.stars:
            parent_desig = getattr(body, 'parent_star_group', None)
            parent = next((s for s in system.stars if s.designation == parent_desig), None)
            if parent is None:
                parent = system.primary_star
            if parent is not None:
                if parent.is_composite and parent.components:
                    num_stars = len(parent.components)
                    star_mass = sum(s.mass for s in system.stars
                                    if s.designation in parent.components)
                else:
                    num_stars = 1
                    star_mass = parent.mass

        if star_mass < 0.5:
            dm -= 2
        elif star_mass <= 1.0:
            dm -= 1
        elif 2.0 <= star_mass <= 5.0:
            dm += 1
        elif star_mass > 5.0:
            dm += 2

        if num_stars > 1:
            dm -= num_stars

        moon_size_sum = 0
        for sat in getattr(body, 'satellites', []):
            if sat.is_ring:
                continue
            s_code = str(getattr(sat, 'size_code', '0') or '0')
            if s_code not in ('0', 'S', 'R'):
                s_val = Utils.from_eHex(s_code)
                if s_val >= 1:
                    moon_size_sum += s_val
        dm -= moon_size_sum

    elif case == 'planet':
        dm += 6  # Base DM for moon to planet
        orbit_pd = getattr(body, 'orbit_pd', 0.0) or 0.0
        if orbit_pd > 20.0:
            dm -= int(math.floor(orbit_pd / 20.0))
        if getattr(body, 'retrograde', False):
            dm -= 2
        parent = getattr(body, 'parent_body', None)
        mp = getattr(parent, 'mass_terran', 1.0) if parent is not None else 1.0
        if 1.0 <= mp <= 10.0:
            dm += 2
        elif 10.0 < mp <= 100.0:
            dm += 4
        elif 100.0 < mp <= 1000.0:
            dm += 6
        elif mp > 1000.0:
            dm += 8

    elif case == 'moon':
        dm -= 10  # Base DM for terrestrial planet to moon (WBH p. 107)
        if target_moon is not None:
            m_code = str(getattr(target_moon, 'size_code', '0') or '0')
            m_size = 0 if m_code in ('0', 'S', 'R') else Utils.from_eHex(m_code)
            if m_size >= 1:
                dm += m_size
            pd = getattr(target_moon, 'orbit_pd', 0.0) or 0.0
            if pd < 5.0:
                dm += 5 + int(math.ceil((5.0 - pd) * 5.0))
            elif pd <= 10.0:
                dm += 4
            elif pd <= 20.0:
                dm += 2
            elif pd <= 40.0:
                dm += 1
            elif pd > 60.0:
                dm -= 6
        sig_moons = [s for s in getattr(body, 'satellites', []) if not s.is_ring]
        if len(sig_moons) > 1:
            dm -= 2 * (len(sig_moons) - 1)

    return dm


def apply_tidal_lock_roll(body: Any, roll: int, orbital_period_hours: float,
                          case: str = 'star', target_label: str = '',
                          allow_break_reroll: bool = True) -> str:
    """Applies a roll on the Tidal Lock Status table (WBH p. 105) to `body`,
    updating its `rotation_period_hours`, `axial_tilt`, `eccentricity`,
    `tidal_lock_status`, and `notes`. Returns the resulting status code."""
    if roll >= 12 and allow_break_reroll:
        # Footnote *: On a 1:1 lock, roll 2D; on a natural 12 an impact or
        # passing body broke the lock — reroll on the table with DM 0.
        if Utils.D6(2) == 12:
            reroll = Utils.D6(2)
            saved_hours = body.rotation_period_hours
            status = apply_tidal_lock_roll(
                body, reroll, orbital_period_hours, case=case,
                target_label=target_label, allow_break_reroll=False
            )
            # For a moon locked to a planet, if the broken-lock day length
            # exceeds its orbital period around the planet, it stays 1:1 locked.
            if (case == 'planet' and orbital_period_hours > 0
                    and body.rotation_period_hours > orbital_period_hours):
                body.rotation_period_hours = saved_hours
                return apply_tidal_lock_roll(
                    body, 12, orbital_period_hours, case=case,
                    target_label=target_label, allow_break_reroll=False
                )
            return status

    if roll <= 2:
        body.tidal_lock_status = "None"
        return "None"
    elif roll == 3:
        body.rotation_period_hours = round(body.rotation_period_hours * 1.5, 2)
        body.tidal_lock_status = "Slowed (x1.5)"
    elif roll == 4:
        body.rotation_period_hours = round(body.rotation_period_hours * 2.0, 2)
        body.tidal_lock_status = "Slowed (x2)"
    elif roll == 5:
        body.rotation_period_hours = round(body.rotation_period_hours * 3.0, 2)
        body.tidal_lock_status = "Slowed (x3)"
    elif roll == 6:
        body.rotation_period_hours = round(body.rotation_period_hours * 5.0, 2)
        body.tidal_lock_status = "Slowed (x5)"
    elif roll == 7:
        body.rotation_period_hours = float(Utils.D6() * 5 * 24)
        body.tidal_lock_status = "Prograde Slow"
    elif roll == 8:
        body.rotation_period_hours = float(Utils.D6() * 20 * 24)
        body.tidal_lock_status = "Prograde Very Slow"
    elif roll == 9:
        body.rotation_period_hours = float(Utils.D6() * 10 * 24)
        if body.axial_tilt < 90.0:
            body.axial_tilt = round(180.0 - body.axial_tilt, 2)
            body.axial_tilt_remarks = "Retrograde (tidal)"
        body.tidal_lock_status = "Retrograde"
    elif roll == 10:
        body.rotation_period_hours = float(Utils.D6() * 50 * 24)
        if body.axial_tilt < 90.0:
            body.axial_tilt = round(180.0 - body.axial_tilt, 2)
            body.axial_tilt_remarks = "Retrograde (tidal)"
        body.tidal_lock_status = "Retrograde Slow"
    elif roll == 11:
        # 3:2 tidal lock: world spins 3 times for every 2 revolutions (WBH p. 105)
        if orbital_period_hours > 0:
            body.rotation_period_hours = round(orbital_period_hours * (2.0 / 3.0), 2)
        body.tidal_lock_status = "3:2"
        body.tidal_lock_target = target_label
        if body.axial_tilt > 3.0:
            body.axial_tilt = round((Utils.D6(2) - 2) / 10.0, 2)
            body.axial_tilt_remarks = "Tidal lock damped (3:2)"
        note = f"3:2 Tidal Lock to {target_label or case.title()}"
        if note not in body.notes:
            body.notes.append(note)
    else:  # 12+
        # 1:1 tidal lock: world spins once per revolution (WBH p. 105)
        if orbital_period_hours > 0:
            body.rotation_period_hours = round(orbital_period_hours, 2)
        body.tidal_lock_status = "1:1"
        body.tidal_lock_target = target_label
        if body.axial_tilt > 3.0:
            body.axial_tilt = round((Utils.D6(2) - 2) / 10.0, 2)
            body.axial_tilt_remarks = "Tidal lock damped (1:1)"
        if getattr(body, 'eccentricity', 0.0) > 0.1:
            new_ecc = _reroll_eccentricity_with_dm(-2)
            body.eccentricity = min(body.eccentricity, new_ecc)
        if case == 'star':
            body.is_twilight_zone_world = True
            note = "Tidally Locked to Star"
        elif case == 'planet':
            note = f"Tidally Locked to Planet ({target_label})" if target_label else "Tidally Locked to Planet"
        else:
            note = f"Tidally Locked to Moon ({target_label})" if target_label else "Tidally Locked to Moon"
        if not any(note in n for n in body.notes):
            body.notes.append(note)

    return body.tidal_lock_status


def calculate_solar_day_and_year(body: Any, system: Optional[StellarSystem] = None) -> None:
    """Computes sidereal days in year, solar days in year, and solar day length
    in hours (WBH p. 104).

    Solar Days in a local year = (Year in hours / signed Sidereal Day in hours) - 1
    Solar Day (hours) = Year in hours / Solar Days in a local year

    For a planet 1:1 tidally locked to its star, there are 0 solar days in a
    year and `solar_day_hours` is `None` (undefined/infinite — twilight zone
    world). For a world with axial tilt > 90° (retrograde), its sidereal day is
    treated as negative in the solar day formula."""
    period_years = getattr(body, 'period_years', 0.0) or 0.0
    if not period_years and getattr(body, 'parent_body', None) is not None:
        period_years = getattr(body.parent_body, 'period_years', 0.0) or 0.0
    year_hours = period_years * 8766.0

    sidereal_hours = getattr(body, 'rotation_period_hours', 0.0) or 0.0
    body.sidereal_day_hours = round(sidereal_hours, 2)
    if sidereal_hours <= 0 or year_hours <= 0:
        body.sidereal_days_in_year = 0.0
        body.solar_days_in_year = 0.0
        body.solar_day_hours = sidereal_hours if sidereal_hours > 0 else None
        return

    body.sidereal_days_in_year = round(year_hours / sidereal_hours, 2)

    # A world 1:1 locked to its star has sidereal day == year length and no
    # defined solar day (twilight zone world, WBH pp. 104, 107).
    if getattr(body, 'is_twilight_zone_world', False) or (
        getattr(body, 'tidal_lock_status', '') == '1:1'
        and getattr(body, 'parent_body', None) is None
        and abs(year_hours - sidereal_hours) < 1.0
    ):
        body.solar_days_in_year = 0.0
        body.solar_day_hours = None
        body.is_twilight_zone_world = True
        return

    signed_sidereal = -sidereal_hours if (getattr(body, 'axial_tilt', 0.0) or 0.0) > 90.0 else sidereal_hours
    solar_days = (year_hours / signed_sidereal) - 1.0
    if abs(solar_days) < 1e-6:
        body.solar_days_in_year = 0.0
        body.solar_day_hours = None
    else:
        body.solar_days_in_year = round(abs(solar_days), 2)
        body.solar_day_hours = round(abs(year_hours / solar_days), 2)


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


def generate_rotation_period(world: Any, system: StellarSystem):
    """Generates the basic sidereal day length, evaluates the full Tidal Lock
    Status table (planet-to-star, moon-to-planet, and planet-to-moon, including
    3:2 resonances and 1:1 locks), and computes solar day length and days in
    year (WBH pp. 103-107)."""
    body_type = getattr(world, 'body_type', 'Terrestrial')
    if body_type == 'Planetoid Belt' or getattr(world, 'is_ring', False):
        return

    age_gyr = getattr(system, 'age_gyr', 4.5) if system is not None else 4.5
    size_code = str(getattr(world, 'size_code', '0') or '0')
    world.rotation_period_hours = roll_basic_day_length(body_type, size_code, age_gyr)

    is_moon = getattr(world, 'parent_body', None) is not None
    if is_moon:
        parent = world.parent_body
        dm = calculate_tidal_lock_dm(world, system, case='planet')
        world.tidal_lock_dm = dm
        parent_label = getattr(parent, 'designation', '') or getattr(parent, 'name', 'Planet')
        period_hours = getattr(world, 'period_hours', 0.0) or (world.rotation_period_hours * 2.0)
        if dm >= 10:
            apply_tidal_lock_roll(world, 12, period_hours, case='planet',
                                  target_label=parent_label)
        elif dm > -10:
            roll = Utils.D6(2) + dm
            apply_tidal_lock_roll(world, roll, period_hours, case='planet',
                                  target_label=parent_label)
        calculate_solar_day_and_year(world, system)
        return

    # For a planet: check if any moons are already 1:1 locked to this planet
    # (only Terrestrial planets Size 1-F can lock to a moon, WBH p. 107).
    locked_moons = [
        s for s in getattr(world, 'satellites', [])
        if not s.is_ring and getattr(s, 'tidal_lock_status', '') == '1:1'
    ]
    locked_moons.sort(key=lambda s: getattr(s, 'orbit_pd', 9999.0) or 9999.0)

    star_dm = calculate_tidal_lock_dm(world, system, case='star')
    star_label = getattr(world, 'parent_star_group', '') or 'Star'
    year_hours = (getattr(world, 'period_years', 0.0) or 0.0) * 8766.0

    best_moon = None
    best_moon_dm = -999
    if body_type == 'Terrestrial' and size_code not in ('0', 'S') and locked_moons:
        for m in locked_moons:
            m_dm = calculate_tidal_lock_dm(world, system, case='moon', target_moon=m)
            if m_dm > best_moon_dm:
                best_moon_dm = m_dm
                best_moon = m

    # WBH p. 106: Only roll for the case with the highest DM. On a tie, roll
    # for the moon first, and if a lock condition (3:2 or 1:1) does not occur,
    # roll for the star and apply the higher adjusted roll.
    if best_moon is not None and best_moon_dm > star_dm:
        world.tidal_lock_dm = best_moon_dm
        m_label = getattr(best_moon, 'designation', '') or 'Moon'
        m_period = getattr(best_moon, 'period_hours', 0.0) or year_hours
        if best_moon_dm >= 10:
            apply_tidal_lock_roll(world, 12, m_period, case='moon', target_label=m_label)
        elif best_moon_dm > -10:
            apply_tidal_lock_roll(world, Utils.D6(2) + best_moon_dm, m_period,
                                  case='moon', target_label=m_label)
    elif best_moon is not None and best_moon_dm == star_dm and best_moon_dm > -10:
        world.tidal_lock_dm = best_moon_dm
        m_label = getattr(best_moon, 'designation', '') or 'Moon'
        m_period = getattr(best_moon, 'period_hours', 0.0) or year_hours
        moon_roll = 12 if best_moon_dm >= 10 else (Utils.D6(2) + best_moon_dm)
        saved_rot = world.rotation_period_hours
        saved_tilt = world.axial_tilt
        status = apply_tidal_lock_roll(world, moon_roll, m_period, case='moon',
                                       target_label=m_label)
        if status not in ('3:2', '1:1'):
            star_roll = 12 if star_dm >= 10 else (Utils.D6(2) + star_dm)
            if star_roll > moon_roll:
                world.rotation_period_hours = saved_rot
                world.axial_tilt = saved_tilt
                apply_tidal_lock_roll(world, star_roll, year_hours, case='star',
                                      target_label=star_label)
    else:
        world.tidal_lock_dm = star_dm
        if star_dm >= 10:
            apply_tidal_lock_roll(world, 12, year_hours, case='star',
                                  target_label=star_label)
        elif star_dm > -10:
            apply_tidal_lock_roll(world, Utils.D6(2) + star_dm, year_hours,
                                  case='star', target_label=star_label)

    calculate_solar_day_and_year(world, system)


def roll_hydrographics_percentage(hydrographics_code: Any,
                                  size_code: Any = '5') -> float:
    """Rolls the precise hydrographics percentage for a world's Hydrographics
    code (WBH p. 99):
    - Hydrographics 0: `-4 + d10`, results below 0 treated as 0% (0-5% range)
    - Hydrographics 1-9: base of range `(H*10 - 5) + d10` (e.g. H=6 -> 56-65%)
    - Hydrographics A (10): `96 + d10` capped at 100%, or always 100% when
      Size > 9."""
    if hydrographics_code is None or str(hydrographics_code) == '':
        return 0.0
    hyd = Utils.from_eHex(hydrographics_code) if isinstance(hydrographics_code, str) else int(hydrographics_code)
    size_str = str(size_code or '0')
    size_val = 0 if size_str in ('0', 'S', 'R') or size_str.startswith('G') else Utils.from_eHex(size_str)

    if size_val <= 1 and hyd == 0:
        return 0.0
    if hyd <= 0:
        return float(max(0, min(5, -4 + random.randint(1, 10))))
    if hyd >= 10:
        if size_val > 9:
            return 100.0
        return float(min(100, 95 + random.randint(1, 10)))
    return float((hyd * 10 - 5) + random.randint(1, 10))


def roll_surface_distribution(hydrographics_code: Any,
                              hydrographics_pct: Optional[float] = None) -> Dict[str, Any]:
    """Rolls `2D-2` on the Surface Distribution table (WBH pp. 100-102) and
    determines dominant geography ('ocean' or 'land') plus counts of major
    (>=5% surface area) and minor (1-5% surface area) continents or oceans."""
    hyd = Utils.from_eHex(hydrographics_code) if isinstance(hydrographics_code, str) else int(hydrographics_code or 0)
    pct = float(hydrographics_pct if hydrographics_pct is not None else hyd * 10.0)

    dist_roll = Utils.D6(2) - 2
    dist_info = DATA['surface_distribution'][dist_roll]

    if hyd == 0 and pct <= 0.0:
        return {
            'code': dist_roll,
            'description': dist_info['name'],
            'dominant_geography': 'land',
            'major_continents': 0,
            'minor_continents': 0,
        }

    if hyd >= 6 or pct > 55.0:
        dominant = 'ocean'
    elif hyd <= 4 or pct < 45.0:
        dominant = 'land'
    else:
        dominant = 'ocean' if Utils.D6() <= 3 else 'land'

    # The discrete bodies measured by the table are continents when ocean is
    # foundational, and oceans/seas when land is foundational (WBH p. 100).
    body_coverage_pct = (100.0 - pct) if dominant == 'ocean' else pct
    major_fraction = dist_info['major_fraction']
    major_pct = body_coverage_pct * major_fraction
    minor_pct = body_coverage_pct * (1.0 - major_fraction)

    if body_coverage_pct < 1.0:
        major_count = 0
        minor_count = 0
    elif dist_roll == 0 or body_coverage_pct < 5.0:
        major_count = 0
        minor_count = max(1, int(round(body_coverage_pct / 2.5)))
    elif dist_roll >= 9:
        major_count = 1
        minor_count = max(0, int(round(minor_pct / 2.5)))
    else:
        max_major = max(1, int(major_pct // 5.0))
        major_count = random.randint(1, min(7, max_major))
        minor_count = max(0, int(round(minor_pct / 3.0)))

    return {
        'code': dist_roll,
        'description': dist_info['name'],
        'dominant_geography': dominant,
        'major_continents': major_count,
        'minor_continents': minor_count,
    }


def determine_exotic_liquids(world: Any) -> Dict[str, Any]:
    """Determines the surface liquid composition and WBH p. 103 hydrographics
    profile (`H-D:%%:XX-##:YY-##`) from the world's Hydrographics code,
    precise percentage, Atmosphere code/composition/taint, pressure, and
    surface temperature (WBH pp. 102-103)."""
    hyd_str = str(getattr(world, 'hydrographics_code', '0') or '0')
    hyd = Utils.from_eHex(hyd_str) if hyd_str.isalnum() else 0
    pct = getattr(world, 'hydrographics_pct', None)
    if pct is None or (pct == 0.0 and hyd > 0):
        pct = roll_hydrographics_percentage(hyd, getattr(world, 'size_code', '5'))
        world.hydrographics_pct = pct

    dist_code = getattr(world, 'surface_distribution', 5)
    dist_ehex = Utils.eHex(dist_code)
    pct_int = int(round(pct))

    if hyd == 0 and pct_int == 0:
        world.hydrographics_liquid = "None"
        world.hydrographics_composition = {}
        world.hydrographics_profile = f"0-{dist_ehex}:00"
        return {
            'liquid': world.hydrographics_liquid,
            'composition': world.hydrographics_composition,
            'profile': world.hydrographics_profile,
        }

    atm_str = str(getattr(world, 'atmosphere_code', '0') or '0')
    atm = Utils.from_eHex(atm_str) if atm_str.isalnum() else 0
    temp = getattr(world, 'mean_temperature', 0.0) or 288.0
    pressure = getattr(world, 'atmos_pressure_bar', 1.0) or 1.0
    atm_comp = (getattr(world, 'atmosphere_composition', '') or '').lower()
    taint_info = getattr(world, 'atmosphere_taint', None) or {}
    taint_str = (taint_info.get('type', '') if isinstance(taint_info, dict) else str(taint_info)).lower()

    # 1. Surface temperature > 1,000K: liquid rock / magma oceans (WBH p. 102)
    if temp >= 1000.0:
        world.hydrographics_liquid = "Magma (Liquid Rock)"
        world.hydrographics_composition = {"SiO2": 100}
        world.hydrographics_profile = f"{Utils.eHex(hyd)}-{dist_ehex}:{pct_int:02d}:SiO2-100"
        return {
            'liquid': world.hydrographics_liquid,
            'composition': world.hydrographics_composition,
            'profile': world.hydrographics_profile,
        }

    # 2. Outer system / Vacuum or Trace (Atm 0-1): surface water ice (WBH p. 100)
    if atm in (0, 1):
        world.hydrographics_liquid = "Water Ice"
        world.hydrographics_composition = {"H2O": 100}
        world.hydrographics_profile = f"{Utils.eHex(hyd)}-{dist_ehex}:{pct_int:02d}:H2O"
        return {
            'liquid': world.hydrographics_liquid,
            'composition': world.hydrographics_composition,
            'profile': world.hydrographics_profile,
        }

    # 3. Standard/Breathable/Thin/Dense Atmospheres (2-9, D, E): Water
    if atm in (2, 3, 4, 5, 6, 7, 8, 9, 13, 14):
        world.hydrographics_liquid = "Water"
        world.hydrographics_composition = {"H2O": 100}
        world.hydrographics_profile = f"{Utils.eHex(hyd)}-{dist_ehex}:{pct_int:02d}:H2O"
        return {
            'liquid': world.hydrographics_liquid,
            'composition': world.hydrographics_composition,
            'profile': world.hydrographics_profile,
        }

    # 4. Exotic (A), Corrosive (B), Insidious (C), or Unusual (F) Fluidic Worlds
    # (WBH pp. 102-103 Possible Exotic Liquids table).
    # Higher pressures widen boiling points upward slightly.
    bp_shift = max(0.0, math.log10(max(0.1, pressure)) * 25.0) if pressure > 1.0 else 0.0
    table = DATA['exotic_liquids']

    def _weight_for(mol: dict) -> float:
        w = float(mol['abundance'])
        code = mol['code']
        name_l = mol['name'].lower()
        # Exotic (A) allows water freely when temperature permits; Corrosive (B)
        # and Insidious (C) strongly favour corrosive/acidic/non-water liquids
        # (WBH p. 102).
        if atm in (11, 12) and code == 'H2O':
            w *= 0.15
        if atm in (11, 12) and ('acid' in name_l or code in ('NH3', 'SO2', 'Cl2', 'F2', 'HCN', 'CH3NO')):
            w *= 3.0
        # Boost liquids whose elements match the atmosphere composition or taint
        if name_l in atm_comp or code.lower() in atm_comp:
            w *= 3.0
        if ('sulphur' in atm_comp or 'sulfur' in taint_str or 'so2' in atm_comp) and ('S' in code):
            w *= 2.5
        if ('chlorine' in atm_comp or 'chlorine' in taint_str) and ('Cl' in code):
            w *= 4.0
        if ('fluorine' in atm_comp or 'fluorine' in taint_str) and ('F' in code):
            w *= 4.0
        if ('methane' in atm_comp or 'ethane' in atm_comp) and code in ('CH4', 'C2H6'):
            w *= 2.5
        if ('ammonia' in atm_comp or 'nitrogen' in atm_comp) and code in ('NH3', 'HCN', 'CH3NO'):
            w *= 2.0
        if ('carbon dioxide' in atm_comp or 'co2' in atm_comp) and code in ('H2CO3', 'CH2O2', 'CH3NO'):
            w *= 2.0
        return max(0.1, w)

    # Candidates whose liquid range [melting_k, boiling_k + bp_shift] spans temp
    in_range = [
        m for m in table
        if (m['melting_k'] - 10.0) <= temp <= (m['boiling_k'] + bp_shift + 10.0)
    ]
    if not in_range:
        # Pick the 2 molecules whose liquid range is closest to `temp`
        def _dist(m: dict) -> float:
            hi = m['boiling_k'] + bp_shift
            if temp < m['melting_k']:
                return m['melting_k'] - temp
            if temp > hi:
                return temp - hi
            return 0.0
        in_range = sorted(table, key=_dist)[:2]

    weights = [_weight_for(m) for m in in_range]
    primary = random.choices(in_range, weights=weights, k=1)[0]

    # When multiple exotic liquids share the temperature band, allow a mixture
    # (like Titan's CH4 + C2H6 or acid-water mixtures, WBH p. 103).
    remaining = [m for m in in_range if m['code'] != primary['code']]
    if remaining and Utils.D6() >= 4:
        rem_weights = [_weight_for(m) for m in remaining]
        secondary = random.choices(remaining, weights=rem_weights, k=1)[0]
        primary_share = min(95, max(50, 45 + Utils.D6() * 8 + random.randint(0, 5)))
        secondary_share = 100 - primary_share
        comp = {primary['code']: primary_share, secondary['code']: secondary_share}
        liquid_name = f"{primary['name']} / {secondary['name']}"
        comp_str = f"{primary['code']}-{primary_share:02d}:{secondary['code']}-{secondary_share:02d}"
    else:
        comp = {primary['code']: 100}
        liquid_name = primary['name']
        comp_str = "H2O" if primary['code'] == 'H2O' else f"{primary['code']}-100"

    world.hydrographics_liquid = liquid_name
    world.hydrographics_composition = comp
    world.hydrographics_profile = f"{Utils.eHex(hyd)}-{dist_ehex}:{pct_int:02d}:{comp_str}"
    return {
        'liquid': world.hydrographics_liquid,
        'composition': world.hydrographics_composition,
        'profile': world.hydrographics_profile,
    }


def detail_hydrographics(world: Any, system: Optional[StellarSystem] = None) -> None:
    """Populates precise hydrographics percentage, surface distribution,
    major/minor continent counts, and exotic liquid composition (WBH pp. 99-103)."""
    if not getattr(world, 'hydrographics_code', None) or not str(world.hydrographics_code).isalnum():
        return
    pct = roll_hydrographics_percentage(world.hydrographics_code,
                                        getattr(world, 'size_code', '5'))
    world.hydrographics_pct = pct
    dist = roll_surface_distribution(world.hydrographics_code, pct)
    world.surface_distribution = dist['code']
    world.surface_distribution_desc = dist['description']
    world.dominant_geography = dist['dominant_geography']
    world.major_continents = dist['major_continents']
    world.minor_continents = dist['minor_continents']
    determine_exotic_liquids(world)


def generate_surface_features(world: Any) -> str:
    """Generates a description of the world's surface features, precise
    hydrographic percentage, surface distribution, and liquid composition
    (WBH pp. 99-103)."""
    if not world.hydrographics_code or not str(world.hydrographics_code).isalnum():
        return "No hydrographics data."

    hydro_val = Utils.from_eHex(world.hydrographics_code)
    if getattr(world, 'hydrographics_pct', 0.0) == 0.0 and not getattr(world, 'surface_distribution_desc', ''):
        detail_hydrographics(world)
    else:
        # Refresh liquid composition now that final mean_temperature is known
        determine_exotic_liquids(world)

    pct = int(round(getattr(world, 'hydrographics_pct', hydro_val * 10)))
    liquid = getattr(world, 'hydrographics_liquid', 'Water') or 'Water'
    dist_desc = getattr(world, 'surface_distribution_desc', 'Mixed') or 'Mixed'
    surface_dist_roll = getattr(world, 'surface_distribution', 5)
    maj = getattr(world, 'major_continents', 0)
    min_c = getattr(world, 'minor_continents', 0)

    if hydro_val == 0 and pct == 0:
        return "0% surface liquid; barren desert world."
    elif hydro_val == 10 and pct >= 98:
        return f"{pct}% {liquid.lower()} coverage ({world.hydrographics_profile}). Panthalassic world, almost entirely covered in deep oceans."

    liquid_phrase = "water" if liquid == "Water" else f"exotic liquid ({liquid})"
    if getattr(world, 'dominant_geography', '') == 'ocean' or hydro_val > 5:
        if surface_dist_roll < 3:
            return (f"{pct}% {liquid_phrase} coverage ({dist_desc}, {world.hydrographics_profile}). "
                    f"Archipelago-rich world ocean with {min_c} minor continents and island chains.")
        elif surface_dist_roll < 7:
            return (f"{pct}% {liquid_phrase} coverage ({dist_desc}, {world.hydrographics_profile}). "
                    f"World ocean with {maj} major and {min_c} minor continents.")
        else:
            return (f"{pct}% {liquid_phrase} coverage ({dist_desc}, {world.hydrographics_profile}). "
                    f"Single massive super-continent surrounded by a global ocean.")
    else:
        if surface_dist_roll < 3:
            return (f"{pct}% {liquid_phrase} coverage ({dist_desc}, {world.hydrographics_profile}). "
                    f"Dispersed surface liquid across {min_c} minor inland seas and rift lakes.")
        elif surface_dist_roll < 7:
            return (f"{pct}% {liquid_phrase} coverage ({dist_desc}, {world.hydrographics_profile}). "
                    f"Continuous landmass with {maj} major and {min_c} minor ocean basins.")
        else:
            return (f"{pct}% {liquid_phrase} coverage ({dist_desc}, {world.hydrographics_profile}). "
                    f"Single concentrated super-ocean basin on a world-spanning continent.")

def generate_life(world: Any, system: Any = None) -> str:
    """Native lifeform ratings (WBH pp.127-131): biomass, biocomplexity,
    biodiversity and compatibility, plus the native and extinct sophont
    checks. Records the profile MXDC on the world."""
    if not world.atmosphere_code or not str(world.atmosphere_code).isalnum():
        return "No life data."

    atm_val = Utils.from_eHex(world.atmosphere_code)
    hyd_val = Utils.from_eHex(getattr(world, 'hydrographics_code', 0) or 0)
    age = getattr(system, 'age_gyr', 4.5) if system is not None else 4.5

    # Biomass rating = 2D + DMs, capped at DM+4 and floored at DM-12
    dm = 0
    if atm_val in (6, 8):
        dm += 2
    elif atm_val in (5, 7, 9):
        dm += 1
    elif atm_val in (0, 1):
        dm -= 12
    elif atm_val in (2, 3):
        dm -= 4
    elif atm_val in (10, 11, 12) or atm_val >= 15:
        dm -= 8

    if hyd_val == 0:
        dm -= 4
    elif hyd_val >= 6:
        dm += 1

    temp = getattr(world, 'mean_temperature', 0.0) or 0.0
    if temp and (temp < 233 or temp > 373):
        dm -= 4
    if age < 1.0:
        dm -= 4  # too young for life to have taken hold

    dm = max(-12, min(4, dm))
    biomass = max(0, Utils.D6(2) + dm)

    if biomass == 0:
        world.biomass_rating = 0
        world.biocomplexity_rating = 0
        world.biodiversity_rating = 0
        world.compatibility_rating = 0
        world.native_lifeform_profile = "0000"
        return "No native life."

    # Biocomplexity = 2D-7 + biomass, with the biomass DM capped at 9
    biocomplexity = max(0, Utils.D6(2) - 7 + min(9, biomass))

    # Biodiversity = 2D-7 + (biomass + biocomplexity)/2, rounded up, minimum 1
    biodiversity = max(1, Utils.D6(2) - 7
                       + math.ceil((biomass + biocomplexity) / 2))

    # Compatibility = 2D - (biomass + biocomplexity)/2 + DMs, rounded down
    comp_dm = 0
    if atm_val in (0, 1, 11, 16, 17):
        comp_dm -= 8
    elif atm_val in (2, 4, 7, 9):
        comp_dm -= 2
    elif atm_val in (3, 5, 8):
        comp_dm += 1
    elif atm_val == 6:
        comp_dm += 2
    elif atm_val in (10, 15):
        comp_dm -= 6
    elif atm_val == 12:
        comp_dm -= 10
    elif atm_val in (13, 14):
        comp_dm -= 1
    if age > 8:
        comp_dm -= 2

    compatibility = max(0, math.floor(
        Utils.D6(2) - (biomass + biocomplexity) / 2 + comp_dm))

    world.biomass_rating = biomass
    world.biocomplexity_rating = biocomplexity
    world.biodiversity_rating = biodiversity
    world.compatibility_rating = compatibility

    e = Utils.eHex
    world.native_lifeform_profile = (
        f"{e(min(33, biomass))}{e(min(33, biocomplexity))}"
        f"{e(min(33, biodiversity))}{e(min(33, compatibility))}")

    # Native and extinct sophont checks for biocomplexity 8+ (WBH p.130)
    if biocomplexity >= 8:
        capped = min(9, biocomplexity)
        if Utils.D6(2) + capped - 7 >= 13:
            world.native_sophont = True
            world.notes.append("Native sophont species present")
        extinct_dm = 1 if age > 5 else 0
        if Utils.D6(2) + capped - 7 + extinct_dm >= 13:
            world.extinct_sophont = True
            world.notes.append("Evidence of an extinct native sophont species")

    if biocomplexity <= 2:
        desc = "Single-cell microbial life only."
    elif biocomplexity <= 5:
        desc = "Simple multicellular structures, fungi-analogues and basic plants."
    elif biocomplexity <= 8:
        desc = "Complex fauna, animal lifeforms and developed biomes."
    else:
        desc = "Extremely complex, diverse biosphere with high biohazard risk."

    return (f"Biomass {e(biomass)}, Biocomplexity {e(biocomplexity)}, "
            f"Biodiversity {e(biodiversity)}, Compatibility {e(compatibility)}. "
            f"{desc}")

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

    rings = [s for s in world.satellites if s.is_ring]
    for sat in rings:
        # Ring Centre Location (PD) = 0.4 + ((1D-1) x 5 + 1D-1) / 30, and a
        # span of at least 0.07 PD (WBH p.78). The span's dice operand is
        # illegible in the source text, so a d100 fraction is used.
        centre = 0.4 + ((Utils.D6() - 1) * 5 + (Utils.D6() - 1)) / 30.0
        span = random.randint(1, 100) / 100.0 * 0.5 + 0.07
        sat.orbit_pd = round(max(0.2, centre), 3)
        sat.ring_width_pd = round(span, 3)

    # Where rings overlap, the outer ring moves out until its inner edge meets
    # the inner ring's outer edge (WBH p.78).
    rings.sort(key=lambda s: s.orbit_pd)
    for i in range(1, len(rings)):
        inner, outer = rings[i - 1], rings[i]
        inner_outer_edge = inner.orbit_pd + inner.ring_width_pd / 2
        if outer.orbit_pd - outer.ring_width_pd / 2 < inner_outer_edge:
            outer.orbit_pd = round(
                inner.orbit_pd + (inner.ring_width_pd + outer.ring_width_pd) / 2, 3)

    for sat in rings:
        sat.period_hours = _moon_period_hours(sat.orbit_pd, size_equiv, mass)

    if rings:
        # Ring profile R0#:C-S,C-S, ...
        world.ring_profile = (
            f"R{len(rings):02d}:" +
            ",".join(f"{r.orbit_pd:.2f}-{r.ring_width_pd:.2f}" for r in rings))

    for sat in world.satellites:
        if sat.is_ring:
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
