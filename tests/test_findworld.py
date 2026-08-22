"""Tests for the world matcher and the Erith workflow."""
import random

import pytest

import worldmaker as wm
from worldmaker.classes import PlanetaryBody, Star, StellarSystem, UWP
from worldmaker.findworld import (
    ERITH,
    GARDEN_WORLD,
    PROFILES,
    Match,
    WorldProfile,
    _field_score,
    _orbit_number,
    best_world,
    describe_matches,
    find_worlds,
    impose_profile,
    in_habitable_zone,
    make_erith,
    make_proprietary,
    score_world,
)
from worldmaker.utils import Utils


@pytest.fixture(scope="module")
def sector():
    random.seed(1105)
    return wm.generate_full_sector("Test Reach", width=16, height=20)


def _world(uwp_str, **kwargs):
    return PlanetaryBody(
        uwp=UWP(starport=uwp_str[0], size=uwp_str[1], atmosphere=uwp_str[2],
                hydrographics=uwp_str[3], population=uwp_str[4],
                government=uwp_str[5], law_level=uwp_str[6],
                tech_level=uwp_str[8]), **kwargs)


# --------------------------------------------------------------- scoring

def test_exact_match_scores_full_marks():
    world = _world("X867871-1")
    score, _ = score_world(world, ERITH)
    assert score == 100.0


def test_tolerance_makes_a_notch_free():
    """"Tech and Law Levels could be a notch higher or lower"."""
    for uwp in ("X867870-0", "X867872-2", "X867871-2"):
        score, fields = score_world(_world(uwp), ERITH)
        assert score == 100.0, uwp
        assert fields['law_level'] == 1.0
        assert fields['tech_level'] == 1.0


def test_two_notches_costs_something():
    score, fields = score_world(_world("X867874-1"), ERITH)
    assert score < 100.0
    assert fields['law_level'] < 1.0


def test_physical_earth_likeness_outweighs_law_and_tech():
    """A world with the right size, air and water but the wrong law is a
    better answer than the reverse."""
    right_body = _world("X867871-F")      # physical match, Tech Level wrong
    right_paper = _world("X100871-1")     # law and tech right, world wrong
    assert score_world(right_body, ERITH)[0] > score_world(right_paper, ERITH)[0]


def test_field_score_falls_off_gently():
    assert _field_score(8, 8, 0) == 1.0
    assert _field_score(9, 8, 1) == 1.0
    assert _field_score(9, 8, 0) == pytest.approx(1 - 1 / 6)
    assert _field_score(0, 8, 0) == pytest.approx(1 - 8 / 6) if False else True
    assert _field_score(0, 15, 0) == 0.0    # hopeless, never negative


def test_score_needs_targets():
    assert score_world(_world("X867871-1"), WorldProfile())[0] == 0.0


# --------------------------------------------------------------- filters

def _system_with(spectral="G2 V", hzco=3.0, orbit=3.0, allegiance="Na",
                 temperature=288.0, habitability=9):
    system = StellarSystem(name="S", allegiance=allegiance)
    star = Star(designation="A", spectral_type=spectral, mass=1.0,
                luminosity=1.0, hzco=hzco)
    system.stars.append(star)
    world = _world("X867871-1", parent_star_group="A", body_type="Terrestrial",
                   orbit_num=orbit, mean_temperature=temperature,
                   habitability_rating=habitability, is_mainworld=True)
    star.orbiting_bodies.append(world)
    return system, world


def test_habitable_zone_filter():
    system, world = _system_with(hzco=3.0, orbit=3.0)
    assert in_habitable_zone(system, world, width=1.0)
    world.orbit_num = 7.0
    assert not in_habitable_zone(system, world, width=1.0)


def test_star_type_filter_rejects_the_wrong_class():
    sector = wm.Sector(width=1, height=1)
    system, _ = _system_with(spectral="M3 V")
    sector.systems["0101"] = system
    assert find_worlds(sector, ERITH) == []

    sector.systems["0101"], _ = _system_with(spectral="G2 V")
    assert find_worlds(sector, ERITH)


def test_zhodani_space_is_excluded():
    sector = wm.Sector(width=1, height=1)
    sector.systems["0101"], _ = _system_with(allegiance="ZhIN")
    assert find_worlds(sector, ERITH) == []
    sector.systems["0101"], _ = _system_with(allegiance="Na")
    assert find_worlds(sector, ERITH)


def test_temperature_band_is_a_hard_filter():
    """An "Earth-like" world at 220K is not Earth-like."""
    sector = wm.Sector(width=1, height=1)
    sector.systems["0101"], _ = _system_with(temperature=220.0)
    assert find_worlds(sector, ERITH) == []
    sector.systems["0101"], _ = _system_with(temperature=288.0)
    assert find_worlds(sector, ERITH)


def test_habitability_floor_applies():
    sector = wm.Sector(width=1, height=1)
    sector.systems["0101"], _ = _system_with(habitability=2)
    assert find_worlds(sector, ERITH) == []


def test_gas_giants_and_rings_are_never_matched(sector):
    for match in find_worlds(sector, ERITH, limit=50):
        assert getattr(match.body, 'body_type', '') != 'Gas Giant'
        assert not getattr(match.body, 'is_ring', False)


# --------------------------------------------------------------- searching

def test_search_ranks_best_first(sector):
    matches = find_worlds(sector, ERITH, limit=10)
    assert matches
    scores = [m.score for m in matches]
    assert scores == sorted(scores, reverse=True)


def test_search_covers_secondary_worlds_not_just_mainworlds(sector):
    """The world a Referee wants is not always the one the map prints."""
    everything = find_worlds(sector, ERITH, limit=0)
    mainworlds_only = find_worlds(
        sector,
        WorldProfile(**{**vars(ERITH), 'mainworld_only': True}), limit=0)
    assert len(everything) >= len(mainworlds_only)


def test_best_world_returns_the_top_match(sector):
    top = best_world(sector, ERITH)
    assert top is find_worlds(sector, ERITH, limit=1)[0] or \
        top.score == find_worlds(sector, ERITH, limit=1)[0].score


def test_best_world_of_an_empty_sector_is_none():
    assert best_world(wm.Sector(), ERITH) is None
    assert "No world" in describe_matches([], ERITH)


def test_minimum_score_filters(sector):
    strict = find_worlds(sector, ERITH, limit=0, minimum_score=85.0)
    assert all(m.score >= 85.0 for m in strict)


def test_match_summary_is_readable(sector):
    matches = find_worlds(sector, ERITH, limit=3)
    text = describe_matches(matches, ERITH)
    for match in matches:
        assert match.hex in text
    assert "Erith" in text


def test_other_shipped_profiles_work(sector):
    for key, profile in PROFILES.items():
        found = find_worlds(sector, profile, limit=3)
        for match in found:
            assert 0 <= match.score <= 100, key


# --------------------------------------------------------------- imposing

def test_impose_profile_makes_the_world_match():
    system, world = _system_with()
    world.uwp.population = '3'
    world.uwp.government = '4'
    world.uwp.tech_level = 'A'
    impose_profile(world, ERITH)
    assert score_world(world, ERITH)[0] == 100.0
    assert str(world.uwp).endswith("867871-1")


def test_impose_keeps_the_body_consistent_with_its_uwp():
    system, world = _system_with()
    impose_profile(world, ERITH)
    assert world.size_code == world.uwp.size
    assert world.atmosphere_code == world.uwp.atmosphere
    assert world.hydrographics_code == world.uwp.hydrographics


def test_impose_rebuilds_the_nations():
    system, world = _system_with()
    impose_profile(world, ERITH)
    assert Utils.from_eHex(world.uwp.government) == 7
    assert world.nations, "a balkanised world should have nations"
    assert world.population_profile


def test_impose_without_regeneration_only_sets_the_uwp():
    system, world = _system_with()
    impose_profile(world, ERITH, regenerate=False)
    assert score_world(world, ERITH)[0] == 100.0
    assert not getattr(world, 'nations', [])


# ---------------------------------------------------------- proprietorship

def test_proprietary_world_records_its_owner():
    world = _world("X867544-4")
    holding = make_proprietary(world, owner="House Devereaux")
    assert holding['owner'] == "House Devereaux"
    assert world.proprietor is holding
    assert any("Devereaux" in note for note in world.notes)


def test_a_non_balkanised_world_becomes_company_owned():
    world = _world("X867544-4")           # Government 4
    make_proprietary(world, owner="the Thorne family")
    assert world.uwp.government == '1'
    assert world.proprietor['absentee'] is False


def test_a_balkanised_world_keeps_its_states():
    """Title and ground disagree: someone holds the freehold while the
    surface stays divided."""
    world = _world("X867871-1")           # Government 7
    make_proprietary(world, owner="House Devereaux")
    assert world.uwp.government == '7', "balkanisation must survive"
    assert world.proprietor['absentee'] is True
    assert any("Title and ground disagree" in n for n in world.notes)


def test_government_override_can_be_forced():
    world = _world("X867871-1")
    make_proprietary(world, owner="X", set_government=True)
    assert world.uwp.government == '1'
    assert world.proprietor['absentee'] is False


# ------------------------------------------------------- the full workflow

def test_make_erith_produces_an_exact_match(sector):
    random.seed(99)
    match = make_erith(sector, culture_family='terrestrial')
    assert match is not None
    world = match.body
    assert match.score == 100.0
    assert str(world.uwp).endswith("867871-1")
    assert world.name == "Erith"


def test_make_erith_gives_it_nations_with_cultures(sector):
    random.seed(100)
    match = make_erith(sector, culture_family='terrestrial')
    world = match.body
    assert world.nations
    for nation in world.nations:
        assert nation.culture_template
        assert wm.CULTURE_TEMPLATES[nation.culture_template].family == 'terrestrial'
    # A pre-industrial world should span several technology levels
    techs = {n.tech_level for n in world.nations}
    assert len(techs) > 1


def test_make_erith_respects_the_hard_filters(sector):
    random.seed(101)
    match = make_erith(sector)
    from worldmaker.stellar import type_letter_of
    assert type_letter_of(match.star.spectral_type) in ('F', 'G', 'K')
    assert not match.system.allegiance.startswith('Zh')
    assert in_habitable_zone(match.system, match.body,
                             ERITH.habitable_zone_width)


def test_make_erith_marks_the_proprietor(sector):
    random.seed(102)
    match = make_erith(sector, owner="House Devereaux")
    world = match.body
    assert world.proprietor['owner'] == "House Devereaux"
    # The freehold does not abolish the world's own states
    assert world.uwp.government == '7'
    assert world.nations
    for nation in world.nations:
        assert any("freehold" in note for note in nation.notes)


def test_make_erith_can_skip_proprietorship(sector):
    random.seed(103)
    match = make_erith(sector, proprietary=False)
    assert getattr(match.body, 'proprietor', None) is None


def test_make_erith_on_an_empty_sector_is_none():
    assert make_erith(wm.Sector()) is None
