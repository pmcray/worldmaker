"""Tests for the detailed temperature and seismology chain (WBH pp.107-128)."""
import math
import random

import pytest

import worldmaker as wm
from worldmaker.temperature import (
    _base_temperature,
    apply_seismic_temperature,
    axial_tilt_factor,
    body_tidal_effect,
    calculate_temperature_range,
    geographic_factor,
    roll_albedo,
    roll_greenhouse,
    rotation_factor,
    star_tidal_effect,
    tidal_heating_factor,
)
from worldmaker.classes import PlanetaryBody, StellarSystem, Star
from worldmaker.utils import Utils

N = 200


@pytest.fixture(scope="module")
def systems():
    random.seed(4242)
    return [wm.generate_full_system(f"T{i}") for i in range(N)]


# ------------------------------------------------------ benchmark: Terra

def test_base_temperature_reproduces_terra():
    """The book benchmarks its temperature model against Terra: 288K mean,
    and 255K equilibrium with no greenhouse effect."""
    equilibrium = _base_temperature(1.0, 0.3, 0.0, 1.0)
    assert equilibrium == pytest.approx(255, abs=1.5), equilibrium

    # Terra's greenhouse factor is 0.5 x sqrt(1.013 bar) + small modifiers
    greenhouse = 0.5 * math.sqrt(1.013) + 0.10
    mean = _base_temperature(1.0, 0.3, greenhouse, 1.0)
    assert mean == pytest.approx(288, abs=4), mean


def test_temperature_falls_with_distance():
    hot = _base_temperature(1.0, 0.3, 0.0, 0.7)
    warm = _base_temperature(1.0, 0.3, 0.0, 1.0)
    cold = _base_temperature(1.0, 0.3, 0.0, 5.2)
    assert hot > warm > cold
    # Inverse square root relationship: doubling distance drops T by sqrt(2)
    assert _base_temperature(1.0, 0.3, 0.0, 2.0) == pytest.approx(
        warm / math.sqrt(2), rel=1e-6)


# ------------------------------------------------------------ factors

def test_axial_tilt_factor_matches_table():
    """Basic Axial Tilt Factor table (WBH p.113) is sin(tilt)."""
    for tilt, expected in ((5, 0.09), (30, 0.50), (45, 0.71), (60, 0.87),
                           (85, 1.00), (90, 1.00)):
        assert axial_tilt_factor(tilt, 1.0) == pytest.approx(expected, abs=0.01)


def test_axial_tilt_factor_year_length_adjustments():
    """Short years halve the factor; long years increase it up to +0.25."""
    base = axial_tilt_factor(30, 1.0)
    assert axial_tilt_factor(30, 0.05) == pytest.approx(base / 2, abs=0.01)
    long_year = axial_tilt_factor(30, 10.0)
    assert base < long_year <= min(1.0, base + 0.25) + 1e-6


def test_rotation_factor_rules():
    """sqrt(solar day hours) / 50, capped at 1.0; locked worlds are 1.0."""
    assert rotation_factor(24) == pytest.approx(math.sqrt(24) / 50, abs=1e-3)
    assert rotation_factor(3000) == 1.0
    assert rotation_factor(24, tidally_locked=True) == 1.0
    assert rotation_factor(0) == 0.0


def test_geographic_factor_rules():
    """(10 - HYD) / 20, modified by surface distribution for HYD 2-8."""
    assert geographic_factor(0) == pytest.approx(0.5)
    assert geographic_factor(10) == pytest.approx(0.0)
    assert geographic_factor(5, surface_distribution=9) == pytest.approx(0.35)
    assert geographic_factor(5, surface_distribution=1) == pytest.approx(0.15)
    # Outside 2-8 the distribution modifier does not apply
    assert geographic_factor(10, surface_distribution=9) == pytest.approx(0.0)


# ------------------------------------------------------ albedo/greenhouse

def test_albedo_within_book_bounds(systems):
    """Albedo Range table (WBH p.110), clamped to 0.02-0.98."""
    worlds = [w for s in systems for w in s.all_worlds
              if w.body_type == "Terrestrial"]
    assert worlds
    for w in worlds:
        assert 0.02 <= w.albedo <= 0.98, w.albedo
    assert len({w.albedo for w in worlds}) > 20, "albedo barely varies"


def test_vacuum_worlds_have_no_greenhouse():
    w = PlanetaryBody(atmosphere_code="0", atmos_pressure_bar=0.0)
    assert roll_greenhouse(w) == 0.0


def test_greenhouse_scales_with_pressure():
    """Initial Greenhouse Factor = 0.5 x sqrt(pressure in bar)."""
    random.seed(11)
    thin = PlanetaryBody(atmosphere_code="5", atmos_pressure_bar=0.5)
    dense = PlanetaryBody(atmosphere_code="8", atmos_pressure_bar=2.0)
    thin_vals = [roll_greenhouse(thin) for _ in range(200)]
    dense_vals = [roll_greenhouse(dense) for _ in range(200)]
    assert sum(dense_vals) / 200 > sum(thin_vals) / 200


# ------------------------------------------------- high/low temperatures

def test_high_low_bracket_the_mean(systems):
    """The high and low global temperatures must bracket the mean."""
    checked = 0
    for s in systems:
        for w in s.all_worlds:
            if w.body_type != "Terrestrial" or not w.mean_temperature:
                continue
            checked += 1
            assert w.low_temperature <= w.mean_temperature + 0.05, (
                f"low {w.low_temperature} above mean {w.mean_temperature}")
            assert w.high_temperature >= w.mean_temperature - 0.05, (
                f"high {w.high_temperature} below mean {w.mean_temperature}")
    assert checked > 100


def test_luminosity_modifier_bounded(systems):
    """No temperature modification factor may exceed 1.0 (WBH p.113)."""
    for s in systems:
        for w in s.all_worlds:
            if w.body_type == "Terrestrial":
                assert 0.0 <= w.luminosity_modifier <= 1.0


def test_variance_factors_are_the_sum_of_three(systems):
    for s in systems:
        for w in s.all_worlds:
            if w.body_type != "Terrestrial" or not w.variance_factors:
                continue
            assert w.variance_factors == pytest.approx(
                w.axial_tilt_factor + w.rotation_factor + w.geographic_factor,
                abs=1e-3)


def test_thick_atmosphere_narrows_temperature_range():
    """Atmospheric Factor = 1 + pressure, which damps the luminosity
    modifier and so narrows the high-low spread."""
    system = StellarSystem(age_gyr=4.5)
    star = Star(designation="A", spectral_type="G2 V", mass=1.0,
                luminosity=1.0, hzco=3.0)
    system.stars.append(star)

    def spread_for(pressure):
        w = PlanetaryBody(parent_star_group="A", body_type="Terrestrial",
                          size_code="8", orbit_au=1.0, period_years=1.0,
                          axial_tilt=23.5, rotation_period_hours=24.0,
                          hydrographics_code="7", atmosphere_code="6")
        w.atmos_pressure_bar = pressure
        r = calculate_temperature_range(w, system, 1.0, 0.3, 0.5, 1.0)
        return r["high_temperature"] - r["low_temperature"]

    assert spread_for(5.0) < spread_for(0.5)


# ------------------------------------------------------------ seismology

def test_tidal_effects_fall_with_distance():
    near = star_tidal_effect(1.0, 8, 0.4)
    far = star_tidal_effect(1.0, 8, 5.0)
    assert near > far > 0
    # Inverse cube
    assert star_tidal_effect(1.0, 8, 2.0) == pytest.approx(
        star_tidal_effect(1.0, 8, 1.0) / 8, rel=1e-6)

    close_moon = body_tidal_effect(0.012, 8, 200000)
    distant_moon = body_tidal_effect(0.012, 8, 800000)
    assert close_moon > distant_moon > 0


def test_tidal_heating_needs_eccentricity():
    """Circular orbits produce no tidal heating."""
    assert tidal_heating_factor(1.0, 5, 0.0, 1.0, 1.0, 0.5) == 0.0
    assert tidal_heating_factor(1.0, 5, 0.2, 1.0, 1.0, 0.5) > 0


def test_seismic_temperature_addition():
    """New Temperature = (Old^4 + Stress^4)^(1/4) - negligible unless the
    stress is comparable to the temperature."""
    assert apply_seismic_temperature(288, 0) == pytest.approx(288, abs=0.1)
    assert apply_seismic_temperature(288, 3) == pytest.approx(288, abs=0.1)
    # A stress of the same order as the temperature raises it noticeably
    assert apply_seismic_temperature(100, 100) == pytest.approx(
        100 * 2 ** 0.25, abs=0.5)


def test_seismology_recorded(systems):
    worlds = [w for s in systems for w in s.all_worlds
              if w.body_type == "Terrestrial"]
    assert worlds
    for w in worlds:
        assert w.total_seismic_stress >= 0
        assert w.tectonic_plates >= 0
        assert w.seismic_activity
        assert w.total_seismic_stress == pytest.approx(
            w.residual_seismic_stress + w.tidal_stress_factor
            + w.tidal_heating_factor, abs=0.01)

    # Activity descriptions must track the stress value
    for w in worlds:
        if w.total_seismic_stress < 1:
            assert w.seismic_activity == "Geologically dead"
        elif w.total_seismic_stress > 100:
            assert "Constant" in w.seismic_activity


def test_habitability_uses_high_low_temperatures(systems):
    """With high/low temperatures computed, a world whose high exceeds 323K or
    whose low falls below 200K must be penalised."""
    penalised = [w for s in systems for w in s.all_worlds
                 if w.body_type == "Terrestrial"
                 and w.low_temperature and w.low_temperature < 200]
    assert penalised, "no cold-extreme worlds in sample"
    for w in penalised:
        assert w.habitability_rating <= 9
