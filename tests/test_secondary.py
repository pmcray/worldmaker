"""Tests for secondary world populations (WBH p.155)."""
import random

import pytest

import worldmaker as wm
from worldmaker.classes import PlanetaryBody, StellarSystem, UWP
from worldmaker.secondary import (
    can_be_inhabited,
    generate_secondary_populations,
    max_secondary_population,
    secondary_population_code,
    settlement_appeal,
    settlement_candidates,
)
from worldmaker.utils import Utils

N = 120


@pytest.fixture(scope="module")
def systems():
    random.seed(555)
    return [wm.generate_full_system(f"S{i}") for i in range(N)]


def _secondaries(system):
    return [b for b in system.all_bodies
            if getattr(b, 'is_secondary_world', False)]


# ------------------------------------------------------------- the cap

def test_max_secondary_population_is_below_the_mainworld():
    """Maximum offworld Population is the mainworld's minus 1D, and never
    more than one below it."""
    world = PlanetaryBody(uwp=UWP(population='8'))
    random.seed(1)
    values = [max_secondary_population(world) for _ in range(400)]
    assert max(values) == 7          # never equals the mainworld's 8
    assert min(values) == 2          # 8 - 6
    assert all(v <= 7 for v in values)


def test_low_population_mainworld_rules_out_secondaries():
    """When the roll drops the cap to zero or less, the book stops checking
    the system at all."""
    world = PlanetaryBody(uwp=UWP(population='1'))
    random.seed(2)
    assert all(max_secondary_population(world) <= 0 for _ in range(50))


def test_secondary_population_code_matches_the_books_method():
    """1D for the Population code, with 5 or 6 meaning nobody lives there."""
    random.seed(3)
    rolls = [secondary_population_code(9) for _ in range(600)]
    assert set(rolls) == {0, 1, 2, 3, 4}
    empty = rolls.count(0) / len(rolls)
    assert 0.28 < empty < 0.39       # two results in six
    assert secondary_population_code(0) == 0


def test_secondary_population_respects_the_cap():
    random.seed(4)
    assert all(secondary_population_code(2) <= 2 for _ in range(200))


# ------------------------------------------------- habitation by tech level

def test_tech_level_restricts_habitation():
    """An inhospitable world cannot be settled below the Tech Level its
    environment demands (WBH p.155, citing the Tech Level and Environment
    table)."""
    vacuum = PlanetaryBody(atmosphere_code='0', habitability_rating=0,
                           uwp=UWP(atmosphere='0'))
    assert not can_be_inhabited(vacuum, tech_level=5)
    assert can_be_inhabited(vacuum, tech_level=9)

    benign = PlanetaryBody(atmosphere_code='6', habitability_rating=9,
                           uwp=UWP(atmosphere='6'))
    assert can_be_inhabited(benign, tech_level=0)


def test_no_secondary_world_is_below_its_habitation_floor(systems):
    from worldmaker.population import minimum_sustainable_tl
    checked = 0
    for system in systems:
        for body in _secondaries(system):
            checked += 1
            tl = Utils.from_eHex(body.uwp.tech_level)
            assert tl >= minimum_sustainable_tl(body), (
                f"{body.designation} at TL{tl} cannot survive its own "
                f"environment")
    assert checked > 20


# ----------------------------------------------------------- candidates

def test_appeal_favours_habitable_and_resource_rich_bodies():
    barren = PlanetaryBody(habitability_rating=0, resource_rating=0)
    garden = PlanetaryBody(habitability_rating=9, resource_rating=2)
    mine = PlanetaryBody(habitability_rating=1, resource_rating=10)
    belt = PlanetaryBody(body_type='Planetoid Belt', habitability_rating=0,
                         resource_rating=4)
    assert settlement_appeal(garden) > settlement_appeal(barren)
    assert settlement_appeal(mine) > settlement_appeal(barren)
    assert settlement_appeal(belt) > settlement_appeal(barren)


def test_gas_giants_are_never_settlement_candidates(systems):
    for system in systems:
        for body in _secondaries(system):
            assert getattr(body, 'body_type', '') != 'Gas Giant'


def test_rings_are_never_settled(systems):
    for system in systems:
        for body in _secondaries(system):
            assert not getattr(body, 'is_ring', False)


def test_candidate_list_is_bounded(systems):
    """The book warns against checking every body in the system."""
    for system in systems:
        mainworld = system.mainworld
        if mainworld is None:
            continue
        tl = Utils.from_eHex(mainworld.uwp.tech_level)
        assert len(settlement_candidates(system, mainworld, tl, limit=6)) <= 6


# ------------------------------------------------------- generated results

def test_secondary_worlds_stay_below_the_mainworld(systems):
    """"These worlds will almost always have a smaller population than the
    mainworld" - here, always."""
    checked = 0
    for system in systems:
        mainworld = system.mainworld
        main_pop = Utils.from_eHex(mainworld.uwp.population)
        for body in _secondaries(system):
            checked += 1
            assert Utils.from_eHex(body.uwp.population) < main_pop
    assert checked > 20


def test_secondary_worlds_are_a_minority_of_bodies(systems):
    """Most of a system is empty rock. Populating everything would be
    exactly the error the book cautions against."""
    bodies = sum(len(s.all_bodies) - 1 for s in systems)
    inhabited = sum(len(_secondaries(s)) for s in systems)
    assert inhabited > 0
    assert inhabited / bodies < 0.15, f"{inhabited}/{bodies} bodies inhabited"


def test_some_systems_have_no_secondary_populations(systems):
    empty = [s for s in systems if not _secondaries(s)]
    assert len(empty) > N // 5


def test_secondary_worlds_carry_full_social_detail(systems):
    checked = 0
    for system in systems:
        for body in _secondaries(system):
            checked += 1
            assert body.uwp.population != '0'
            assert body.total_population > 0
            assert body.population_digit > 0
            assert body.government_type, "no government generated"
            assert body.technology_profile, "no technology profile"
            assert body.population_profile
    assert checked > 20


def test_colonies_and_independents_both_occur(systems):
    kinds = {getattr(b, 'affiliated', None)
             for s in systems for b in _secondaries(s)}
    assert kinds == {True, False}


def test_colony_government_is_captive(systems):
    """An affiliated world answers elsewhere - the book has a government
    code for that."""
    checked = 0
    for system in systems:
        for body in _secondaries(system):
            if body.affiliated:
                checked += 1
                assert body.uwp.government == '6'
                assert any('colony' in n for n in body.notes)
    assert checked > 5


def test_colonies_do_not_outpace_their_mainworld(systems):
    checked = 0
    for system in systems:
        main_tl = Utils.from_eHex(system.mainworld.uwp.tech_level)
        for body in _secondaries(system):
            if not body.affiliated:
                continue
            tl = Utils.from_eHex(body.uwp.tech_level)
            # A colony may be forced up by a hostile environment, never by
            # ambition
            from worldmaker.population import minimum_sustainable_tl
            checked += 1
            assert tl <= max(main_tl, minimum_sustainable_tl(body))
    assert checked > 5


# ----------------------------------------------------- UWPs on every body

def test_every_body_presents_its_own_physical_uwp(systems):
    """A planet's UWP used to read X000000-0 however large and wet it was;
    only moons carried their size, atmosphere and hydrographics."""
    checked = 0
    for system in systems:
        for body in system.all_bodies:
            if getattr(body, 'is_ring', False):
                continue
            if getattr(body, 'body_type', '') == 'Gas Giant':
                continue
            size = str(getattr(body, 'size_code', '') or '0')
            if len(size) != 1 or size == '0':
                continue
            checked += 1
            assert body.uwp.size == size, (
                f"{body.designation}: UWP says size {body.uwp.size}, "
                f"body is {size}")
            assert body.uwp.atmosphere == str(body.atmosphere_code or '0')
            assert body.uwp.hydrographics == str(body.hydrographics_code or '0')
    assert checked > 200


def test_uninhabited_bodies_keep_a_zero_population(systems):
    for system in systems:
        for body in system.all_bodies:
            if getattr(body, 'is_secondary_world', False):
                continue
            if body is system.mainworld or getattr(body, 'is_ring', False):
                continue
            assert body.uwp.population == '0'


# ------------------------------------------------------------ integration

def test_a_system_with_no_mainworld_is_handled():
    system = StellarSystem(name="Empty")
    assert generate_secondary_populations(system) == []


def test_secondary_worlds_reach_the_sector_world_count():
    """The T5 W field counts the system's worlds, so secondary populations
    must not break the export."""
    random.seed(31)
    sector = wm.generate_sector(6, 6)
    rows = wm.parse_t5_column(wm.export_sector_sec_file(sector))
    assert rows
    assert all(r['W'].isdigit() and int(r['W']) > 0 for r in rows)
