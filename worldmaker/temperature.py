"""Detailed temperature and seismology (WBH pp.107-126).

Replaces the constant albedo/greenhouse approximations with the book's tables,
and adds the high/low temperature chain, surface tidal effects, seismic stress
and tectonic plate counts.
"""
import math
from typing import Any, Optional

from .utils import Utils

AU_KM = 149597870.9


# --------------------------------------------------------------- albedo

def roll_albedo(world: Any, hzco: float = 0.0) -> float:
    """Albedo Range table (WBH p.110).

    World type sets the base; Atmosphere and Hydrographics add modifiers.
    Results are clamped to 0.02-0.98."""
    density = getattr(world, 'density', 0.0) or 0.0
    body_type = getattr(world, 'body_type', 'Terrestrial')
    orbit_num = getattr(world, 'orbit_num', 0.0)
    if not orbit_num and getattr(world, 'parent_body', None):
        orbit_num = getattr(world.parent_body, 'orbit_num', 0.0)

    if body_type == 'Gas Giant':
        albedo = 0.05 + Utils.D6(2) * 0.05
    elif density > 0.5:
        # Rocky terrestrial
        albedo = 0.04 + (Utils.D6(2) - 2) * 0.02
    elif hzco and orbit_num > hzco + 2:
        # Icy terrestrial well beyond the habitable zone: bright surfaces
        albedo = 0.25 + (Utils.D6(2) - 2) * 0.07
        if albedo <= 0.4:
            albedo -= (Utils.D6() - 1) * 0.05
    else:
        # Icy terrestrial within HZCO+2
        albedo = 0.2 + (Utils.D6(2) - 3) * 0.05

    atm = Utils.from_eHex(getattr(world, 'atmosphere_code', 0) or 0)
    hyd = Utils.from_eHex(getattr(world, 'hydrographics_code', 0) or 0)

    if 1 <= atm <= 3 or atm == 14:
        albedo += (Utils.D6(2) - 3) * 0.01
    elif 4 <= atm <= 9:
        albedo += Utils.D6(2) * 0.01
    elif atm in (10, 11, 12) or atm >= 15:
        albedo += (Utils.D6(2) - 2) * 0.05
    elif atm == 13:
        albedo += Utils.D6(2) * 0.03

    if 2 <= hyd <= 5:
        albedo += (Utils.D6(2) - 2) * 0.02
    elif hyd >= 6:
        albedo += (Utils.D6(2) - 4) * 0.03

    return round(max(0.02, min(0.98, albedo)), 3)


# ----------------------------------------------------------- greenhouse

def roll_greenhouse(world: Any) -> float:
    """Initial Greenhouse Factor = 0.5 x sqrt(pressure in bar), then the
    Greenhouse Modifiers table (WBH p.110)."""
    pressure = getattr(world, 'atmos_pressure_bar', 0.0) or 0.0
    atm = Utils.from_eHex(getattr(world, 'atmosphere_code', 0) or 0)

    if atm == 0 or pressure <= 0:
        return 0.0

    factor = 0.5 * math.sqrt(pressure)

    if 1 <= atm <= 9 or atm in (13, 14):
        factor += Utils.D6(3) * 0.01
    elif atm in (10, 15):  # Exotic or Unusual
        factor *= max(0.5, Utils.D6() - 1)
    elif atm in (11, 12, 16, 17):  # Corrosive, Insidious, gas envelopes
        roll = Utils.D6()
        factor *= (Utils.D6(3) if roll == 6 else roll)

    return round(max(0.0, factor), 4)


# ------------------------------------------------- temperature formulas

def _base_temperature(luminosity: float, albedo: float, greenhouse: float,
                      au: float) -> float:
    """279 x (L x (1 - albedo) x (1 + greenhouse) / AU^2)^0.25 (WBH p.108)."""
    if au <= 0 or luminosity <= 0:
        return 0.0
    value = luminosity * (1 - albedo) * (1 + greenhouse) / (au ** 2)
    if value <= 0:
        return 0.0
    return 279.0 * (value ** 0.25)


def axial_tilt_factor(tilt_degrees: float, year_length_years: float) -> float:
    """Basic Axial Tilt Factor, sin(tilt), adjusted for very short or long
    years (WBH p.113)."""
    tilt = max(0.0, min(90.0, abs(tilt_degrees)))
    factor = math.sin(math.radians(tilt))

    if year_length_years and year_length_years < 0.1:
        factor /= 2.0
    elif year_length_years and year_length_years > 2.0:
        increase = min(0.25, 0.01 * year_length_years)
        factor = min(1.0, factor + increase)

    return round(min(1.0, factor), 4)


def rotation_factor(solar_day_hours: float, tidally_locked: bool = False) -> float:
    """sqrt(solar day in hours) / 50, capped at 1.0 (WBH p.113)."""
    if tidally_locked or solar_day_hours > 2500:
        return 1.0
    if solar_day_hours <= 0:
        return 0.0
    return round(min(1.0, math.sqrt(abs(solar_day_hours)) / 50.0), 4)


def geographic_factor(hydrographics: int, surface_distribution: int = 5) -> float:
    """(10 - HYD) / 20, modified by how concentrated surface water is
    (WBH p.113)."""
    factor = (10 - hydrographics) / 20.0
    if 2 <= hydrographics <= 8:
        if surface_distribution >= 9:
            factor += 0.1
        elif surface_distribution <= 1:
            factor -= 0.1
    return round(factor, 4)


def calculate_temperature_range(world: Any, system: Any, luminosity: float,
                                albedo: float, greenhouse: float,
                                au: float) -> dict:
    """High and low global temperatures via the variance factors and the
    luminosity modifier (WBH pp.112-115)."""
    tilt = getattr(world, 'axial_tilt', 0.0) or 0.0
    period = getattr(world, 'period_years', 0.0) or 0.0
    if not period and getattr(world, 'parent_body', None):
        period = getattr(world.parent_body, 'period_years', 0.0) or 0.0

    solar_day = getattr(world, 'rotation_period_hours', 0.0) or 0.0
    locked = any('Tidally Locked' in n for n in getattr(world, 'notes', []))

    hyd = Utils.from_eHex(getattr(world, 'hydrographics_code', 0) or 0)
    pressure = getattr(world, 'atmos_pressure_bar', 0.0) or 0.0

    atf = axial_tilt_factor(tilt, period)
    rf = rotation_factor(solar_day, locked)
    gf = geographic_factor(hyd)

    variance = atf + rf + gf
    atmospheric_factor = 1.0 + pressure
    lum_modifier = variance / atmospheric_factor if atmospheric_factor else variance
    lum_modifier = max(0.0, min(1.0, lum_modifier))

    eccentricity = getattr(world, 'eccentricity', 0.0) or 0.0
    if not eccentricity and getattr(world, 'parent_body', None):
        eccentricity = getattr(world.parent_body, 'eccentricity', 0.0) or 0.0

    near_au = au * (1 - eccentricity)
    far_au = au * (1 + eccentricity)

    high = _base_temperature(luminosity * (1 + lum_modifier), albedo,
                             greenhouse, near_au)
    low = _base_temperature(luminosity * (1 - lum_modifier), albedo,
                            greenhouse, far_au)

    return {
        'axial_tilt_factor': atf,
        'rotation_factor': rf,
        'geographic_factor': gf,
        'variance_factors': round(variance, 4),
        'atmospheric_factor': round(atmospheric_factor, 4),
        'luminosity_modifier': round(lum_modifier, 4),
        'high_temperature': round(high, 1),
        'low_temperature': round(low, 1),
    }


# ------------------------------------------------- surface tidal effects

def star_tidal_effect(star_mass: float, world_size: float, au: float) -> float:
    """Tidal effect of the primary on a world, in metres (WBH p.126)."""
    if au <= 0 or world_size <= 0:
        return 0.0
    return 3.2 * (star_mass * world_size) / (32 * (au ** 3))


def body_tidal_effect(other_mass_terran: float, world_size: float,
                      distance_km: float) -> float:
    """Tidal effect of a moon on its planet, or a planet on its moon, in
    metres (WBH p.126). Distance is expressed in millions of km."""
    if distance_km <= 0 or world_size <= 0:
        return 0.0
    d = distance_km / 1000000.0
    if d <= 0:
        return 0.0
    return 3.2 * (other_mass_terran * world_size) / (d ** 3)


def calculate_surface_tides(world: Any, system: Any) -> float:
    """Total surface tidal effect in metres, from the star(s) and any moons."""
    size = Utils.from_eHex(getattr(world, 'size_code', 0) or 0)
    if not size:
        return 0.0

    total = 0.0
    parent = next((s for s in getattr(system, 'stars', [])
                   if s.designation == getattr(world, 'parent_star_group', None)),
                  None)
    star_mass = parent.mass if parent else (
        system.primary_star.mass if getattr(system, 'primary_star', None) else 1.0)

    au = getattr(world, 'orbit_au', 0.0) or 0.0
    total += star_tidal_effect(star_mass, size, au)

    diameter = getattr(world, 'diameter_km', 0.0) or 0.0
    for sat in getattr(world, 'satellites', []):
        if sat.is_ring or not sat.orbit_pd or not diameter:
            continue
        distance_km = sat.orbit_pd * diameter
        total += body_tidal_effect(sat.mass_terran, size, distance_km)

    return round(total, 4)


# ------------------------------------------------------------ seismology

def residual_seismic_stress(world: Any, system_age_gyr: float,
                            is_moon: bool = False) -> float:
    """(Size - Age(Gyr) + DMs)^2, floored at zero before squaring
    (WBH p.125)."""
    size = Utils.from_eHex(getattr(world, 'size_code', 0) or 0)
    density = getattr(world, 'density', 0.0) or 0.0

    dm = 0
    if is_moon:
        dm += 1
    if density > 1.0:
        dm += 1

    value = size - system_age_gyr + dm
    if value < 1:
        return 0.0
    return round(value ** 2, 3)


def tidal_heating_factor(primary_mass: float, world_size: float,
                         eccentricity: float, distance_au: float,
                         period_years: float, world_mass: float) -> float:
    """(Primary Mass)^2 x (Size)^5 x ecc^2 / (3000 x Distance^5 x Period x
    Mass) (WBH p.127)."""
    if (eccentricity <= 0 or distance_au <= 0 or period_years <= 0
            or world_mass <= 0 or world_size <= 0):
        return 0.0
    denominator = 3000 * (distance_au ** 5) * period_years * world_mass
    if denominator <= 0:
        return 0.0
    numerator = (primary_mass ** 2) * (world_size ** 5) * (eccentricity ** 2)
    return round(numerator / denominator, 3)


def calculate_seismology(world: Any, system: Any, is_moon: bool = False) -> dict:
    """Total seismic stress and major tectonic plate count (WBH pp.125-128)."""
    size = Utils.from_eHex(getattr(world, 'size_code', 0) or 0)
    hyd = Utils.from_eHex(getattr(world, 'hydrographics_code', 0) or 0)

    residual = residual_seismic_stress(world, getattr(system, 'age_gyr', 0.0),
                                       is_moon)
    tides = calculate_surface_tides(world, system)
    tidal_stress = math.floor(tides / 10.0)

    parent = next((s for s in getattr(system, 'stars', [])
                   if s.designation == getattr(world, 'parent_star_group', None)),
                  None)
    primary_mass = parent.mass if parent else 1.0
    heating = tidal_heating_factor(
        primary_mass, size,
        getattr(world, 'eccentricity', 0.0) or 0.0,
        getattr(world, 'orbit_au', 0.0) or 0.0,
        getattr(world, 'period_years', 0.0) or 0.0,
        getattr(world, 'mass_terran', 0.0) or 0.0)

    total = round(residual + tidal_stress + heating, 3)

    # Major tectonic plates = Size + Hydrographics - 2D + DMs
    plate_dm = 0
    if total > 50:
        plate_dm += 2
    elif total < 1:
        plate_dm -= 2
    plates = max(0, size + hyd - Utils.D6(2) + plate_dm)

    if total > 100:
        activity = "Constant volcanism and near-continuous earthquakes"
    elif total > 50:
        activity = "Frequent eruptions and major seismic activity"
    elif total > 10:
        activity = "Active tectonics with regular earthquakes"
    elif total >= 1:
        activity = "Mild tectonic activity"
    else:
        activity = "Geologically dead"

    return {
        'residual_seismic_stress': residual,
        'surface_tide_metres': tides,
        'tidal_stress_factor': tidal_stress,
        'tidal_heating_factor': heating,
        'total_seismic_stress': total,
        'tectonic_plates': plates,
        'seismic_activity': activity,
    }


def apply_seismic_temperature(temperature: float, total_stress: float) -> float:
    """New Temperature = (Old Temperature^4 + Total Seismic Stress^4)^(1/4)
    (WBH p.127).

    A world receiving no warmth at all from its sun still sits at whatever
    its own internal heat sustains: the book's own example is a rogue world
    in deep space, where "the seismic stress heating value would be the
    primary factor in its surface temperature"."""
    if total_stress <= 0:
        return round(max(0.0, temperature), 1)
    return round((max(0.0, temperature) ** 4 + total_stress ** 4) ** 0.25, 1)


# --------------------------------------------------------- orchestration

def detail_temperatures(world: Any, system: Any, is_moon: bool = False) -> None:
    """Computes albedo, greenhouse, mean/high/low temperatures, tides and
    seismology for a world, recording each on the body."""
    parent_group = getattr(world, 'parent_star_group', None)
    au = getattr(world, 'orbit_au', 0.0) or 0.0
    if is_moon and getattr(world, 'parent_body', None):
        parent_group = getattr(world.parent_body, 'parent_star_group', None)
        au = getattr(world.parent_body, 'orbit_au', 0.0) or 0.0

    star = next((s for s in system.stars if s.designation == parent_group), None)
    if star is None:
        star = system.primary_star
    if star is None or au <= 0:
        return

    luminosity = star.luminosity
    hzco = star.hzco

    world.albedo = roll_albedo(world, hzco)
    world.greenhouse_factor = roll_greenhouse(world)

    mean = _base_temperature(luminosity, world.albedo,
                             world.greenhouse_factor, au)

    seis = calculate_seismology(world, system, is_moon)
    for key, value in seis.items():
        setattr(world, key, value)

    world.mean_temperature = apply_seismic_temperature(
        mean, seis['total_seismic_stress'])

    rng = calculate_temperature_range(world, system, luminosity, world.albedo,
                                      world.greenhouse_factor, au)
    for key, value in rng.items():
        setattr(world, key, value)

    world.high_temperature = apply_seismic_temperature(
        world.high_temperature, seis['total_seismic_stress'])
    world.low_temperature = apply_seismic_temperature(
        world.low_temperature, seis['total_seismic_stress'])

    # The physics guarantees low <= mean <= high, but the three are rounded
    # independently; keep the ordering true after rounding.
    world.low_temperature = min(world.low_temperature, world.mean_temperature)
    world.high_temperature = max(world.high_temperature, world.mean_temperature)
