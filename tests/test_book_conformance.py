"""Conformance tests against the actual rules in the Mongoose 2e
World Builder's Handbook (WBH) and Sector Construction Guide (SCG).

Each failing test here documents a divergence from, or omission of,
a book procedure. Page references are to the book PDFs in documents/.
"""
import math
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
    """WBH pp.78-98: every world with an Atmosphere code gets a total pressure
    in bar drawn from that code's range, an oxygen fraction and partial
    pressure where free oxygen exists, a scale height, and a subtype for
    tainted/exotic/corrosive atmospheres."""
    from worldmaker.atmosphere import ATMOSPHERE_CODES, TAINTED_CODES

    checked = 0
    tainted_seen = 0
    for s in systems:
        for w in s.all_worlds:
            if w.body_type != "Terrestrial" or not w.atmosphere_code:
                continue
            atm = Utils.from_eHex(w.atmosphere_code)
            entry = ATMOSPHERE_CODES.get(atm)
            if not entry:
                continue
            checked += 1

            # Pressure must fall inside the code's tabulated range
            lo, hi = entry["min"], entry["min"] + entry["span"]
            assert lo - 1e-6 <= w.atmos_pressure_bar <= hi + 1e-6, (
                f"Atmosphere {w.atmosphere_code}: pressure "
                f"{w.atmos_pressure_bar} outside {lo}-{hi} bar"
            )
            assert w.atmosphere_name == entry["name"]
            assert w.atmosphere_composition, "no composition recorded"

            # Breathable-range atmospheres carry oxygen
            if atm in (2, 3, 4, 5, 6, 7, 8, 9, 13, 14):
                assert 0.05 <= w.oxygen_fraction <= 0.30, w.oxygen_fraction
                # Recorded to four decimal places, so compare absolutely
                assert w.partial_pressure_oxygen == pytest.approx(
                    w.oxygen_fraction * w.atmos_pressure_bar, abs=1e-4)

            # Scale height needs gravity and temperature, both computed
            if w.gravity > 0 and w.mean_temperature > 0:
                assert w.scale_height_km > 0

            if atm in TAINTED_CODES:
                tainted_seen += 1
                assert w.atmosphere_taint, "tainted atmosphere has no taint detail"
                assert set(w.atmosphere_taint) == {"type", "severity", "persistence"}

    assert checked > 100, f"only {checked} atmospheres examined"
    assert tainted_seen > 0, "no tainted atmospheres in sample"


def test_atmosphere_pressure_falls_with_altitude():
    """Pressure(a) = Pressure(mean) / e^(height / H) (WBH p.81)."""
    from worldmaker.atmosphere import pressure_at_altitude

    h = 8.5
    assert pressure_at_altitude(1.0, 0, h) == pytest.approx(1.0, rel=1e-6)
    assert pressure_at_altitude(1.0, h, h) == pytest.approx(1 / math.e, rel=1e-3)
    assert pressure_at_altitude(1.0, 2 * h, h) < pressure_at_altitude(1.0, h, h)


def test_habitability_rating(systems):
    """WBH p.132: Habitability Rating = 10 + DMs, clamped to 0-12."""
    rated = [w for s in systems for w in s.all_worlds
             if w.body_type == "Terrestrial"]
    assert rated
    for w in rated:
        assert 0 <= w.habitability_rating <= 12, w.habitability_rating

    # Airless rocks and frozen worlds must not score highly.
    for w in rated:
        atm = Utils.from_eHex(w.atmosphere_code)
        if atm in (0, 1) or (w.mean_temperature and w.mean_temperature < 233):
            assert w.habitability_rating <= 7, (
                f"hostile world (atm {w.atmosphere_code}, "
                f"{w.mean_temperature}K) rated {w.habitability_rating}"
            )

    ratings = {w.habitability_rating for w in rated}
    assert len(ratings) >= 4, f"habitability barely varies: {sorted(ratings)}"


def test_mainworld_is_chosen_by_habitability(systems):
    """WBH p.133: the mainworld is selected on habitability (resource rating
    breaking ties), not by orbital position."""
    mw_count = 0
    innermost_count = 0
    for s in systems:
        mw = s.mainworld
        if mw is None:
            continue
        candidates = [w for w in s.all_worlds if w.body_type == "Terrestrial"]
        if len(candidates) < 2:
            continue
        mw_count += 1

        # The chosen world must be at least as habitable as every planetary
        # candidate; a moon can win outright, hence the membership check.
        best = max(c.habitability_rating for c in candidates)
        assert mw.habitability_rating >= best or mw not in candidates, (
            f"{s.name}: chose habitability {mw.habitability_rating} "
            f"over an available {best}"
        )
        if mw is candidates[0]:
            innermost_count += 1

    assert mw_count > 20, "too few multi-candidate systems to judge"
    assert innermost_count < mw_count, (
        "mainworld is still always the innermost terrestrial world"
    )


def test_moons_can_be_mainworlds(systems):
    """A significant moon is a legitimate mainworld candidate (WBH p.59)."""
    moon_mainworlds = [s for s in systems
                       if s.mainworld is not None
                       and s.mainworld not in s.all_worlds]
    assert moon_mainworlds, "no moon was ever selected as a mainworld"
    for s in moon_mainworlds:
        assert s.mainworld.uwp.starport


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


def test_economics_implemented(systems):
    """WBH pp.185-199: Importance (Ix), the Resources/Labour/Infrastructure/
    Efficiency extension (Ex), resource units, GWP and the world trade
    number."""
    mains = [s.mainworld for s in systems if s.mainworld is not None]
    assert mains

    for mw in mains:
        # Importance runs roughly -3 to +5
        assert -4 <= mw.importance <= 6, mw.importance
        # Labour Factor = Population code - 1
        pop = Utils.from_eHex(mw.uwp.population)
        assert mw.labour == max(0, pop - 1)
        # Efficiency is bounded -5..+5 and never a bare 0
        assert -5 <= mw.efficiency <= 5 and mw.efficiency != 0
        # Resource factor has a floor of 2
        assert mw.resources >= 2
        assert mw.wtn >= 0
        assert 5 <= mw.inequality_rating <= 95
        assert mw.economic_extension.startswith("(")

        if pop == 0:
            assert mw.efficiency == -5
            assert mw.total_population == 0
        else:
            # Population code and significant digit give the headcount
            assert mw.total_population >= 10 ** pop
            assert mw.gwp == pytest.approx(
                mw.gwp_per_capita * mw.total_population, rel=1e-6)

    # The sample must show real variation, not a constant
    assert len({mw.importance for mw in mains}) >= 3
    assert len({mw.wtn for mw in mains}) >= 4
    assert any(mw.gwp > 0 for mw in mains), "no world has any economic output"


def test_wtn_responds_to_starport_and_population():
    """WTN = Base WTN (population + TL DMs) + starport modifier (WBH p.191)."""
    from worldmaker.economics import calculate_wtn

    def world(port, pop, tl):
        w = PlanetaryBody()
        w.uwp = UWP(starport=port, population=Utils.eHex(pop),
                    tech_level=Utils.eHex(tl))
        return w

    # A better starport never lowers the WTN
    for pop in range(0, 12):
        a = calculate_wtn(world("A", pop, 12))
        x = calculate_wtn(world("X", pop, 12))
        assert a >= x, f"pop {pop}: class A ({a}) below class X ({x})"

    # More population raises it
    assert calculate_wtn(world("C", 9, 10)) > calculate_wtn(world("C", 3, 10))


def test_law_and_government_detail(systems):
    """WBH pp.156-172: government centralisation/authority/structure, factions
    with strength and relationships, the justice profile (PSU-I-D) and the Law
    Level subcodes (O-WECPR)."""
    mains = [s.mainworld for s in systems if s.mainworld is not None]
    inhabited = [mw for mw in mains
                 if Utils.from_eHex(mw.uwp.population) > 0]
    assert inhabited

    for mw in inhabited:
        assert mw.government_type, "no government type named"
        assert mw.centralisation in ("Confederal", "Federal", "Unitary")
        assert mw.primary_authority in ("Legislative", "Executive",
                                        "Judicial", "Balanced")
        assert mw.government_structure

        # Justice profile: PSU-I-D
        assert mw.justice_primary in ("Inquisitional", "Adversarial",
                                      "Traditional")
        assert mw.law_uniformity in ("Personal", "Territorial", "Universal")
        assert len(mw.justice_profile.split("-")) == 3, mw.justice_profile

        # Law Level profile: O-WECPR, five subcodes around the overall level
        overall, subcodes = mw.law_profile.split("-")
        assert overall == mw.uwp.law_level
        assert len(subcodes) == 5, mw.law_profile
        law = Utils.from_eHex(mw.uwp.law_level)
        for code in subcodes:
            # 2D3-4 spans -2..+2 around the overall Law Level
            assert abs(Utils.from_eHex(code) - law) <= 2 or law < 2

        # Factions
        assert mw.factions, "inhabited world has no factions"
        for f in mw.factions:
            assert f["strength"] in ("Obscure", "Fringe", "Minor", "Notable",
                                     "Significant", "Dominant")
            assert f["government_type"]
        if len(mw.factions) > 1:
            # Relationships are recorded symmetrically between every pair
            for f in mw.factions:
                assert len(f["relations"]) == len(mw.factions) - 1
            a, b = mw.factions[0], mw.factions[1]
            assert a["relations"][b["id"]] == b["relations"][a["id"]]

    # Balkanised worlds should carry more factions than average
    balk = [mw for mw in inhabited if Utils.from_eHex(mw.uwp.government) == 7]
    if balk:
        avg_all = sum(len(mw.factions) for mw in inhabited) / len(inhabited)
        avg_balk = sum(len(mw.factions) for mw in balk) / len(balk)
        assert avg_balk > avg_all


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
