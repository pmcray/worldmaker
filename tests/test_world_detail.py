"""Tests for belt internals, native lifeforms, population detail and the
technology profile (WBH pp.72-75, 127-131, 148-156, 173-180)."""
import random

import pytest

import worldmaker as wm
from worldmaker.belts import (
    calculate_belt_bulk,
    calculate_belt_composition,
    calculate_belt_resource_rating,
)
from worldmaker.classes import PlanetaryBody, UWP
from worldmaker.population import PCR_DESCRIPTIONS, minimum_sustainable_tl
from worldmaker.technology import generate_technology_profile, tlm
from worldmaker.utils import Utils

N = 250


@pytest.fixture(scope="module")
def systems():
    random.seed(808)
    return [wm.generate_full_system(f"W{i}") for i in range(N)]


@pytest.fixture(scope="module")
def mainworlds(systems):
    return [s.mainworld for s in systems if s.mainworld is not None]


# ----------------------------------------------------------------- belts

def test_belts_have_full_profile(systems):
    """WBH pp.72-75: span, composition percentages, bulk, resource rating and
    significant body counts."""
    belts = [w for s in systems for w in s.all_worlds
             if w.body_type == "Planetoid Belt"]
    assert belts, "no belts in sample"
    for b in belts:
        assert b.belt_span > 0
        assert b.belt_bulk >= 1
        assert b.resource_rating >= 1
        assert b.belt_profile
        comp = b.belt_composition
        assert set(comp) == {"m_type", "s_type", "c_type", "other"}
        assert sum(comp.values()) == 100, comp
        assert all(v >= 0 for v in comp.values())
        assert b.size_1_bodies >= 0 and b.size_s_bodies >= 0


def test_belt_composition_never_exceeds_100():
    """Excess over 100% is removed from m-type first, then s-type."""
    random.seed(4)
    body = PlanetaryBody(body_type="Planetoid Belt", orbit_num=3.0)
    for _ in range(300):
        comp = calculate_belt_composition(body, hzco=3.0)
        assert sum(comp.values()) == 100
        assert comp["m_type"] >= 0 and comp["s_type"] >= 0


def test_inner_belts_are_metal_rich_outer_belts_icy():
    """Belt Orbit# inside the HZCO is DM-4, beyond HZCO+2 is DM+4, which
    shifts composition from metallic toward carbonaceous."""
    random.seed(5)
    inner = PlanetaryBody(body_type="Planetoid Belt", orbit_num=1.0)
    outer = PlanetaryBody(body_type="Planetoid Belt", orbit_num=10.0)
    inner_m = [calculate_belt_composition(inner, 5.0)["m_type"] for _ in range(300)]
    outer_c = [calculate_belt_composition(outer, 5.0)["c_type"] for _ in range(300)]
    inner_c = [calculate_belt_composition(inner, 5.0)["c_type"] for _ in range(300)]
    assert sum(inner_m) / 300 > 20, "inner belts should be metal-rich"
    assert sum(outer_c) / 300 > sum(inner_c) / 300, (
        "outer belts should be icier than inner ones")


def test_belt_bulk_falls_with_system_age():
    """Belt Bulk takes DM -Age/2: older systems have thinner belts."""
    random.seed(6)
    comp = {"m_type": 40, "s_type": 40, "c_type": 10, "other": 10}
    young = [calculate_belt_bulk(comp, 1.0) for _ in range(200)]
    old = [calculate_belt_bulk(comp, 12.0) for _ in range(200)]
    assert sum(young) / 200 > sum(old) / 200
    assert min(young + old) >= 1, "bulk has a floor of 1"


def test_belt_resource_rating_follows_metal_content():
    random.seed(7)
    metal = {"m_type": 80, "s_type": 15, "c_type": 0, "other": 5}
    icy = {"m_type": 0, "s_type": 20, "c_type": 80, "other": 0}
    metal_ratings = [calculate_belt_resource_rating(metal, 4) for _ in range(200)]
    icy_ratings = [calculate_belt_resource_rating(icy, 4) for _ in range(200)]
    assert sum(metal_ratings) / 200 > sum(icy_ratings) / 200
    assert min(metal_ratings + icy_ratings) >= 1


# ------------------------------------------------------ native lifeforms

def test_lifeform_profile_recorded(systems):
    """WBH pp.127-131: the MXDC profile - biomass, biocomplexity,
    biodiversity, compatibility."""
    living = [w for s in systems for w in s.all_worlds
              if w.body_type == "Terrestrial" and w.biomass_rating > 0]
    assert living, "no worlds with life in sample"
    for w in living:
        assert len(w.native_lifeform_profile) == 4
        assert w.biodiversity_rating >= 1, "living worlds have biodiversity 1+"
        assert w.compatibility_rating >= 0
        # Biocomplexity derives from biomass, so it cannot run far ahead
        assert w.biocomplexity_rating <= min(9, w.biomass_rating) + 5


def test_airless_worlds_have_no_life(systems):
    """Atmosphere 0 or 1 carries DM-12 to biomass, which 2D cannot overcome."""
    for s in systems:
        for w in s.all_worlds:
            if w.body_type != "Terrestrial":
                continue
            if Utils.from_eHex(w.atmosphere_code) in (0, 1):
                assert w.biomass_rating == 0, (
                    f"atmosphere {w.atmosphere_code} world has biomass "
                    f"{w.biomass_rating}")


def test_sophont_checks_require_biocomplexity_8(systems):
    """Only worlds of biocomplexity 8+ may have native or extinct sophonts."""
    found = 0
    for s in systems:
        for w in s.all_worlds:
            if getattr(w, "native_sophont", False) or getattr(
                    w, "extinct_sophont", False):
                found += 1
                assert w.biocomplexity_rating >= 8, (
                    f"sophont on biocomplexity {w.biocomplexity_rating} world")
    assert found > 0, "no sophont checks ever succeeded"


def test_breathable_atmospheres_favour_life(systems):
    """Atmosphere 6 and 8 carry DM+2 to biomass."""
    good = [w.biomass_rating for s in systems for w in s.all_worlds
            if w.body_type == "Terrestrial"
            and Utils.from_eHex(w.atmosphere_code) in (6, 8)]
    poor = [w.biomass_rating for s in systems for w in s.all_worlds
            if w.body_type == "Terrestrial"
            and Utils.from_eHex(w.atmosphere_code) in (2, 3)]
    assert good and poor
    assert sum(good) / len(good) > sum(poor) / len(poor)


# --------------------------------------------------------- population

def test_population_profile_recorded(mainworlds):
    for mw in mainworlds:
        assert mw.population_profile
        pop = Utils.from_eHex(mw.uwp.population)
        assert 0 <= mw.pcr <= 9
        assert 0 <= mw.urbanisation_pct <= 100
        if pop == 0:
            assert mw.total_population == 0
            assert mw.major_cities == []
        else:
            assert mw.pcr_description in PCR_DESCRIPTIONS.values()
            assert mw.total_population >= 10 ** pop
            assert mw.urban_population <= mw.total_population


def test_high_population_worlds_have_a_minimum_urbanisation(mainworlds):
    """Population 9 sets a minimum of 18% + 1D, Population A+ 50% + 1D."""
    for mw in mainworlds:
        pop = Utils.from_eHex(mw.uwp.population)
        if pop >= 10:
            assert mw.urbanisation_pct >= 51, mw.urbanisation_pct
        elif pop == 9:
            assert mw.urbanisation_pct >= 19, mw.urbanisation_pct


def test_low_tech_worlds_are_capped(mainworlds):
    """TL0-2 caps urbanisation at 20% + 1D, TL3 at 30% + 1D."""
    for mw in mainworlds:
        tl = Utils.from_eHex(mw.uwp.tech_level)
        pop = Utils.from_eHex(mw.uwp.population)
        # A high-population minimum supersedes the maximum (WBH p.151)
        if pop >= 9:
            continue
        if tl <= 2:
            assert mw.urbanisation_pct <= 26, (tl, mw.urbanisation_pct)
        elif tl == 3:
            assert mw.urbanisation_pct <= 36, (tl, mw.urbanisation_pct)


def test_city_populations_sum_within_urban_population(mainworlds):
    for mw in mainworlds:
        if not mw.major_cities:
            continue
        total = sum(c["population"] for c in mw.major_cities)
        assert total <= mw.urban_population + 1, (
            f"cities hold {total} of {mw.urban_population} urban population")
        assert all(c["population"] > 0 for c in mw.major_cities)
        assert len({c["name"] for c in mw.major_cities}) == len(mw.major_cities)
        assert sum(1 for c in mw.major_cities if c.get("is_capital")) == 1


def test_single_settlement_worlds_have_one_city(mainworlds):
    """A small population gathered into one settlement area (PCR 9) has a
    single city - where it has any urban population at all."""
    checked = 0
    for mw in mainworlds:
        pop = Utils.from_eHex(mw.uwp.population)
        if mw.pcr == 9 and 0 < pop < 6 and mw.urban_population > 0:
            checked += 1
            assert len(mw.major_cities) == 1, (
                f"PCR 9 world has {len(mw.major_cities)} cities")
        elif mw.pcr == 9 and mw.urban_population == 0:
            # No urban population, no cities to name
            assert mw.major_cities == []
    assert checked > 0, "no single-settlement worlds in sample"


def test_minimum_sustainable_tl_table():
    """Tech Level and Environment table (WBH p.175)."""
    def world(atm, hab=10):
        w = PlanetaryBody(atmosphere_code=atm)
        w.habitability_rating = hab
        w.uwp = UWP(atmosphere=atm)
        return w

    assert minimum_sustainable_tl(world("0")) == 8
    assert minimum_sustainable_tl(world("A")) == 8
    assert minimum_sustainable_tl(world("3")) == 5
    assert minimum_sustainable_tl(world("B")) == 9
    assert minimum_sustainable_tl(world("C")) == 10
    # The highest applicable minimum wins
    assert minimum_sustainable_tl(world("6", hab=0)) == 8
    assert minimum_sustainable_tl(world("6", hab=10)) == 0


# --------------------------------------------------------- technology

def test_tlm_table_range():
    random.seed(8)
    values = {tlm() for _ in range(500)}
    assert values <= {-3, -2, -1, 0, 1, 2, 3}
    assert -3 in values and 3 in values


def test_technology_profile_structure(mainworlds):
    """H-L-QQQQQ-TTTT-MM-N (WBH p.180)."""
    for mw in mainworlds:
        parts = mw.technology_profile.split("-")
        assert len(parts) == 6, mw.technology_profile
        assert len(parts[0]) == 1               # high common TL
        assert len(parts[1]) == 1               # low common TL
        assert len(parts[2]) == 5               # quality of life QQQQQ
        assert len(parts[3]) == 4               # transport TTTT
        assert len(parts[4]) == 2               # military MM
        assert len(parts[5]) == 1               # novelty N
        assert Utils.from_eHex(parts[0]) == Utils.from_eHex(mw.uwp.tech_level)


def test_low_common_tl_never_exceeds_high(mainworlds):
    for mw in mainworlds:
        assert mw.tech_low <= mw.tech_high


def test_technology_subcategory_bounds(mainworlds):
    """Each subcategory is held inside its bounds (WBH p.177)."""
    for mw in mainworlds:
        if Utils.from_eHex(mw.uwp.population) == 0:
            continue
        assert mw.tech_energy <= mw.tech_high * 1.2 + 0.01
        assert mw.tech_electronics <= mw.tech_energy + 1
        assert mw.tech_manufacturing <= max(mw.tech_energy, mw.tech_electronics)
        assert mw.tech_medical <= mw.tech_electronics
        assert mw.tech_heavy <= mw.tech_manufacturing
        assert mw.tech_novelty >= mw.tech_high
        assert all(v >= 0 for v in (
            mw.tech_energy, mw.tech_electronics, mw.tech_manufacturing,
            mw.tech_medical, mw.tech_environmental, mw.tech_land,
            mw.tech_sea, mw.tech_air, mw.tech_space, mw.tech_personal,
            mw.tech_heavy, mw.tech_novelty))


def test_waterless_worlds_have_no_sea_transport(mainworlds):
    for mw in mainworlds:
        if Utils.from_eHex(mw.uwp.hydrographics) == 0:
            assert mw.tech_sea == 0, "sea transport on a world with no seas"


def test_uninhabited_worlds_have_no_technology():
    w = PlanetaryBody(uwp=UWP(starport="X", population="0", tech_level="0"))
    generate_technology_profile(w)
    assert w.tech_low == 0
    assert w.technology_profile.endswith("-00000-0000-00-0")
