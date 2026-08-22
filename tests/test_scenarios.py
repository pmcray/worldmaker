"""Tests for the additional temperature scenarios (WBH pp.114-124)."""
import math
import random

import pytest

import worldmaker as wm
from worldmaker.classes import PlanetaryBody, Star, StellarSystem
from worldmaker.scenarios import (
    add_temperatures,
    altitude_greenhouse_factor,
    altitude_temperature,
    atmospheric_refraction,
    day_is_significant,
    eccentricity_libration,
    gas_giant_inherent_temperature,
    hourly_rotation_factor,
    latitude_luminosity_adjustment,
    latitude_temperature,
    latitude_zone,
    normalise_axial_tilt,
    season_is_significant,
    seasonal_axial_tilt_factor,
    seasonal_temperature,
    solar_declination,
    star_temperature_contributions,
    sunlight_hours,
    sunlight_portion,
    time_of_day_temperature,
    twilight_band_extent,
    twilight_rotation_factor,
    worst_case_luminosity_modifier,
    worst_case_temperatures,
)

N = 60


@pytest.fixture(scope="module")
def systems():
    random.seed(20260805)
    return [wm.generate_full_system(f"S{i}") for i in range(N)]


def _terra_system():
    system = StellarSystem(age_gyr=4.568)
    system.stars.append(Star(designation="A", spectral_type="G2 V", mass=1.0,
                             luminosity=1.0, hzco=3.0))
    world = PlanetaryBody(
        parent_star_group="A", body_type="Terrestrial", size_code="8",
        orbit_num=3.0, orbit_au=1.0, eccentricity=0.0167, period_years=1.0,
        axial_tilt=23.5, rotation_period_hours=24.0,
        atmosphere_code="6", hydrographics_code="7")
    world.albedo = 0.3
    world.greenhouse_factor = 0.5 * math.sqrt(1.013) + 0.10
    world.atmos_pressure_bar = 1.013
    world.axial_tilt_factor = 0.399
    world.rotation_factor = 0.098
    world.geographic_factor = 0.15
    world.atmospheric_factor = 2.013
    world.scale_height_km = 8.5
    world.mean_temperature = 288.0
    return world, system


# ------------------------------------------------------------- worst case

def test_worst_case_matches_terra_benchmark():
    """The book's check: Terra's worst-case luminosity modifier is 0.67,
    giving roughly 330K and 219K."""
    assert worst_case_luminosity_modifier(1.013) == pytest.approx(0.67, abs=0.01)
    greenhouse = 0.5 * math.sqrt(1.013) + 0.10
    high, low = worst_case_temperatures(1.0, 0.3, greenhouse, 1.0, 1.013, 0.0167)
    assert high == pytest.approx(330, abs=4)
    assert low == pytest.approx(219, abs=4)


def test_worst_case_matches_zed_prime_high():
    """Zed Prime: modifier 0.657 and a worst-case high of 359K."""
    assert worst_case_luminosity_modifier(1.04) == pytest.approx(0.657, abs=0.002)
    high, low = worst_case_temperatures(1.419, 0.33, 0.59, 1.06, 1.04, 0.10)
    assert high == pytest.approx(359, abs=3)
    assert low < 260


def test_worst_case_brackets_the_ordinary_range(systems):
    """Worst case must be at least as extreme as the ordinary high/low."""
    checked = 0
    for s in systems:
        for w in s.all_worlds:
            if w.body_type != "Terrestrial" or not w.worst_case_high:
                continue
            checked += 1
            assert w.worst_case_high >= w.high_temperature - 0.1
            assert w.worst_case_low <= w.low_temperature + 0.1
    assert checked > 50


# ------------------------------------------------------------- by season

def test_seasonal_factor_cycles_between_extremes():
    """Full tilt factor at local summer (after the lag), its negative in
    midwinter, near zero at the equinoxes."""
    year = 365.25
    lag = 36.525
    assert seasonal_axial_tilt_factor(0.4, lag, year) == pytest.approx(0.4)
    assert seasonal_axial_tilt_factor(0.4, year / 2 + lag, year) == pytest.approx(-0.4)
    assert abs(seasonal_axial_tilt_factor(0.4, year / 4 + lag, year)) < 0.01
    assert abs(seasonal_axial_tilt_factor(0.4, 3 * year / 4 + lag, year)) < 0.01


def test_seasonal_lag_uses_lesser_of_standard_and_local():
    """A short local year lags by a tenth of itself, not of a standard year."""
    short_year = 50.0
    assert seasonal_axial_tilt_factor(0.5, 5.0, short_year) == pytest.approx(0.5)


def test_summer_warmer_than_winter():
    world, system = _terra_system()
    summer = seasonal_temperature(world, system, 36.5, 365.25)
    winter = seasonal_temperature(world, system, 219.1, 365.25)
    assert summer > world.mean_temperature > winter


def test_season_significance_threshold():
    assert season_is_significant(0.4, 2.0)
    assert not season_is_significant(0.05, 2.0)


# ------------------------------------------------------------ by latitude

def test_axial_tilt_normalisation():
    assert normalise_axial_tilt(-30) == 30
    assert normalise_axial_tilt(120) == 60
    assert normalise_axial_tilt(23.5) == 23.5


def test_latitude_zones_for_moderate_tilt():
    """Tropical up to the tilt, arctic above 90 minus tilt, middle between."""
    assert latitude_zone(23.5, 10) == 'Tropical'
    assert latitude_zone(23.5, 45) == 'Middle'
    assert latitude_zone(23.5, 80) == 'Arctic'


def test_latitude_zones_for_extreme_tilt():
    """At 45 degrees or more of tilt there is no middle zone."""
    assert latitude_zone(60, 10) == 'Tropical'
    assert latitude_zone(60, 50) == 'Arctic'
    for lat in range(0, 91, 5):
        assert latitude_zone(75, lat) in ('Tropical', 'Arctic')


def test_latitude_adjustment_cases():
    """Case 1: tropical zone gets sin(45 - tilt); case 2 gets
    sin(45 - latitude); Part B freezes the tropical value at the arctic
    border."""
    assert latitude_luminosity_adjustment(23.5, 10) == pytest.approx(
        math.sin(math.radians(21.5)), abs=1e-3)
    assert latitude_luminosity_adjustment(23.5, 60) == pytest.approx(
        math.sin(math.radians(-15)), abs=1e-3)
    # 45 degrees latitude is the definition of the mean: adjustment zero
    assert latitude_luminosity_adjustment(23.5, 45) == pytest.approx(0.0, abs=1e-6)
    # Part B: tilt 60, border at 30; below it the border value applies
    border_value = math.sin(math.radians(45 - 30))
    assert latitude_luminosity_adjustment(60, 10) == pytest.approx(border_value, abs=1e-3)
    assert latitude_luminosity_adjustment(60, 30) == pytest.approx(border_value, abs=1e-3)
    assert latitude_luminosity_adjustment(60, 80) == pytest.approx(
        math.sin(math.radians(-35)), abs=1e-3)


def test_latitude_temperature_gradient():
    """Equator warmer than mean, mean at 45 degrees, poles colder."""
    world, system = _terra_system()
    equator = latitude_temperature(world, system, 0)
    mid = latitude_temperature(world, system, 45)
    pole = latitude_temperature(world, system, 90)
    assert equator > mid > pole
    assert mid == pytest.approx(288, abs=3)


def test_scenarios_carry_the_worlds_inherent_heat(systems):
    """Inherent (seismic) heat is a background global effect applied to all
    high, low, mean, local and periodic temperatures (WBH pp.125-126). On a
    cold, seismically active world it dominates, so a scenario that skipped
    it would report a temperature far below the world's own mean."""
    checked = 0
    for s in systems:
        for w in s.all_worlds:
            if w.body_type != "Terrestrial" or not w.mean_temperature:
                continue
            if w.total_seismic_stress <= w.mean_temperature / 2:
                continue     # inherent heat is negligible on this world
            checked += 1
            # The mean is defined as the temperature at 45 degrees latitude
            assert w.latitude_temperatures[45] == pytest.approx(
                w.mean_temperature, abs=0.6)
            assert w.worst_case_low >= w.total_seismic_stress - 0.6
            for temperature in w.latitude_temperatures.values():
                assert temperature >= w.total_seismic_stress - 0.6
    assert checked, "no seismically dominated worlds in the sample"


def test_mean_is_the_temperature_at_45_degrees(systems):
    """The book defines a world's mean temperature as its mean at 45 degrees
    latitude (WBH p.116)."""
    checked = 0
    for s in systems:
        for w in s.all_worlds:
            if w.body_type != "Terrestrial" or not w.latitude_temperatures:
                continue
            checked += 1
            assert w.latitude_temperatures[45] == pytest.approx(
                w.mean_temperature, rel=0.02, abs=0.6)
    assert checked > 50


def test_latitude_profile_recorded_on_generated_worlds(systems):
    checked = 0
    for s in systems:
        for w in s.all_worlds:
            if w.body_type != "Terrestrial" or not w.latitude_temperatures:
                continue
            checked += 1
            profile = w.latitude_temperatures
            assert set(profile) == {0, 15, 30, 45, 60, 75, 90}
            # Monotone non-increasing from equator to pole for tilt < 45
            if 0 < normalise_axial_tilt(w.axial_tilt) < 45:
                lats = sorted(profile)
                for a, b in zip(lats, lats[1:]):
                    assert profile[a] >= profile[b] - 0.11, (
                        w.axial_tilt, profile)
    assert checked > 50


# ---------------------------------------------------------- time of day

def test_hourly_rotation_factor_shape():
    """Coldest near dawn, warmest in the afternoon, bounded by the rotation
    factor."""
    values = {h: hourly_rotation_factor(1.0, h, 24.0) for h in range(24)}
    assert values[0] < -0.7                       # cold at dawn
    warmest = max(values, key=values.get)
    assert 7 <= warmest <= 12                     # afternoon of a dawn-start clock
    coldest = min(values, key=values.get)
    assert coldest >= 19                          # small hours before dawn
    assert all(-1.0 <= v <= 1.0 for v in values.values())


def test_hourly_rotation_factor_uneven_days_continuous():
    """Method 2 joins the day and night halves without a jump at dusk."""
    portion = 0.75
    daylight = 24.0 * portion
    before = hourly_rotation_factor(1.0, daylight - 0.01, 24.0, portion)
    after = hourly_rotation_factor(1.0, daylight + 0.01, 24.0, portion)
    assert before == pytest.approx(after, abs=0.01)


def test_time_of_day_temperature_afternoon_beats_predawn():
    """The daily curve peaks in the afternoon and bottoms out before dawn;
    the swing stays inside the world's global high/low band."""
    world, system = _terra_system()
    afternoon = time_of_day_temperature(world, system, 9.6)
    predawn = time_of_day_temperature(world, system, 21.6)
    assert afternoon > predawn
    # The full swing is set by the rotation factor's contribution
    assert afternoon - predawn > 5


def test_day_significance_threshold():
    assert day_is_significant(0.5, 2.0)
    assert not day_is_significant(0.05, 2.0)


# ------------------------------------------- sunlight portion and hours

def test_sunlight_portion_at_equator_is_half():
    for date in (0, 91, 182, 273):
        assert sunlight_portion(0, 23.5, date, 365) == pytest.approx(0.5, abs=0.01)


def test_sunlight_portion_polar_extremes():
    """Date runs from the winter solstice: polar night at date 0, midnight
    sun half a year later."""
    assert sunlight_portion(80, 23.5, 0, 365) == 0.0
    assert sunlight_portion(80, 23.5, 182.5, 365) == 1.0


def test_sunlight_hours_scale_with_solar_day():
    assert sunlight_hours(0, 23.5, 91, 365, 24.0) == pytest.approx(12.0, abs=0.3)
    assert sunlight_hours(0, 23.5, 91, 365, 48.0) == pytest.approx(24.0, abs=0.6)


def test_solar_declination_cycle():
    assert solar_declination(23.5, 0, 365) == pytest.approx(23.5, abs=0.01)
    assert solar_declination(23.5, 182.5, 365) == pytest.approx(-23.5, abs=0.01)
    assert abs(solar_declination(23.5, 91.25, 365)) < 0.5


# ------------------------------------------------------ twilight zones

def test_twilight_rotation_factor_mapping():
    """+1.0 deep in the bright side, 0 where the sun is partly visible,
    stepping to -1.0 through the twilight bands (WBH p.122)."""
    assert twilight_rotation_factor(20) == 1.0
    assert twilight_rotation_factor(15) == 1.0
    assert twilight_rotation_factor(3) == pytest.approx(0.2)
    assert twilight_rotation_factor(-0.5) == 0.0     # sun partly visible
    civil_dark = twilight_rotation_factor(-7)        # ~ dark edge of civil
    assert civil_dark == pytest.approx(-0.3, abs=0.02)
    assert twilight_rotation_factor(-13) == pytest.approx(-0.6, abs=0.02)
    assert twilight_rotation_factor(-19) == pytest.approx(-1.0, abs=0.02)
    assert twilight_rotation_factor(-90) == -1.0


def test_twilight_monotone_into_the_dark():
    previous = 1.0
    for degrees in range(15, -30, -1):
        value = twilight_rotation_factor(float(degrees))
        assert value <= previous + 1e-9
        previous = value


def test_airless_world_has_no_twilight():
    assert twilight_band_extent(0.0, 8) == 0.0
    assert twilight_rotation_factor(-2, scale_height_km=0.0) == -1.0


def test_twilight_helpers():
    """Luna's eccentricity gives a libration span near 8 degrees; refraction
    on Terra is about half a degree."""
    assert eccentricity_libration(0.055) == pytest.approx(8.0, abs=0.1)
    assert atmospheric_refraction(1.013, 288) == pytest.approx(0.5, abs=0.05)


# ------------------------------------------------- altitude temperature

def test_altitude_cools_the_world():
    world, system = _terra_system()
    surface = altitude_temperature(world, system, 0.0)
    high = altitude_temperature(world, system, 5.0)
    higher = altitude_temperature(world, system, 15.0)
    assert surface > high > higher
    assert surface == pytest.approx(288, abs=3)


def test_altitude_greenhouse_keeps_rolled_modifier():
    """The rolled greenhouse modifier beyond 0.5 x sqrt(P) carries over."""
    surface_gh = 0.5 * math.sqrt(1.0) + 0.1
    at_zero = altitude_greenhouse_factor(surface_gh, 1.0, 0.0, 8.5)
    assert at_zero == pytest.approx(surface_gh, abs=1e-3)
    aloft = altitude_greenhouse_factor(surface_gh, 1.0, 8.5, 8.5)
    assert aloft == pytest.approx(0.5 * math.exp(-0.5) + 0.1, abs=1e-3)


# ------------------------------------- multiple stars and inherent heat

def test_temperature_addition_matches_book_table():
    """The Zed Prime low column: 243.30, 234.47, 63.71 and 12.36 add to
    284.41 (WBH p.124)."""
    assert add_temperatures(243.30, 234.47, 63.71, 12.36) == pytest.approx(
        284.41, abs=0.05)
    assert add_temperatures(255.17, 250.02, 71.61, 15.00) == pytest.approx(
        300.68, abs=0.05)
    # Adding a negligible source changes nothing measurable
    assert add_temperatures(288.0, 3.0) == pytest.approx(288.0, abs=0.01)


def test_star_contributions_totals(systems):
    """Every star contributes; the total can never be below the largest
    single contribution and the columns must order low <= mean <= high."""
    checked = 0
    for s in systems:
        if len([st for st in s.stars if not st.is_composite]) < 2:
            continue
        for w in s.all_worlds:
            if w.body_type != "Terrestrial" or not w.orbit_au:
                continue
            table = star_temperature_contributions(w, s)
            if not table['stars']:
                continue
            checked += 1
            assert table['low'] <= table['mean'] <= table['high'] + 0.01
            best = max(r['mean'] for r in table['stars'])
            assert table['mean'] >= best - 0.01
            break
    assert checked > 5


def test_gas_giant_residual_heat_matches_zed_prime():
    """1,200 Earth masses at 6.336 Gyr comes to 187K (WBH p.125)."""
    assert gas_giant_inherent_temperature(1200, 6.336) == pytest.approx(187, abs=1)
    # Young and massive runs hotter; old and small runs colder
    assert gas_giant_inherent_temperature(1200, 0.5) > 187
    assert gas_giant_inherent_temperature(100, 6.336) < 187
    assert gas_giant_inherent_temperature(0, 5.0) == 0.0
