"""Tests for notability scanning and the minimal sustainable Tech Level."""
import random

import pytest

import worldmaker as wm
from worldmaker.classes import PlanetaryBody, Star, StellarSystem, UWP
from worldmaker.notable import (
    EXOTIC_STARS,
    GIANT_CLASSES,
    Notable,
    describe_notable,
    find_exotic_systems,
    find_notable,
    notability,
)
from worldmaker.population import (
    enforce_sustainable_tech_level,
    minimum_sustainable_tl,
)
from worldmaker.utils import Utils


@pytest.fixture(scope="module")
def sector():
    random.seed(1105)
    return wm.generate_full_sector("Notable Reach", width=16, height=20)


def _system(spectral="G2 V", **world_kwargs):
    system = StellarSystem(name="S", age_gyr=4.5)
    system.stars.append(Star(designation="A", spectral_type=spectral,
                             mass=1.0, luminosity=1.0, hzco=3.0))
    world = PlanetaryBody(name="W", parent_star_group="A",
                          body_type="Terrestrial", is_mainworld=True,
                          uwp=UWP(starport='C', size='8', atmosphere='6',
                                  hydrographics='7', population='6',
                                  government='4', law_level='5',
                                  tech_level='9'),
                          **world_kwargs)
    system.stars[0].orbiting_bodies.append(world)
    return system, world


# ------------------------------------------------------------ the reasons

def test_a_dull_world_is_not_notable():
    system, world = _system()
    score, reasons = notability(world, system)
    assert score == 0 and reasons == []


def test_native_sophonts_are_the_strongest_signal():
    system, world = _system()
    world.native_sophont = True
    score, reasons = notability(world, system)
    assert score > 0
    assert reasons[0] == "a native sophont species"


def test_ruins_are_flagged():
    system, world = _system()
    world.extinct_sophont = True
    _, reasons = notability(world, system)
    assert any("extinct sophont" in r for r in reasons)


def test_exotic_stars_are_flagged_and_ranked():
    for spectral, (weight, text) in EXOTIC_STARS.items():
        system, world = _system(spectral=spectral)
        score, reasons = notability(world, system)
        assert any(text in r for r in reasons), spectral
    # A black hole outranks a brown dwarf
    hole, _ = _system(spectral='Black Hole')
    brown, _ = _system(spectral='BD')
    assert (notability(hole.all_worlds[0], hole)[0]
            > notability(brown.all_worlds[0], brown)[0])


def test_giant_classes_are_flagged():
    for lum_class in GIANT_CLASSES:
        system, world = _system(spectral=f"K2 {lum_class}")
        _, reasons = notability(world, system)
        assert reasons, lum_class


def test_repeated_reasons_are_not_double_counted():
    """Two subgiants in one system are one reason, not two."""
    system, world = _system(spectral="K2 IV")
    system.stars.append(Star(designation="B", spectral_type="M0 IV",
                             mass=0.5, luminosity=0.1))
    _, reasons = notability(world, system)
    assert reasons.count("a subgiant primary") == 1


def test_physical_extremes_are_flagged():
    system, world = _system()
    world.notes.append("Magma ocean (surface above 1,500K)")
    world.total_seismic_stress = 150
    world.atmosphere_code = 'C'
    _, reasons = notability(world, system)
    joined = " ".join(reasons)
    assert "magma" in joined
    assert "volcanism" in joined
    assert "insidious" in joined


def test_habitable_but_unsettled_is_interesting():
    system, world = _system()
    world.habitability_rating = 11
    world.uwp.population = '0'
    _, reasons = notability(world, system)
    assert any("unsettled" in r for r in reasons)


def test_travel_zones_are_flagged():
    system, world = _system()
    system.travel_zone = 'R'
    _, reasons = notability(world, system)
    assert any("Red Zone" in r for r in reasons)


def test_a_moon_mainworld_is_flagged():
    system, world = _system()
    world.parent_body = object()
    _, reasons = notability(world, system)
    assert any("moon serving as" in r for r in reasons)


def test_sophont_homeworlds_are_flagged_from_the_sector():
    system, world = _system()
    sector = wm.Sector()
    sector.systems["0101"] = system
    sector.native_sophonts["0101"] = wm.Sophont(name="Droyne")
    _, reasons = notability(world, system, sector, "0101")
    assert any("Droyne" in r for r in reasons)


# ---------------------------------------------------------------- scanning

def test_scan_returns_ranked_results(sector):
    found = find_notable(sector, limit=15)
    assert found
    scores = [n.score for n in found]
    assert scores == sorted(scores, reverse=True)
    for entry in found:
        assert entry.reasons, entry.hex


def test_scan_can_filter_by_kind(sector):
    mainworlds = find_notable(sector, limit=0, kind='mainworld')
    secondaries = find_notable(sector, limit=0, kind='secondary')
    assert mainworlds and secondaries
    assert all(n.kind == 'mainworld' for n in mainworlds)
    assert all(n.kind == 'secondary' for n in secondaries)


def test_scan_skips_gas_giants_and_rings(sector):
    for entry in find_notable(sector, limit=0):
        assert getattr(entry.body, 'body_type', '') != 'Gas Giant'
        assert not getattr(entry.body, 'is_ring', False)


def test_scan_only_covers_inhabited_or_main_worlds(sector):
    for entry in find_notable(sector, limit=0):
        assert (getattr(entry.body, 'is_mainworld', False)
                or getattr(entry.body, 'is_secondary_world', False))


def test_exotic_system_scan(sector):
    found = find_exotic_systems(sector, limit=10)
    for entry in found:
        assert entry.kind == 'system'
        assert entry.reasons


def test_describe_reads_usefully(sector):
    text = describe_notable(find_notable(sector, limit=5), "Top worlds")
    assert "Top worlds" in text
    assert describe_notable([], "Nothing").endswith("nothing stood out.")


# ------------------------------------- minimal sustainable Tech Level

def test_the_environment_table_matches_the_book():
    """WBH p.174: Atmosphere 0, 1 or A needs TL8; B needs 9; C needs 10;
    G or H need 14; habitability 0 needs 8."""
    def world_with(atmosphere, habitability=10):
        return PlanetaryBody(atmosphere_code=atmosphere,
                             habitability_rating=habitability,
                             uwp=UWP(atmosphere=atmosphere))

    assert minimum_sustainable_tl(world_with('0')) == 8
    assert minimum_sustainable_tl(world_with('A')) == 8
    assert minimum_sustainable_tl(world_with('2')) == 5
    assert minimum_sustainable_tl(world_with('4')) == 3
    assert minimum_sustainable_tl(world_with('B')) == 9
    assert minimum_sustainable_tl(world_with('C')) == 10
    assert minimum_sustainable_tl(world_with('G')) == 14
    assert minimum_sustainable_tl(world_with('6', habitability=0)) == 8
    # "If multiple factors apply to a world, the highest minimum applies"
    assert minimum_sustainable_tl(world_with('C', habitability=0)) == 10


def test_a_world_is_raised_to_its_habitation_floor():
    world = PlanetaryBody(atmosphere_code='C', habitability_rating=5,
                          uwp=UWP(atmosphere='C', population='6',
                                  tech_level='4'))
    random.seed(1)          # avoid the precarious branch
    changed = enforce_sustainable_tech_level(world)
    assert changed
    assert Utils.from_eHex(world.uwp.tech_level) == 10
    assert any("minimum its environment" in n for n in world.notes)


def test_an_unpopulated_world_is_left_alone():
    world = PlanetaryBody(atmosphere_code='C', habitability_rating=5,
                          uwp=UWP(atmosphere='C', population='0',
                                  tech_level='2'))
    assert not enforce_sustainable_tech_level(world)
    assert world.uwp.tech_level == '2'


def test_a_world_already_above_the_floor_is_untouched():
    world = PlanetaryBody(atmosphere_code='6', habitability_rating=9,
                          uwp=UWP(atmosphere='6', population='6',
                                  tech_level='9'))
    assert not enforce_sustainable_tech_level(world)
    assert world.uwp.tech_level == '9'


def test_some_worlds_hang_on_below_the_limit():
    """The book allows survival "one or two Tech Levels lower... prone to
    the dangers of life support failures"."""
    random.seed(7)
    precarious = 0
    for _ in range(200):
        world = PlanetaryBody(atmosphere_code='2', habitability_rating=6,
                              uwp=UWP(atmosphere='2', population='5',
                                      tech_level='4'))   # floor 5, one below
        enforce_sustainable_tech_level(world)
        if any("Precarious" in n for n in world.notes):
            precarious += 1
    assert 0 < precarious < 200, "the allowance should be occasional"


def test_a_gap_beyond_two_levels_is_always_closed():
    random.seed(7)
    for _ in range(50):
        world = PlanetaryBody(atmosphere_code='G', habitability_rating=5,
                              uwp=UWP(atmosphere='G', population='5',
                                      tech_level='2'))   # floor 14
        enforce_sustainable_tech_level(world)
        assert Utils.from_eHex(world.uwp.tech_level) == 14


def test_a_setting_ceiling_below_the_floor_empties_the_world():
    """Where surviving costs more technology than the setting has, nobody
    lives there."""
    world = PlanetaryBody(atmosphere_code='G', habitability_rating=5,
                          uwp=UWP(atmosphere='G', population='6',
                                  tech_level='7'))
    assert enforce_sustainable_tech_level(world, max_tech_level=9)
    assert world.uwp.population == '0'
    assert world.total_population == 0
    assert any("Uninhabited" in n for n in world.notes)


def test_generated_worlds_respect_their_habitation_floor(sector):
    """Across a sector, only the book's occasional precarious cases sit
    below the limit."""
    below = precarious = populated = 0
    for system in sector.systems.values():
        world = system.mainworld
        if world is None or Utils.from_eHex(world.uwp.population) == 0:
            continue
        populated += 1
        if Utils.from_eHex(world.uwp.tech_level) < minimum_sustainable_tl(world):
            below += 1
            if any("Precarious" in n for n in world.notes):
                precarious += 1
    assert populated > 50
    assert below / populated < 0.10, f"{below}/{populated} below the floor"
    assert below == precarious, "every shortfall should be a flagged case"
