"""Tests for balkanised nations and the culture palette (WBH pp.155-156)."""
import random

import pytest

import worldmaker as wm
from worldmaker.classes import CulturalProfile, PlanetaryBody, UWP
from worldmaker.cultures import (
    CULTURE_TEMPLATES,
    FAMILIES,
    TRAIT_KEYS,
    apply_template_palette,
    culture_for_template,
    culture_from_template,
    culture_profile_string,
    describe_palette,
    procedural_culture,
    suggest_template,
    templates_for_tech_level,
    templates_in_family,
)
from worldmaker.government import generate_government_details
from worldmaker.nations import (
    Nation,
    assign_territories,
    describe_nations,
    generate_nation_name,
    generate_nations,
    land_cells,
    nations_per_faction,
)
from worldmaker.population import generate_population_details
from worldmaker.utils import Utils


def _make_world(uwp_str="E867871-1", name="Erith"):
    """A world with the Erith profile: Earth-like, populous, balkanised and
    pre-industrial."""
    world = PlanetaryBody(
        name=name, size_code=uwp_str[1], atmosphere_code=uwp_str[2],
        hydrographics_code=uwp_str[3], mean_temperature=288.0,
        tectonic_plates=7, biomass_rating=9,
        uwp=UWP(starport=uwp_str[0], size=uwp_str[1], atmosphere=uwp_str[2],
                hydrographics=uwp_str[3], population=uwp_str[4],
                government=uwp_str[5], law_level=uwp_str[6],
                tech_level=uwp_str[8]))
    generate_population_details(world)
    generate_government_details(world)
    return world


@pytest.fixture
def erith():
    random.seed(1867)
    world = _make_world()
    generate_nations(world, terrain=wm.generate_world_terrain(world))
    return world


# ------------------------------------------------------------- the count

def test_nations_per_faction_follows_the_book():
    """1D nations, with a 5 multiplying by 10 minus PCR and a 6 also by the
    Population code minus D3."""
    random.seed(1)
    plain = [nations_per_faction(pcr=9, population_code=3) for _ in range(500)]
    assert min(plain) >= 1
    # PCR 9 makes 10-PCR equal 1, so the escalation barely bites
    assert max(plain) <= 6 * 1 * max(2, 3 - 1)

    random.seed(1)
    sprawling = [nations_per_faction(pcr=0, population_code=9)
                 for _ in range(500)]
    assert max(sprawling) > max(plain), "low PCR should multiply out further"


def test_balkanised_world_gets_many_states(erith):
    assert erith.nation_count >= len(erith.nations)
    assert len(erith.nations) > 1


def test_detail_limit_bounds_the_work():
    """The book calls hundreds of nations "flavour, not a prelude to
    developing the details of hundreds of nations"."""
    random.seed(4)
    world = _make_world()
    generate_nations(world, detail_limit=5)
    assert len(world.nations) <= 5
    assert world.nation_count >= len(world.nations)


def test_unbalkanised_worlds_get_no_nations():
    random.seed(5)
    world = _make_world("C867544-8")     # Government 4, not 7
    generate_nations(world)
    assert world.nations == []
    assert world.nation_count == 0
    assert "not balkanised" in describe_nations(world)


# ------------------------------------------------ per-nation law and tech

def test_each_nation_has_its_own_law_and_tech(erith):
    """This is the point: a balkanised world is many societies, not one."""
    laws = {n.law_level for n in erith.nations}
    techs = {n.tech_level for n in erith.nations}
    assert len(laws) > 1, "every nation shares one Law Level"
    assert len(techs) > 1, "every nation shares one Tech Level"
    for nation in erith.nations:
        assert nation.law_profile
        assert nation.law_profile.split('-')[0] == Utils.eHex(nation.law_level)


def test_nations_carry_their_own_technology_profile(erith):
    for nation in erith.nations:
        assert nation.technology_profile, nation.name


def test_the_starport_state_carries_the_uwp_values(erith):
    """The Government Types table says a balkanised world's Law Level
    "refers to the government nearest the starport"."""
    seats = [n for n in erith.nations if n.holds_starport]
    assert len(seats) == 1
    seat = seats[0]
    assert seat.law_level == Utils.from_eHex(erith.uwp.law_level)
    assert seat.tech_level == Utils.from_eHex(erith.uwp.tech_level)
    assert any('starport' in note for note in seat.notes)


def test_a_preindustrial_world_spans_several_tech_levels(erith):
    """A world at TL 1 can hold neighbours at TL 0 and TL 3 - which is what
    makes it usable as a setting."""
    techs = sorted(n.tech_level for n in erith.nations)
    assert techs[-1] - techs[0] >= 2
    assert all(0 <= t <= 33 for t in techs)


def test_nation_populations_sum_to_the_world(erith):
    total = sum(n.population for n in erith.nations)
    assert total == erith.total_population
    assert all(n.population >= 0 for n in erith.nations)


def test_nation_names_are_unique_and_suit_the_government(erith):
    names = [n.name for n in erith.nations]
    assert len(names) == len(set(names))
    used = set()
    monarchy = generate_nation_name(14, used)
    assert any(word in monarchy for word in
               ("Kingdom", "Crown", "Realm", "Principality"))
    company = generate_nation_name(1, used)
    assert any(word in company for word in
               ("Combine", "Concern", "Holdings", "Trust"))


# ------------------------------------------------------------- territory

def test_territories_cover_the_land_without_overlap(erith):
    terrain = wm.generate_world_terrain(erith)
    nations = erith.nations
    assign_territories(nations, terrain)

    land = set(land_cells(terrain))
    claimed = []
    for nation in nations:
        claimed.extend(nation.territory)
    assert len(claimed) == len(set(claimed)), "two nations claim one cell"
    assert set(claimed) == land
    assert sum(n.land_share for n in nations) == pytest.approx(100, abs=1.5)


def test_no_nation_claims_ocean(erith):
    terrain = wm.generate_world_terrain(erith)
    assign_territories(erith.nations, terrain)
    for nation in erith.nations:
        for face, index in nation.territory:
            assert terrain[face][index] not in ('ocean', 'sea', 'ice')


def test_territory_assignment_survives_a_waterworld():
    random.seed(8)
    world = _make_world("E86A871-1")     # Hydrographics A
    generate_nations(world, terrain=wm.generate_world_terrain(world))
    assert world.nations       # nations exist even with little dry land


# ---------------------------------------------------------------- cities

def test_cities_are_assigned_to_nations(erith):
    """"Each city would receive at least a faction code" (WBH p.154)."""
    cities = erith.major_cities
    if not cities:
        pytest.skip("this world generated no major cities")
    for city in cities:
        assert city.get('nation'), city
        assert city.get('faction') is not None
    owned = sum(len(n.cities) for n in erith.nations)
    assert owned == len(cities)


def test_the_capital_belongs_to_the_starport_state(erith):
    capitals = [c for c in erith.major_cities if c.get('is_capital')]
    if not capitals:
        pytest.skip("no capital generated")
    seat = next(n for n in erith.nations if n.holds_starport)
    assert capitals[0]['nation'] == seat.name


# ------------------------------------------------------- culture palette

def test_palette_is_broad_and_not_earth_centric():
    """The palette deliberately reaches past terrestrial history."""
    assert len(CULTURE_TEMPLATES) >= 40
    by_family = {f: len(templates_in_family(f)) for f in FAMILIES}
    assert all(count > 0 for count in by_family.values())
    # Earth's own periods are one family among several, and not the largest
    assert by_family['terrestrial'] < (by_family['starfaring']
                                       + by_family['exotic'])
    assert by_family['exotic'] >= by_family['terrestrial']


def test_every_template_is_well_formed():
    for key, template in CULTURE_TEMPLATES.items():
        assert template.key == key
        assert template.name and template.description
        assert template.family in FAMILIES
        assert set(template.traits) == set(TRAIT_KEYS), key
        assert all(1 <= v <= 15 for v in template.traits.values()), key
        low, high = template.tech_level
        assert 0 <= low <= high <= 20, key


def test_template_culture_is_recognisable_but_varied():
    """Two nations on one template share a character without being identical."""
    random.seed(9)
    profiles = [culture_from_template('regency') for _ in range(30)]
    assert len({culture_profile_string(p) for p in profiles}) > 5
    centre = CULTURE_TEMPLATES['regency'].traits['militancy']
    values = [p.militancy for p in profiles]
    assert abs(sum(values) / len(values) - centre) <= 1.5


def test_unknown_template_fails_loudly():
    with pytest.raises(ValueError) as excinfo:
        culture_for_template('victorion')     # a typo
    assert 'unknown culture template' in str(excinfo.value)


def test_templates_are_tech_level_gated():
    low = templates_for_tech_level(1)
    high = templates_for_tech_level(14)
    assert low and high
    assert {t.key for t in low} != {t.key for t in high}
    assert 'information_age' not in {t.key for t in low}
    assert 'neolithic' not in {t.key for t in high}


def test_suggest_template_respects_family_and_tech():
    nation = Nation(government_code=14, tech_level=2)
    template = suggest_template(nation, family='terrestrial')
    assert template.family == 'terrestrial'
    assert template.suits(2)


def test_procedural_culture_is_the_default(erith):
    """No template is applied unless one is asked for."""
    assert all(n.culture_template == "" for n in erith.nations)
    assert all(isinstance(n.culture, CulturalProfile) for n in erith.nations)
    for nation in erith.nations:
        for key in TRAIT_KEYS:
            assert 1 <= getattr(nation.culture, key) <= 15


def test_applying_a_palette_labels_every_nation(erith):
    keys = apply_template_palette(erith, family='terrestrial')
    assert len(keys) == len(erith.nations)
    for nation in erith.nations:
        assert nation.culture_template in CULTURE_TEMPLATES
        assert CULTURE_TEMPLATES[nation.culture_template].family == 'terrestrial'
        assert any('Culture:' in note for note in nation.notes)


def test_applying_one_template_to_everything(erith):
    apply_template_palette(erith, template='dark_age')
    assert all(n.culture_template == 'dark_age' for n in erith.nations)


def test_an_exotic_palette_works_too(erith):
    apply_template_palette(erith, family='exotic')
    families = {CULTURE_TEMPLATES[n.culture_template].family
                for n in erith.nations}
    assert families == {'exotic'}


def test_culture_profile_string_has_eight_traits():
    profile = CulturalProfile(diversity=9, xenophilia=8, uniqueness=7,
                              symbology=7, cohesion=4, progressiveness=9,
                              expansionism=9, militancy=9)
    text = culture_profile_string(profile)
    assert text == "9877-4999"
    assert culture_profile_string(None) == ""


def test_palette_description_lists_every_template():
    text = describe_palette()
    for key in CULTURE_TEMPLATES:
        assert key in text


# ---------------------------------------------------------------- output

def test_describe_nations_reads_usefully(erith):
    text = describe_nations(erith)
    assert "Erith" in text
    assert "sovereign states" in text
    for nation in erith.nations:
        assert nation.name in text


def test_nation_profile_is_compact(erith):
    for nation in erith.nations:
        parts = nation.profile.split('-')
        assert len(parts) >= 3


# ----------------------------------------------------------- integration

def test_generated_sectors_produce_balkanised_worlds_with_nations():
    random.seed(21)
    sector = wm.generate_sector(8, 10)
    balkanised = [s.mainworld for s in sector.systems.values()
                  if s.mainworld
                  and Utils.from_eHex(s.mainworld.uwp.government) == 7
                  and Utils.from_eHex(s.mainworld.uwp.population) > 0]
    if not balkanised:
        pytest.skip("no balkanised worlds in this sample")
    for world in balkanised:
        assert world.nations, f"{world.name} is balkanised but has no nations"
        assert world.nation_count >= len(world.nations)
