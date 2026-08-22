"""Additional temperature scenarios (WBH pp.114-124).

The mean, high and low global temperatures come from temperature.py; this
module implements the scenario machinery layered on top of them: worst-case
extremes, temperature by season, mean temperature by latitude, temperature by
time of day (with the sunlight-portion calculation), twilight-zone worlds,
the altitude temperature factor, multiple-star contributions with the
temperature addition equation, and inherent heat (gas giant residual heat).
"""
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .utils import Utils
from .temperature import _base_temperature, apply_seismic_temperature
from .atmosphere import pressure_at_altitude

STANDARD_YEAR_DAYS = 365.25


def _with_inherent_heat(world: Any, temperature: float) -> float:
    """Adds the world's inherent (seismic) heat to a computed temperature.

    WBH p.125 calls this a background global effect that "should be computed
    last", and p.126 applies it to "all high, low, mean, local or periodic
    temperature values" - so every scenario result carries it, not just the
    three global figures. On a warm world it is negligible; on a cold one it
    can be the whole story."""
    stress = getattr(world, 'total_seismic_stress', 0.0) or 0.0
    return apply_seismic_temperature(temperature, stress)


# ------------------------------------------------------------- worst case

def worst_case_luminosity_modifier(pressure_bar: float) -> float:
    """Variance factors set to 1.0 and only half the atmospheric pressure
    counted (WBH p.115): 1 / (1 + bar/2)."""
    return round(1.0 / (1.0 + max(0.0, pressure_bar) / 2.0), 4)


def worst_case_temperatures(luminosity: float, albedo: float, greenhouse: float,
                            au: float, pressure_bar: float = 0.0,
                            eccentricity: float = 0.0) -> Tuple[float, float]:
    """Worst-case (high, low) temperatures in K (WBH p.115 sidebar).

    Validated against the book's own checks: Terra comes out at about 330K
    and 219K, Zed Prime at 359K and 230K."""
    modifier = worst_case_luminosity_modifier(pressure_bar)
    near_au = au * (1 - eccentricity)
    far_au = au * (1 + eccentricity)
    high = _base_temperature(luminosity * (1 + modifier), albedo, greenhouse,
                             near_au)
    low = _base_temperature(luminosity * (1 - modifier), albedo, greenhouse,
                            far_au)
    return round(high, 1), round(low, 1)


# ------------------------------------------------------------- by season

def seasonal_axial_tilt_factor(tilt_factor: float, days_since_summer_solstice: float,
                               year_length_days: float) -> float:
    """Seasonal Axial Tilt Factor (WBH p.115).

    The adjusted fractional year subtracts the lesser of 0.1 standard years or
    0.1 local years as thermal lag, then cos(fraction x 360 degrees) scales the
    axial tilt factor from +1 (local summer) through 0 (equinox) to -1
    (midwinter)."""
    if year_length_days <= 0:
        return tilt_factor
    lag_days = min(0.1 * STANDARD_YEAR_DAYS, 0.1 * year_length_days)
    fraction = (days_since_summer_solstice - lag_days) / year_length_days
    return round(math.cos(math.radians(fraction * 360.0)) * tilt_factor, 4)


def seasonal_temperature(world: Any, system: Any,
                         days_since_summer_solstice: float,
                         year_length_days: Optional[float] = None) -> float:
    """Global temperature at a point in the year, substituting the seasonal
    axial tilt factor into the luminosity modifier (WBH p.115)."""
    params = _scenario_parameters(world, system)
    if params is None:
        return getattr(world, 'mean_temperature', 0.0) or 0.0
    if year_length_days is None:
        year_length_days = params['period_years'] * STANDARD_YEAR_DAYS

    seasonal = seasonal_axial_tilt_factor(
        params['axial_tilt_factor'], days_since_summer_solstice,
        year_length_days)
    # In winter the seasonal factor turns negative and drags the modifier
    # below zero: the hemisphere then receives less than mean luminosity.
    variance = seasonal + params['rotation_factor'] + params['geographic_factor']
    raw = variance / params['atmospheric_factor']
    luminosity = params['luminosity'] * (1 + max(-1.0, min(1.0, raw)))
    return _with_inherent_heat(world, _base_temperature(
        luminosity, params['albedo'], params['greenhouse'], params['au']))


def season_is_significant(tilt_factor: float, atmospheric_factor: float) -> bool:
    """Seasonal calculation is worthwhile when tilt factor / atmospheric
    factor exceeds 0.05 (WBH p.115)."""
    if atmospheric_factor <= 0:
        return tilt_factor > 0.05
    return tilt_factor / atmospheric_factor > 0.05


# ------------------------------------------------------------ by latitude

def normalise_axial_tilt(tilt_degrees: float) -> float:
    """Axial tilt mapped into 0-90 degrees: negatives are treated as positive
    and tilts beyond 90 are subtracted from 180 (WBH pp.112, 115)."""
    tilt = abs(tilt_degrees) % 360.0
    if tilt > 180.0:
        tilt = 360.0 - tilt
    if tilt > 90.0:
        tilt = 180.0 - tilt
    return tilt


def latitude_zone(axial_tilt: float, latitude: float) -> str:
    """Tropical, Middle or Arctic zone for a latitude (WBH p.116).

    With axial tilt of 45 degrees or more the middle zones vanish and the
    tropical and arctic zones meet or overlap; the arctic claim wins for the
    overlap, matching the Part B procedure."""
    tilt = normalise_axial_tilt(axial_tilt)
    lat = abs(latitude)
    if lat > 90.0 - tilt and tilt > 0:
        return 'Arctic'
    if lat <= tilt:
        return 'Tropical'
    if tilt >= 45.0:
        # No middle zone: everything below the arctic border is tropical
        return 'Tropical'
    return 'Middle'


def latitude_luminosity_adjustment(axial_tilt: float, latitude: float) -> float:
    """Zone Latitude Adjustment (WBH pp.116-117).

    Part A (tilt < 45): the tropical zone gets sin(45 - tilt); the middle and
    arctic zones get sin(45 - latitude). Part B (tilt >= 45): the arctic zone
    still uses sin(45 - latitude) and the equatorial tropical zone freezes at
    the value on the arctic border, sin(45 - (90 - tilt))."""
    tilt = normalise_axial_tilt(axial_tilt)
    lat = abs(latitude)
    if tilt < 45.0:
        if lat <= tilt:
            return round(math.sin(math.radians(45.0 - tilt)), 4)
        return round(math.sin(math.radians(45.0 - lat)), 4)
    arctic_border = 90.0 - tilt
    if lat > arctic_border:
        return round(math.sin(math.radians(45.0 - lat)), 4)
    return round(math.sin(math.radians(45.0 - arctic_border)), 4)


def latitude_temperature(world: Any, system: Any, latitude: float) -> float:
    """Mean annual temperature at a latitude (WBH p.116).

    The zone adjustment divided by the atmospheric factor replaces the axial
    tilt factor; Latitude Luminosity = L x (1 + modifier). At 45 degrees the
    adjustment is zero and the result is the world's mean temperature, which
    is how the book defines the mean."""
    params = _scenario_parameters(world, system)
    if params is None:
        return getattr(world, 'mean_temperature', 0.0) or 0.0
    adjustment = latitude_luminosity_adjustment(params['axial_tilt'], latitude)
    modifier = adjustment / params['atmospheric_factor']
    luminosity = params['luminosity'] * (1 + modifier)
    return _with_inherent_heat(world, _base_temperature(
        luminosity, params['albedo'], params['greenhouse'], params['au']))


def latitude_temperature_profile(world: Any, system: Any,
                                 latitudes: Sequence[int] = (0, 15, 30, 45,
                                                             60, 75, 90),
                                 ) -> Dict[int, float]:
    """Mean temperatures for a set of latitudes, equator to pole."""
    return {int(lat): latitude_temperature(world, system, lat)
            for lat in latitudes}


# ---------------------------------------------------------- by time of day

def hourly_rotation_factor(rotation_factor: float, hours_since_dawn: float,
                           solar_day_hours: float,
                           sunlight_portion: float = 0.5) -> float:
    """Hourly Rotation Factor (WBH p.117).

    Method 1 (even day and night) is the sunlight_portion = 0.5 case; other
    portions use Method 2, which stretches the day and night halves of the
    cycle to their actual lengths. Both apply the book's 15% thermal lag,
    shifted so the curve matches the described behaviour - coldest near dawn,
    full heat in the afternoon (the book's printed '+0.15' would put the
    warmest hour in mid-morning and a warm spike at dawn)."""
    if solar_day_hours <= 0:
        return 0.0
    portion = min(0.999, max(0.001, sunlight_portion))
    hours = hours_since_dawn % solar_day_hours
    daylight_hours = solar_day_hours * portion
    if hours <= daylight_hours:
        fraction = hours / (solar_day_hours * portion * 2.0) - 0.15
    else:
        fraction = (0.5 + (hours - daylight_hours)
                    / (solar_day_hours * (1.0 - portion) * 2.0) - 0.15)
    return round(math.sin(math.radians(fraction * 360.0)) * rotation_factor, 4)


def day_is_significant(rotation_factor: float, atmospheric_factor: float) -> bool:
    """Time-of-day calculation is worthwhile when rotation factor /
    atmospheric factor exceeds 0.05 (WBH p.117)."""
    if atmospheric_factor <= 0:
        return rotation_factor > 0.05
    return rotation_factor / atmospheric_factor > 0.05


def time_of_day_temperature(world: Any, system: Any, hours_since_dawn: float,
                            sunlight_portion: float = 0.5) -> float:
    """Temperature at a time of day, substituting the hourly rotation factor
    into the luminosity modifier (WBH p.117)."""
    params = _scenario_parameters(world, system)
    if params is None:
        return getattr(world, 'mean_temperature', 0.0) or 0.0
    hourly = hourly_rotation_factor(params['rotation_factor'],
                                    hours_since_dawn,
                                    params['solar_day_hours'] or 24.0,
                                    sunlight_portion)
    variance = params['axial_tilt_factor'] + hourly + params['geographic_factor']
    raw = variance / params['atmospheric_factor']
    luminosity = params['luminosity'] * (1 + max(-1.0, min(1.0, raw)))
    return _with_inherent_heat(world, _base_temperature(
        luminosity, params['albedo'], params['greenhouse'], params['au']))


# ------------------------------------------- sunlight portion and hours

def solar_declination(axial_tilt: float, date_solar_days: float,
                      solar_days_in_year: float) -> float:
    """Angle between the sun's rays and the equator plane; the date counts
    solar days since the winter solstice (WBH p.118)."""
    if solar_days_in_year <= 0:
        return 0.0
    tilt = normalise_axial_tilt(axial_tilt)
    return tilt * math.cos(math.radians(360.0 * date_solar_days
                                        / solar_days_in_year))


def sunlight_portion(latitude: float, axial_tilt: float,
                     date_solar_days: float, solar_days_in_year: float) -> float:
    """Fraction of the solar day that is daylight (WBH p.118).

    cos(sunrise) = tan(latitude) x tan(solar declination); above 1.0 the sun
    never rises (polar night), below -1.0 daylight is constant (midnight
    sun). In the book's convention the date runs from the winter solstice,
    so date 0 at high latitude is the depth of polar night."""
    declination = solar_declination(axial_tilt, date_solar_days,
                                    solar_days_in_year)
    lat = max(-89.999, min(89.999, latitude))
    cos_sunrise = math.tan(math.radians(lat)) * math.tan(
        math.radians(declination))
    if cos_sunrise > 1.0:
        return 0.0
    if cos_sunrise < -1.0:
        return 1.0
    sunrise_angle = math.degrees(math.acos(cos_sunrise))
    return round(sunrise_angle / 180.0, 4)


def sunlight_hours(latitude: float, axial_tilt: float, date_solar_days: float,
                   solar_days_in_year: float, solar_day_hours: float) -> float:
    """Actual hours of sunlight for the date and latitude (WBH p.118)."""
    return round(solar_day_hours * sunlight_portion(
        latitude, axial_tilt, date_solar_days, solar_days_in_year), 2)


# ------------------------------------------------------ twilight zone worlds

BRIGHT_SIDE_ROTATION_FACTOR = 1.0
DARK_SIDE_ROTATION_FACTOR = -1.0


def twilight_band_extent(scale_height_km: float, world_size: int) -> float:
    """Extent of each twilight band (civil, nautical, astronomical) in degrees
    of longitude: 6 degrees scaled by scale height and Size (WBH p.121)."""
    if scale_height_km <= 0 or world_size <= 0:
        return 0.0
    return round(6.0 * (scale_height_km / 8.5) * (world_size / 8.0), 3)


def twilight_rotation_factor(degrees_from_terminator: float,
                             star_diameter_sol: float = 1.0,
                             orbit_au: float = 1.0,
                             scale_height_km: float = 8.5,
                             world_size: int = 8) -> float:
    """Rotation factor across a tidally locked world's surface, using the
    simplified mapping method (WBH p.122).

    Positive degrees run into the bright side, negative into the dark side.
    A Sol-sized star at 1 AU shines about 1 degree past the terminator; the
    factor then steps down through the civil (-0.3), nautical (-0.6) and
    astronomical (-1.0) twilight bands, and climbs by 0.2 per 3 degrees on
    the bright side until it reaches +1.0 at 15 degrees."""
    d = degrees_from_terminator
    if d >= 0:
        return round(min(BRIGHT_SIDE_ROTATION_FACTOR, (d / 3.0) * 0.2), 4)

    if orbit_au <= 0:
        sun_reach = 1.0
    else:
        sun_reach = 1.0 * star_diameter_sol / orbit_au
    into_dark = -d
    if into_dark <= sun_reach:
        return 0.0  # the sun is still at least partly visible

    band = twilight_band_extent(scale_height_km, world_size)
    if band <= 0:
        return DARK_SIDE_ROTATION_FACTOR  # no atmosphere, no twilight

    past_sunset = into_dark - sun_reach
    if past_sunset <= band:            # civil twilight: 0 to -0.3
        factor = -0.3 * past_sunset / band
    elif past_sunset <= 2 * band:      # nautical twilight: -0.3 to -0.6
        factor = -0.3 - 0.3 * (past_sunset - band) / band
    elif past_sunset <= 3 * band:      # astronomical twilight: -0.6 to -1.0
        factor = -0.6 - 0.4 * (past_sunset - 2 * band) / band
    else:
        factor = DARK_SIDE_ROTATION_FACTOR
    return round(max(DARK_SIDE_ROTATION_FACTOR, factor), 4)


def eccentricity_libration(eccentricity: float) -> float:
    """Longitudinal libration span in degrees, about 145 x eccentricity
    (WBH p.120)."""
    return round(145.0 * max(0.0, eccentricity), 2)


def tilt_libration(axial_tilt: float, latitude: float) -> float:
    """Latitudinal libration: axial tilt x sin(latitude) (WBH p.121)."""
    return round(normalise_axial_tilt(axial_tilt)
                 * math.sin(math.radians(abs(latitude))), 3)


def atmospheric_refraction(pressure_bar: float, temperature_k: float) -> float:
    """Refraction in degrees: 0.5 x pressure x 300 / temperature (WBH p.121)."""
    if temperature_k <= 0:
        return 0.0
    return round(0.5 * (max(0.0, pressure_bar) * 300.0) / temperature_k, 4)


# ------------------------------------------------- altitude temperature

def altitude_greenhouse_factor(surface_greenhouse: float,
                               surface_pressure_bar: float,
                               altitude_km: float,
                               scale_height_km: float) -> float:
    """Greenhouse factor at altitude (WBH pp.122-123): the initial factor is
    recomputed from the pressure at altitude, and the world's rolled
    greenhouse modifier (the part beyond 0.5 x sqrt(surface pressure)) is
    carried over unchanged."""
    if surface_pressure_bar <= 0:
        return 0.0
    p_a = pressure_at_altitude(surface_pressure_bar, altitude_km,
                               scale_height_km)
    initial_surface = 0.5 * math.sqrt(surface_pressure_bar)
    modifier = surface_greenhouse - initial_surface
    return round(max(0.0, 0.5 * math.sqrt(max(0.0, p_a)) + modifier), 4)


def altitude_temperature(world: Any, system: Any, altitude_km: float) -> float:
    """Temperature at an altitude above mean baseline (WBH pp.122-123). The
    atmospheric factor stays global; only the greenhouse factor thins out."""
    params = _scenario_parameters(world, system)
    if params is None:
        return getattr(world, 'mean_temperature', 0.0) or 0.0
    greenhouse = altitude_greenhouse_factor(
        params['greenhouse'], params['pressure_bar'], altitude_km,
        params['scale_height_km'])
    return _with_inherent_heat(world, _base_temperature(
        params['luminosity'], params['albedo'], greenhouse, params['au']))


# ------------------------------------- multiple stars and inherent heat

def add_temperatures(*temperatures: float) -> float:
    """Temperature addition equation: (sum of T^4)^(1/4) (WBH p.125)."""
    total = sum(max(0.0, t) ** 4 for t in temperatures)
    return round(total ** 0.25, 2)


def star_temperature_contributions(world: Any, system: Any,
                                   worst_case_eccentricity: bool = True) -> dict:
    """High, mean and low temperature contributions from every star in the
    system, combined with the temperature addition equation (WBH pp.123-124).

    Nearest distance is the difference of the orbits (eccentricities pulled
    as close as possible when worst_case_eccentricity), mean distance is the
    root of the sum of squares, and furthest is the sum of the orbits with
    eccentricities pushed apart."""
    albedo = getattr(world, 'albedo', 0.0) or 0.3
    greenhouse = getattr(world, 'greenhouse_factor', 0.0) or 0.0

    world_au = getattr(world, 'orbit_au', 0.0) or 0.0
    world_ecc = getattr(world, 'eccentricity', 0.0) or 0.0
    parent_group = getattr(world, 'parent_star_group', None)
    if (not world_au) and getattr(world, 'parent_body', None):
        world_au = getattr(world.parent_body, 'orbit_au', 0.0) or 0.0
        world_ecc = getattr(world.parent_body, 'eccentricity', 0.0) or 0.0
        parent_group = getattr(world.parent_body, 'parent_star_group', None)
    if world_au <= 0:
        return {'stars': [], 'low': 0.0, 'mean': 0.0, 'high': 0.0}

    group = next((s for s in system.stars if s.designation == parent_group),
                 None) or system.primary_star
    home_components = set(getattr(group, 'components', None)
                          or [group.designation])

    rows = []
    for star in system.stars:
        if star.is_composite or star.luminosity <= 0:
            continue
        if star.designation in home_components and not star.parent:
            star_au, star_ecc = 0.0, 0.0        # the primary itself
        else:
            star_au = Utils.orbit_to_au(star.orbit_num)
            star_ecc = star.eccentricity or 0.0

        if star_au <= 0:
            near = world_au * (1 - world_ecc)
            mean_d = world_au
            far = world_au * (1 + world_ecc)
        else:
            if worst_case_eccentricity:
                if star_au < world_au:  # interior star
                    near = abs(world_au * (1 - world_ecc)
                               - star_au * (1 + star_ecc))
                else:
                    near = abs(world_au * (1 + world_ecc)
                               - star_au * (1 - star_ecc))
                far = world_au * (1 + world_ecc) + star_au * (1 + star_ecc)
            else:
                near = abs(world_au - star_au)
                far = world_au + star_au
            mean_d = math.sqrt(world_au ** 2 + star_au ** 2)

        near = max(near, 1e-6)
        rows.append({
            'designation': star.designation,
            'luminosity': star.luminosity,
            'high': round(_base_temperature(star.luminosity, albedo,
                                            greenhouse, near), 2),
            'mean': round(_base_temperature(star.luminosity, albedo,
                                            greenhouse, mean_d), 2),
            'low': round(_base_temperature(star.luminosity, albedo,
                                           greenhouse, far), 2),
        })

    return {
        'stars': rows,
        'high': add_temperatures(*(r['high'] for r in rows)),
        'mean': add_temperatures(*(r['mean'] for r in rows)),
        'low': add_temperatures(*(r['low'] for r in rows)),
    }


def gas_giant_inherent_temperature(mass_terran: float, age_gyr: float) -> float:
    """Residual heat of a gas giant: 80 x fourth root of mass over the square
    root of age (WBH p.125). The book's worked example - 1,200 Earth masses at
    6.336 Gyr - comes out at 187K."""
    if mass_terran <= 0 or age_gyr <= 0:
        return 0.0
    return round(80.0 * (mass_terran ** 0.25) / math.sqrt(age_gyr), 1)


# ----------------------------------------------------------- orchestration

def _scenario_parameters(world: Any, system: Any) -> Optional[dict]:
    """Gathers the inputs the scenarios share: star luminosity, orbit AU,
    albedo, greenhouse and the variance factors recorded by
    detail_temperatures."""
    parent_group = getattr(world, 'parent_star_group', None)
    au = getattr(world, 'orbit_au', 0.0) or 0.0
    if (not au) and getattr(world, 'parent_body', None):
        parent_group = getattr(world.parent_body, 'parent_star_group', None)
        au = getattr(world.parent_body, 'orbit_au', 0.0) or 0.0

    star = next((s for s in getattr(system, 'stars', [])
                 if s.designation == parent_group), None)
    if star is None:
        star = getattr(system, 'primary_star', None)
    if star is None or au <= 0:
        return None

    pressure = getattr(world, 'atmos_pressure_bar', 0.0) or 0.0
    return {
        'luminosity': star.luminosity,
        'au': au,
        'albedo': getattr(world, 'albedo', 0.0) or 0.0,
        'greenhouse': getattr(world, 'greenhouse_factor', 0.0) or 0.0,
        'axial_tilt': getattr(world, 'axial_tilt', 0.0) or 0.0,
        'axial_tilt_factor': getattr(world, 'axial_tilt_factor', 0.0) or 0.0,
        'rotation_factor': getattr(world, 'rotation_factor', 0.0) or 0.0,
        'geographic_factor': getattr(world, 'geographic_factor', 0.0) or 0.0,
        'atmospheric_factor': getattr(world, 'atmospheric_factor', 0.0) or (1.0 + pressure),
        'pressure_bar': pressure,
        'scale_height_km': getattr(world, 'scale_height_km', 0.0) or 0.0,
        'solar_day_hours': getattr(world, 'rotation_period_hours', 0.0) or 0.0,
        'period_years': (getattr(world, 'period_years', 0.0)
                         or getattr(getattr(world, 'parent_body', None),
                                    'period_years', 0.0) or 1.0),
    }


def detail_temperature_scenarios(world: Any, system: Any) -> None:
    """Records the scenario outputs on the world: worst-case extremes and the
    mean temperature by latitude profile. The finer-grained scenarios
    (season, time of day, altitude, twilight mapping) stay on demand since
    they take a time or place as input."""
    params = _scenario_parameters(world, system)
    if params is None:
        return
    high, low = worst_case_temperatures(
        params['luminosity'], params['albedo'], params['greenhouse'],
        params['au'], params['pressure_bar'],
        getattr(world, 'eccentricity', 0.0) or 0.0)
    # The same inherent (seismic) heat that raises the ordinary temperatures
    # applies to the worst-case pair.
    stress = getattr(world, 'total_seismic_stress', 0.0) or 0.0
    high = apply_seismic_temperature(high, stress)
    low = apply_seismic_temperature(low, stress)
    # The worst case is by definition at least as extreme as the ordinary
    # global high and low; rounding must not be allowed to invert that.
    ordinary_high = getattr(world, 'high_temperature', 0.0) or 0.0
    ordinary_low = getattr(world, 'low_temperature', 0.0) or 0.0
    world.worst_case_high = max(high, ordinary_high)
    world.worst_case_low = min(low, ordinary_low)
    world.latitude_temperatures = latitude_temperature_profile(world, system)
