"""Conformance tests against the actual rules in the Mongoose 2e
World Builder's Handbook (WBH) and Sector Construction Guide (SCG).

Each failing test here documents a divergence from, or omission of,
a book procedure. Page references are to the book PDFs in documents/.
"""
import random
from collections import Counter

import pytest

import worldmaker as wm
from worldmaker import society, stellar
from worldmaker.classes import PlanetaryBody, UWP
from worldmaker.sector import calculate_population_dm, Sector
from worldmaker.utils import Utils

N = 400


@pytest.fixture(scope="module")
def systems():
    random.seed(2022)
    return [wm.generate_full_system(f"S{i}") for i in range(N)]


# ---------------------------------------------------------------- stars

def test_primary_star_class_diversity(systems):
    """WBH p.15: a 2D roll of 2 is 'Special' -> Class III/IV/VI giants,
    subgiants, subdwarfs; 'Peculiar' results give white dwarfs, brown
    dwarfs, neutron stars, black holes, protostars, nebulae. Over 400
    systems ~2.8% should be non-Class-V primaries (~11 systems).
    The code hardcodes 'Special' to a G V star."""
    classes = Counter(
        s.primary_star.spectral_type.split(" ")[-1] for s in systems
    )
    non_v = sum(v for k, v in classes.items() if k != "V")
    assert non_v > 0, (
        f"all {N} primaries are luminosity class V: {dict(classes)}; "
        "WBH Special/Unusual star results (Class Ia-IV, VI, D, BD, "
        "neutron stars, black holes) are not implemented"
    )


def test_secondary_star_period_computed(systems):
    """WBH p.30: binary period P = sqrt(AU^3 / (M1+M2)). Star dataclass has
    period_years but it is never computed for secondaries."""
    secondaries = [
        st for s in systems for st in s.stars
        if st.orbit_class in ("Close", "Near", "Far", "Companion")
    ]
    assert secondaries, "no secondaries in sample"
    assert any(st.period_years > 0 for st in secondaries), (
        "no secondary star has an orbital period; WBH p.30 not implemented"
    )


# ------------------------------------------------------- world physical

def test_planetoid_belt_profile(systems):
    """WBH pp.72-75: belts get span, composition percentages (c/m/s-type),
    bulk, resource rating and a belt profile. Code sets size_code='0' only."""
    belts = [
        w for s in systems for w in s.all_worlds
        if w.body_type == "Planetoid Belt"
    ]
    assert belts, "no belts in sample"
    detailed = [b for b in belts if b.resource_rating > 0 or b.notes]
    assert detailed, (
        f"none of {len(belts)} planetoid belts has any WBH belt "
        "characteristics (span/composition/bulk/resource rating)"
    )


def test_atmosphere_pressure_and_composition(systems):
    """WBH pp.78-98: every world with Atmosphere 1+ gets pressure in bar,
    oxygen fraction, scale height; tainted/exotic/corrosive subtypes.
    No field for any of this exists on PlanetaryBody."""
    for attr in ("atmos_pressure_bar", "oxygen_fraction", "scale_height_km",
                 "atmosphere_taint", "atmosphere_composition"):
        assert not hasattr(PlanetaryBody(), attr), "field exists - update test"
    pytest.fail(
        "WBH expanded atmosphere system (pressure, ppO2, scale height, "
        "taints, exotic/corrosive/insidious types, non-HZ atmospheres, "
        "pp.78-98) is entirely unimplemented"
    )


def test_habitability_rating(systems):
    """WBH p.132: Habitability Rating = 10 + DMs decides the mainworld
    (p.133 Final Mainworld Determination). Code picks the first
    terrestrial world regardless of habitability."""
    assert not hasattr(PlanetaryBody(), "habitability_rating")
    # Demonstrate the consequence: mainworlds are chosen ignoring
    # habitability - count mainworlds that are the innermost terrestrial.
    first_count = 0
    mw_count = 0
    for s in systems:
        terr = [w for w in s.all_worlds if w.body_type == "Terrestrial"]
        mws = [w for w in terr if w.is_mainworld]
        if not mws:
            continue
        mw_count += 1
        if mws[0] is terr[0]:
            first_count += 1
    assert first_count < mw_count, (
        f"mainworld is always the innermost terrestrial world "
        f"({first_count}/{mw_count}); WBH habitability-based mainworld "
        "selection (pp.132-133) is not implemented"
    )


def test_mainworld_uwp_matches_physical_world(systems):
    """The mainworld's UWP should describe the world that was physically
    generated. The code re-rolls Size/Atm/Hyd from scratch in
    generate_mainworld_uwp() and overwrites the world's physical size,
    so density/gravity/temperature computed earlier belong to a
    different world."""
    mismatches = 0
    checked = 0
    for s in systems:
        for w in s.all_worlds:
            if w.is_mainworld and w.diameter_km:
                checked += 1
                implied = Utils.from_eHex(w.uwp.size) * 1600
                if abs(implied - w.diameter_km) > 1600:
                    mismatches += 1
    assert mismatches == 0, (
        f"{mismatches}/{checked} mainworlds have a UWP Size inconsistent "
        "with their generated diameter (UWP is re-rolled, not derived)"
    )


# --------------------------------------------------------- world social

def test_cultural_traits_use_2d(systems):
    """WBH p.182+: every cultural trait is 2D + DMs (values 2-12+ before
    DMs). Code rolls 1D per trait, so values 7+ can never occur."""
    traits = []
    for s in systems:
        for w in s.all_worlds:
            if w.is_mainworld and Utils.from_eHex(w.uwp.population) > 0:
                cp = w.cultural_profile
                traits += [cp.diversity, cp.xenophilia, cp.uniqueness,
                           cp.symbology, cp.cohesion, cp.progressiveness,
                           cp.expansionism, cp.militancy]
    assert traits
    assert max(traits) > 6, (
        f"max cultural trait over {len(traits)} samples is {max(traits)}; "
        "WBH rolls 2D+DMs (7+ common), code rolls 1D"
    )


def test_tech_level_government_dms():
    """Mongoose core TL table (used by WBH): Government 0 or 5 DM+1,
    Government 7 DM+2, Government 13/14 DM-2. generate_tech_level() does
    not even take government as a parameter."""
    import inspect

    params = inspect.signature(society.generate_tech_level).parameters
    assert "government" in params, (
        "generate_tech_level() ignores Government DMs "
        "(gov 0/5: +1, gov 7: +2, gov D/E: -2)"
    )


def test_economics_implemented():
    """WBH pp.185-199: Importance (Ix), Resources/Labour/Infrastructure/
    Efficiency (Ex), RU, GWP, WTN, inequality, development score, tariffs."""
    missing = [a for a in ("importance", "resources", "labour",
                           "infrastructure", "efficiency", "gwp",
                           "wtn", "resource_units")
               if not hasattr(PlanetaryBody(), a)]
    assert not missing, f"WBH economic extension not implemented: {missing}"


def test_law_and_government_detail():
    """WBH pp.156-172: government structure/factions with strength,
    justice system profile (PSU-I-D), Law Level subcodes (O-WECPR)."""
    for attr in ("government_structure", "law_profile", "justice_profile"):
        assert not hasattr(PlanetaryBody(), attr), "field exists - update test"
    pytest.fail(
        "WBH detailed government/law procedures (factions table, justice "
        "profile, law subcodes W/E/C/P/R) are unimplemented"
    )


def test_travel_zones():
    """SCG p.27 / WBH p.208: Amber/Red (or Zhodani Forbidden) travel zones.
    No zone field exists anywhere."""
    from worldmaker.classes import StellarSystem

    assert hasattr(StellarSystem(), "travel_zone"), (
        "travel zones (Amber/Red) are not represented at all"
    )


def test_population_wave_dm_capped():
    """SCG p.22: thin wave DM is -5 +1/century, i.e. the penalty decays to
    0 after 5 centuries; thick wave -3 +1/century, normal after 3
    centuries. The DM must never become positive. The hard-coded sector
    wave (age 10 centuries) gives every hex within range DM+7."""
    sec = Sector()
    from worldmaker.sector import define_settlement_waves

    define_settlement_waves(sec)
    dm = calculate_population_dm("0101", sec)
    assert dm <= 0, (
        f"population DM at wave origin is +{dm}; SCG wave DMs cap at 0, "
        "so populations are systematically inflated"
    )


# ----------------------------------------------------------- statistics

def test_mainworld_size_distribution():
    """Mainworld Size is 2D-2 (mean 5.0, WBH p.69/core rules)."""
    random.seed(9)
    sizes = [Utils.from_eHex(society.generate_mainworld_uwp().size)
             for _ in range(4000)]
    mean = sum(sizes) / len(sizes)
    assert 4.7 < mean < 5.3, f"mainworld size mean {mean:.2f}, expected 5.0"
    assert min(sizes) >= 0 and max(sizes) <= 10


def test_star_type_frequencies():
    """WBH p.15 Star Type table on 2D: M on 3-6 (13/36), K on 7-8 (11/36),
    G on 9-10 (7/36), F on 11 (2/36), Hot on 12 (1/36), Special on 2
    (1/36). Sample primary types and check M-dominance."""
    random.seed(11)
    types = Counter(
        stellar.generate_primary_star().spectral_type[0] for _ in range(6000)
    )
    frac_m = types["M"] / 6000
    assert 0.30 < frac_m < 0.42, f"M-dwarf fraction {frac_m:.3f}, expect ~0.36"
    frac_k = types["K"] / 6000
    assert 0.25 < frac_k < 0.36, f"K fraction {frac_k:.3f}, expect ~0.31"
