"""Tests for WBH precise hydrographics & exotic liquids (pp. 99-103),
rotation/solar day/extreme axial tilt/full tidal lock status (pp. 103-107),
and SCG historical border generation from sector timelines (pp. 20, 26, 42, 47)."""

import math
import random
import pytest

import worldmaker as wm
from worldmaker.classes import PlanetaryBody, Satellite, Star, StellarSystem, UWP


# ==============================================================================
# 1. PRECISE HYDROGRAPHICS, SURFACE DISTRIBUTION & EXOTIC LIQUIDS (WBH pp. 99-103)
# ==============================================================================

def test_precise_hydrographics_percentage_ranges():
    """WBH p. 99: Hydrographics 0 is 0-5%, 1-9 are (H*10-4)..(H*10+5)%,
    and A (10) is 96-100% (or always 100% when Size > 9)."""
    random.seed(101)
    for _ in range(100):
        pct0 = wm.roll_hydrographics_percentage("0", "6")
        assert 0.0 <= pct0 <= 5.0

    for h_code in range(1, 10):
        lo = h_code * 10 - 4
        hi = h_code * 10 + 5
        for _ in range(40):
            pct = wm.roll_hydrographics_percentage(wm.Utils.eHex(h_code), "6")
            assert lo <= pct <= hi

    for _ in range(50):
        pct_a = wm.roll_hydrographics_percentage("A", "8")
        assert 96.0 <= pct_a <= 100.0
        # Worlds above Size 9 with Hydrographics A are always 100% liquid
        assert wm.roll_hydrographics_percentage("A", "A") == 100.0
        assert wm.roll_hydrographics_percentage("A", "C") == 100.0


def test_surface_distribution_and_continents():
    """WBH pp. 100-102: 2D-2 Surface Distribution table (0-10) and dominant
    geography ('ocean' for 6+, 'land' for 4-, 50/50 on 5)."""
    random.seed(202)
    ocean_dom = wm.roll_surface_distribution("7", 71.0)
    assert 0 <= ocean_dom["code"] <= 10
    assert ocean_dom["description"]
    assert ocean_dom["dominant_geography"] == "ocean"

    land_dom = wm.roll_surface_distribution("2", 20.0)
    assert land_dom["dominant_geography"] == "land"

    dry = wm.roll_surface_distribution("0", 0.0)
    assert dry["major_continents"] == 0
    assert dry["minor_continents"] == 0


def test_exotic_liquids_by_temperature_and_atmosphere():
    """WBH pp. 102-103:
    - Breathable/standard worlds have Water (H2O)
    - Vacuum/Trace outer worlds have Water Ice
    - Worlds >= 1000K have Magma (SiO2)
    - Cold Exotic/Corrosive worlds (~95-110K) select cryogens (CH4, C2H6, O2, F2)
    - Hot Corrosive worlds (~500K) select high-boiling acids/solvents (H2SO4, H2CO3, CH3NO)
    - Profile follows H-D:%%:XX-## format."""
    random.seed(303)

    # Terra-like standard world
    terra = PlanetaryBody(
        size_code="8", atmosphere_code="6", hydrographics_code="7",
        mean_temperature=288.0, atmos_pressure_bar=1.0
    )
    wm.detail_hydrographics(terra)
    assert terra.hydrographics_liquid == "Water"
    assert terra.hydrographics_composition == {"H2O": 100}
    assert terra.hydrographics_profile.startswith("7-")
    assert terra.hydrographics_profile.endswith(":H2O")

    # Cryogenic Titan-like world (~95K, Exotic atmosphere with methane/nitrogen)
    titan = PlanetaryBody(
        size_code="5", atmosphere_code="A", hydrographics_code="2",
        mean_temperature=95.0, atmos_pressure_bar=1.5,
        atmosphere_composition="96% Nitrogen, 4% Methane"
    )
    wm.detail_hydrographics(titan)
    assert set(titan.hydrographics_composition.keys()) <= {"CH4", "C2H6", "O2", "F2"}
    assert sum(titan.hydrographics_composition.values()) == 100

    # Hot Corrosive Aab I-like world (~520K, Corrosive atmosphere)
    aab_i = PlanetaryBody(
        size_code="9", atmosphere_code="B", hydrographics_code="1",
        mean_temperature=520.0, atmos_pressure_bar=15.0,
        atmosphere_composition="48% Carbon Dioxide, 47% Ammonia"
    )
    wm.detail_hydrographics(aab_i)
    assert set(aab_i.hydrographics_composition.keys()) <= {"H2SO4", "H2CO3", "CH3NO"}
    assert sum(aab_i.hydrographics_composition.values()) == 100

    # Magma ocean world (>= 1000K)
    lava = PlanetaryBody(
        size_code="7", atmosphere_code="B", hydrographics_code="4",
        mean_temperature=1250.0, atmos_pressure_bar=5.0
    )
    wm.detail_hydrographics(lava)
    assert "Magma" in lava.hydrographics_liquid
    assert lava.hydrographics_composition == {"SiO2": 100}


# ==============================================================================
# 2. SOLAR DAY, DAYS IN YEAR, EXTREME TILT & FULL TIDAL LOCK (WBH pp. 103-107)
# ==============================================================================

def test_extreme_axial_tilt_subtable_and_bounds():
    """WBH p. 104: Extreme Axial Tilt sub-table produces tilts up to 180°
    (retrograde when > 90°) and never exceeds 180°."""
    random.seed(404)
    tilts = [wm.roll_axial_tilt() for _ in range(500)]
    values = [t[0] for t in tilts]
    remarks = {t[1] for t in tilts}
    assert all(0.0 <= v <= 180.0 for v in values)
    assert any(v > 35.0 for v in values), "Extreme Axial Tilt sub-table never reached"
    assert any(v > 90.0 for v in values), "Retrograde axial tilts (>90°) never rolled"
    assert len(remarks) >= 3


def test_solar_day_and_days_in_year_benchmarks():
    """WBH p. 104:
    - Terra: sidereal day ~23.9344h, year 1.0 (8766h) -> ~365.25 solar days, 24.0h solar day
    - Zed Prime (moon): sidereal day 42.37h, parent period 0.805y (7056.63h)
      -> 165.55 solar days in year, 42.63h solar day
    - Retrograde world (tilt > 90°): sidereal day treated as negative, so solar
      days in year = -(year_h / sidereal_h) - 1 (shorter solar day than sidereal)
    - 1:1 star-locked world: 0 solar days in year, solar_day_hours is None."""
    # Terra benchmark
    terra = PlanetaryBody(
        size_code="8", period_years=1.0, rotation_period_hours=23.93447,
        axial_tilt=23.44
    )
    wm.calculate_solar_day_and_year(terra)
    assert terra.solar_days_in_year == pytest.approx(365.25, abs=0.1)
    assert terra.solar_day_hours == pytest.approx(24.0, abs=0.02)

    # Zed Prime moon benchmark (WBH pp. 104-105)
    gg = PlanetaryBody(body_type="Gas Giant", period_years=0.805)
    zed_prime = Satellite(
        size_code="5", parent_body=gg, rotation_period_hours=42.37,
        axial_tilt=73.65
    )
    wm.calculate_solar_day_and_year(zed_prime)
    assert zed_prime.solar_days_in_year == pytest.approx(165.55, abs=0.05)
    assert zed_prime.solar_day_hours == pytest.approx(42.63, abs=0.05)

    # Retrograde rotation (tilt > 90°)
    retro = PlanetaryBody(
        size_code="6", period_years=1.0, rotation_period_hours=100.0,
        axial_tilt=120.0
    )
    wm.calculate_solar_day_and_year(retro)
    # 8766 / -100 - 1 = -88.66 -> 88.66 solar days, solar day ~98.87h (< 100h)
    assert retro.solar_days_in_year == pytest.approx(88.66, abs=0.05)
    assert retro.solar_day_hours < retro.rotation_period_hours

    # 1:1 star-locked twilight zone world
    locked = PlanetaryBody(
        size_code="5", period_years=0.5, rotation_period_hours=0.5 * 8766.0,
        tidal_lock_status="1:1", is_twilight_zone_world=True
    )
    wm.calculate_solar_day_and_year(locked)
    assert locked.solar_days_in_year == 0.0
    assert locked.solar_day_hours is None


def test_zed_prime_tidal_lock_dm_benchmark():
    """WBH p. 107 worked example:
    Zed Prime is a Size 5 moon in retrograde orbit at 22 PD with eccentricity
    0.25 and axial tilt 73.65° around a 1,200-Earth-mass gas giant in a 6.3 Gyr
    system.
    Common DMs: +2 (Size 5), -2 (ecc 0.25), -2 (tilt > 30°), -4 (tilt 60-120°),
                +2 (age 5-10 Gyr) = -4.
    Moon-to-planet DMs: +6 (Base), -1 (22 PD), -2 (retrograde), +8 (Mp > 1000) = +11.
    Total DM = +7."""
    system = StellarSystem(age_gyr=6.3)
    gg = PlanetaryBody(body_type="Gas Giant", mass_terran=1200.0, period_years=0.805)
    zed_prime = Satellite(
        size_code="5", parent_body=gg, orbit_pd=22.0, eccentricity=0.25,
        retrograde=True, axial_tilt=73.65, atmos_pressure_bar=1.0
    )
    dm = wm.calculate_tidal_lock_dm(zed_prime, system, case="planet")
    assert dm == 7


def test_tidal_lock_table_3_2_and_1_1_effects():
    """WBH p. 105: Roll 11 produces a 3:2 resonance (sidereal day = 2/3 of
    orbital period) and damps axial tilt > 3°; Roll 12+ produces a 1:1 lock."""
    random.seed(505)
    w_32 = PlanetaryBody(
        size_code="4", period_years=0.24, rotation_period_hours=30.0,
        axial_tilt=25.0, eccentricity=0.20
    )
    year_h = 0.24 * 8766.0
    status = wm.apply_tidal_lock_roll(
        w_32, 11, year_h, case="star", target_label="A", allow_break_reroll=False
    )
    assert status == "3:2"
    assert w_32.rotation_period_hours == pytest.approx(year_h * (2.0 / 3.0), abs=0.1)
    assert w_32.axial_tilt <= 1.0

    w_11 = PlanetaryBody(
        size_code="6", period_years=0.1, rotation_period_hours=24.0,
        axial_tilt=40.0, eccentricity=0.25
    )
    year_h_11 = 0.1 * 8766.0
    status_11 = wm.apply_tidal_lock_roll(
        w_11, 12, year_h_11, case="star", target_label="A", allow_break_reroll=False
    )
    assert status_11 == "1:1"
    assert w_11.is_twilight_zone_world is True
    assert w_11.rotation_period_hours == pytest.approx(year_h_11, abs=0.1)
    assert w_11.axial_tilt <= 1.0


# ==============================================================================
# 3. HISTORICAL BORDER GENERATION FROM SECTOR TIMELINES (SCG pp. 20, 26, 42, 47)
# ==============================================================================

def test_procedural_borders_driven_by_history_and_timeline():
    """SCG pp. 20, 26, 42: Procedural polities record founding, frontier wars,
    and border treaties in `sector.border_history`, `polity.history`, and
    `universe.timeline`, while keeping all polity territories contiguous."""
    random.seed(606)
    universe = wm.create_universe("Contested Reach", preset="pocket_empires")
    wm.build_default_timeline(universe)
    initial_events = len(universe.timeline)

    sector = wm.generate_universe_sector(universe, "Contested", width=16, height=20)
    assert sector.polities
    assert sector.border_history, "no border history events generated"
    assert any(ev["type"] == "founding" for ev in sector.border_history)
    # With 5 close polities in 'pocket_empires', frontier wars and treaties occur
    assert any(ev["type"] in ("frontier_war", "treaty") for ev in sector.border_history)
    assert len(universe.timeline) > initial_events

    for p in sector.polities:
        assert p.history, f"{p.name} has no historical border entries"


def test_decline_and_collapse_trajectories_contract_borders():
    """In 'collapse' or 'decline' universes, outer rim worlds can secede or
    lose contact during the border contraction phase."""
    random.seed(707)
    universe = wm.create_universe(
        "Fallen Reach", preset="fallen_empire", density="dense", polity_count=2
    )
    sector = wm.generate_universe_sector(universe, "Fallen", width=16, height=20)
    contractions = [ev for ev in sector.border_history if ev["type"] == "contraction"]
    assert contractions, "no border contraction occurred in a collapse universe"
    for ev in contractions:
        for h in ev["hexes_lost"]:
            assert sector.systems[h].allegiance == "Na"
            assert any("Seceded / lost contact" in n for n in sector.systems[h].historical_notes)


def test_foreven_timeline_drives_border_annotations():
    """SCG pp. 26, 47: Foreven's timeline events (First-Fourth Frontier Wars,
    Treaty of 620, Charter of 628, Pres Tinto/Pres Alfa fortifications, Zuekgoz
    occupation) populate `sector.border_history` and system historical notes."""
    sector = wm.generate_foreven_1105(seed=1105, preset="scg_worked_1105")
    assert len(sector.border_history) >= 10
    years = [ev["year"] for ev in sector.border_history]
    assert years == sorted(years)
    assert 604 in years  # First Frontier War (Massina conquest)
    assert 628 in years  # Charter of the Avalar Consulate
    assert 983 in years  # Third Frontier War fortifications
    assert 1045 in years  # Zuekgoz occupation
    assert 1084 in years  # Fourth Frontier War

    # Check specific border worlds carry their timeline notes
    assert any("First Frontier War" in n for n in sector.systems["2805"].historical_notes)
    assert any("985" in n for n in sector.systems["1637"].historical_notes)
    assert any("983" in n for n in sector.systems["1734"].historical_notes)
    assert any("1045" in n for n in sector.systems["1938"].historical_notes)
