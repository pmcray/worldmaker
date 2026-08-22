"""Tests for Special Circumstances (WBH pp.219-234)."""
import random

import pytest

import worldmaker as wm
from worldmaker.special import (
    ARTIFICIAL_WORLD_TYPES,
    BROWN_DWARF_TYPES,
    EMPTY_HEX_OBJECTS,
    WHITE_DWARF_AGING,
    brown_dwarf_type,
    crust_formation_age_myr,
    dead_star_system_exists,
    generate_artificial_world,
    generate_black_hole,
    generate_brown_dwarf,
    generate_brown_dwarf_system,
    generate_dead_star_system,
    generate_empty_hex,
    generate_neutron_star,
    generate_nebula,
    generate_primordial_system,
    generate_protostar_system,
    generate_rogue_gas_giant,
    generate_rogue_small_body,
    generate_rogue_terrestrial,
    generate_star_cluster_hex,
    generate_white_dwarf,
    is_primordial_host,
    jump_dm_for_target,
    jump_restrictions,
    populate_empty_hexes,
)
from worldmaker.classes import Sector, Star
from worldmaker.utils import Utils


@pytest.fixture(autouse=True)
def _seeded():
    random.seed(31337)


# -------------------------------------------------------------- white dwarfs

def test_white_dwarf_mass_and_diameter():
    """Mass = d10/100 + (2D-1)/10, under the 1.44 Chandrasekhar limit;
    diameter = (1/Mass) x 0.01, in the terrestrial planet range."""
    dwarfs = [generate_white_dwarf(1.0) for _ in range(300)]
    for d in dwarfs:
        assert 0.09 <= d.mass <= 1.44, d.mass
        assert d.diameter == pytest.approx(0.01 / d.mass, abs=1e-4)
        # A solar diameter is 1.39 million km, so this lands near planet scale
        assert 5000 < d.diameter * 1391000 < 200000
        assert d.mao == 0.001
    assert len({d.mass for d in dwarfs}) > 30


def test_white_dwarf_cools_with_age():
    """The aging table runs from over 100,000K down to about 3,800K."""
    young = generate_white_dwarf(0.0)
    middle = generate_white_dwarf(1.5)
    old = generate_white_dwarf(13.0)
    # Compare at equal mass by scaling out the Mass/0.6 factor
    assert young.temp_k / young.mass > middle.temp_k / middle.mass
    assert middle.temp_k / middle.mass > old.temp_k / old.mass


def test_white_dwarf_aging_table_is_monotone():
    ages = [row[0] for row in WHITE_DWARF_AGING]
    temps = [row[1] for row in WHITE_DWARF_AGING]
    assert ages == sorted(ages)
    assert temps == sorted(temps, reverse=True)


# ------------------------------------------------------------ neutron stars

def test_neutron_star_mass_and_diameter():
    """Mass = 1 + 1D/10 (a six adds (1D-1)/10), never past the 2.16 collapse
    limit; diameter 19+1D kilometres."""
    stars = [generate_neutron_star('Neutron Star', 1.0) for _ in range(200)]
    for s in stars:
        assert 1.1 <= s.mass <= 2.16, s.mass
        diameter_km = s.diameter * 1391000
        assert 19.9 < diameter_km < 25.1, diameter_km


def test_pulsar_and_magnetar_are_neutron_stars():
    pulsar = generate_neutron_star('Pulsar', 1.0)
    magnetar = generate_neutron_star('Magnetar', 1.0)
    assert pulsar.spectral_type == 'Pulsar'
    # Magnetars behave as pulsars for Traveller purposes
    assert magnetar.spectral_type == 'Pulsar'


# --------------------------------------------------------------- black holes

def test_black_hole_mass_and_diameter():
    """Mass = 2.1 + 1D - 1 + d10/10, exploding on sixes; diameter =
    5.9km x Mass; no radiation at all."""
    holes = [generate_black_hole() for _ in range(300)]
    for h in holes:
        assert h.mass >= 2.1, h.mass
        assert h.diameter * 1391000 == pytest.approx(5.9 * h.mass, rel=1e-3)
        assert h.luminosity == 0.0
        assert h.temp_k == 0.0
    # The exploding sixes must occasionally push well past the 2.1-8 base band
    assert max(h.mass for h in holes) > 9


# -------------------------------------------------------------- brown dwarfs

def test_brown_dwarf_mass_range():
    """Mass = 1D/100 + (4D-1)/1000: 0.013 to 0.083 solar masses."""
    dwarfs = [generate_brown_dwarf(1.0) for _ in range(300)]
    for d in dwarfs:
        assert 0.012 <= d.mass <= 0.084, d.mass
        assert d.mao == 0.005
    assert len({d.mass for d in dwarfs}) > 20


def test_brown_dwarf_types_match_the_table():
    """The Brown Dwarf Types table's own mass rows map to their types."""
    for name, _temp, mass, _diam, _lum in BROWN_DWARF_TYPES:
        assert brown_dwarf_type(mass, age_gyr=1.0) == name


def test_brown_dwarf_cools_into_later_types():
    """Aging steps the subtype down one per Gyr above 0.05 mass, two below."""
    assert brown_dwarf_type(0.080, 1.0) == 'L0'
    assert brown_dwarf_type(0.080, 4.0) == 'L3'
    # A smaller dwarf cools twice as fast
    assert brown_dwarf_type(0.040, 1.0) == 'T5'
    assert brown_dwarf_type(0.040, 3.0) == 'T9'


# ------------------------------------------------------- dead star systems

def test_dead_star_system_existence_dms():
    """The 8+ check takes DM-2 for multiple dead stars or a neutron star and
    DM-4 for a black hole, so black hole systems are rarest."""
    random.seed(1)
    white = sum(dead_star_system_exists(['D']) for _ in range(2000))
    random.seed(1)
    neutron = sum(dead_star_system_exists(['Neutron Star']) for _ in range(2000))
    random.seed(1)
    hole = sum(dead_star_system_exists(['Black Hole']) for _ in range(2000))
    assert white > neutron > hole
    # A natural 12 always succeeds, so none of them is ever impossible
    assert hole > 0


def test_dead_star_system_uses_dead_star_rules():
    """Gas giants are rarer, belts commoner, terrestrials 1D-2, MAO 0.001."""
    systems = [generate_dead_star_system(f"D{i}", 'D') for i in range(40)]
    populated = [s for s in systems if s.all_worlds]
    assert populated, "no dead star system got a planetary system"
    for s in populated:
        assert s.primary_star.spectral_type == 'D'
        assert s.primary_star.mao == 0.001
        # 1D-2 caps the rolled count at 4; anomalous orbits then add worlds
        # of their own on top, so they have to be allowed for.
        assert s.terrestrial_planet_count <= 4 + len(s.anomalous_planets)
        for w in s.all_worlds:
            assert w.orbit_num > 0


def test_some_dead_stars_have_no_planets():
    """Most dead stars do not have a planetary system (WBH p.229)."""
    systems = [generate_dead_star_system(f"D{i}", 'Black Hole') for i in range(40)]
    assert any(not s.all_worlds for s in systems)


def test_pulsar_worlds_carry_radioactive_taint():
    """All planets orbiting a pulsar or magnetar take the radioactive taint
    at severity and persistence 9 (WBH p.229)."""
    found = False
    for i in range(60):
        system = generate_dead_star_system(f"P{i}", 'Pulsar')
        for world in system.all_worlds:
            if world.body_type != 'Terrestrial':
                continue
            found = True
            assert world.atmosphere_taint['type'] == 'Radioactive Particulates'
            assert world.atmosphere_taint['severity'] == '9'
            assert world.atmosphere_taint['persistence'] == '9'
        if found:
            break
    assert found, "no pulsar system produced a terrestrial world"


def test_brown_dwarf_system_rules():
    """A brown dwarf primary gets a small system with MAO 0.005."""
    systems = [generate_brown_dwarf_system(f"B{i}") for i in range(20)]
    for s in systems:
        assert s.primary_star.spectral_type == 'BD'
        assert s.primary_star.mao == 0.005
        for w in s.all_worlds:
            assert w.orbit_num >= 0.005 - 1e-9


# ---------------------------------------- protostar and primordial systems

def test_protostar_system_is_young_and_debris_filled():
    """Every planetary orbit also holds a planetoid belt, and nothing is
    alive yet (WBH p.225)."""
    system = generate_protostar_system("Proto")
    assert system.age_gyr < 0.02          # under about 20 million years
    planets = [w for w in system.all_worlds
               if w.body_type in ('Terrestrial', 'Gas Giant')]
    belts = [w for w in system.all_worlds if w.body_type == 'Planetoid Belt']
    assert len(belts) >= len(planets)
    for w in system.all_worlds:
        if w.body_type == 'Terrestrial':
            assert w.biomass_rating == 0
            assert 'protostar' in w.life_details


def test_protostar_worlds_are_size_capped_by_age():
    """The maximum terrestrial size equals the system age in million
    years."""
    for _ in range(10):
        system = generate_protostar_system("Proto")
        age_myr = system.age_gyr * 1000
        for w in system.all_worlds:
            if w.body_type != 'Terrestrial':
                continue
            assert Utils.from_eHex(w.size_code) <= max(1, int(age_myr))


def test_protostar_magma_oceans():
    """Worlds of Size 2+ younger than (Size-2)^2 + 2 million years still have
    magma oceans above 1,500K."""
    assert crust_formation_age_myr(2) == 2
    assert crust_formation_age_myr(8) == 38
    found = False
    for _ in range(15):
        system = generate_protostar_system("Proto")
        for w in system.all_worlds:
            if w.body_type != 'Terrestrial':
                continue
            size = Utils.from_eHex(w.size_code)
            if size >= 2 and system.age_gyr * 1000 < crust_formation_age_myr(size):
                found = True
                assert w.hydrographics_code == 'A'
                assert w.mean_temperature >= 1500
        if found:
            break
    assert found, "no protostar world had a magma ocean"


def test_protostar_atmospheres_are_remapped():
    """Atmospheres roll at DM+4 and collapse onto A, C, F and H; vacuum and
    trace results are below the table's bands and survive (WBH p.225)."""
    seen = set()
    for _ in range(10):
        system = generate_protostar_system("Proto")
        for w in system.all_worlds:
            if w.body_type != 'Terrestrial' or not w.atmosphere_code:
                continue
            if Utils.from_eHex(w.size_code) == 0:
                continue
            assert w.atmosphere_code in ('0', '1', 'A', 'C', 'F', 'H'), (
                w.atmosphere_code)
            seen.add(w.atmosphere_code)
    # The DM+4 pushes most results into the dense bands, not just vacuum
    assert seen & {'A', 'C', 'F', 'H'}


def test_primordial_system_is_young_and_lifeless():
    system = generate_primordial_system("Prim")
    assert 0.01 <= system.age_gyr < 0.1     # 10 to 100 million years
    for w in system.all_worlds:
        if w.body_type == 'Terrestrial':
            assert w.biomass_rating == 0
            assert 'primordial' in w.life_details


def test_primordial_hosts_identified():
    """Class Ia/Ib/II, O-types and stars over 8 solar masses (WBH p.225)."""
    assert is_primordial_host(Star(spectral_type="A2 Ia", mass=10.0))
    assert is_primordial_host(Star(spectral_type="G2 V", mass=9.0))
    assert is_primordial_host(Star(spectral_type="O5 V", mass=5.0))
    assert not is_primordial_host(Star(spectral_type="O5 VI", mass=1.0))
    assert not is_primordial_host(Star(spectral_type="G2 V", mass=1.0))


# --------------------------------------------------------------- rogues

def test_rogue_terrestrial_sizes():
    """Large rogues are Size 1D+9; small ones 2D-2 with 0 becoming 1 and A
    becoming 9 (WBH p.220)."""
    large = {generate_rogue_terrestrial(large=True).size_code for _ in range(200)}
    small = {generate_rogue_terrestrial(large=False).size_code for _ in range(200)}
    assert large <= set('ABCDEF')
    assert small <= set('123456789')
    assert '0' not in small


def test_rogue_worlds_are_cold_and_starless():
    for _ in range(20):
        rogue = generate_rogue_terrestrial(large=True)
        assert rogue.mean_temperature < 100
        assert any('Rogue world' in n for n in rogue.notes)
        assert not rogue.parent_star_group


def test_rogue_gas_giant_moons_take_the_negative_dm():
    """Rogue gas giants roll significant moons at DM-1 per dice."""
    random.seed(4)
    rogue_moons = sum(len(generate_rogue_gas_giant('GL').satellites)
                      for _ in range(200))
    assert rogue_moons >= 0
    giants = [generate_rogue_gas_giant() for _ in range(50)]
    assert all(g.body_type == 'Gas Giant' for g in giants)
    assert {g.size_code[:2] for g in giants} <= {'GS', 'GM', 'GL'}


def test_rogue_small_bodies():
    """Size S on a 1D roll of 6, otherwise Size 0; three composition
    classes."""
    bodies = [generate_rogue_small_body() for _ in range(300)]
    assert {b['size'] for b in bodies} == {'S', '0'}
    s_count = sum(1 for b in bodies if b['size'] == 'S')
    assert 20 < s_count < 90                     # about one in six
    assert len({b['composition'] for b in bodies}) == 3


# ----------------------------------------------------------- empty hexes

def test_empty_hex_object_table_survey_indices():
    """The Empty Hex Objects table's survey indices and detection points
    (WBH p.221)."""
    assert EMPTY_HEX_OBJECTS['White Dwarf']['si'] == 3
    assert EMPTY_HEX_OBJECTS['Brown Dwarf']['detection'] == 20
    assert EMPTY_HEX_OBJECTS['Large Gas Giant']['detection'] == 60
    assert EMPTY_HEX_OBJECTS['Small Bodies']['si'] == 12
    # Dimmer, smaller objects always need at least as much observation
    ordered = ['Brown Dwarf', 'Large Gas Giant', 'Medium Gas Giant',
               'Small Gas Giant', 'Terrestrial (A+)', 'Terrestrial (1-9)']
    points = [EMPTY_HEX_OBJECTS[k]['detection'] for k in ordered]
    assert points == sorted(points)


def test_empty_hex_frequencies():
    """Brown dwarfs are as likely as a system in the region; white dwarfs
    need a 6 on 1D first; neutron stars and black holes an 18 on 3D."""
    random.seed(2024)
    kinds = []
    for _ in range(400):
        survey = generate_empty_hex(density_target=4)
        kinds.append(survey.star_system.primary_star.spectral_type
                     if survey.star_system else None)
    brown = kinds.count('BD')
    white = kinds.count('D')
    dead = kinds.count('Neutron Star') + kinds.count('Black Hole')
    assert 130 < brown < 250      # about half the hexes
    assert 5 < white < 60         # about one in twelve
    assert dead <= 6              # about one in 430


def test_empty_hexes_hold_rogue_worlds():
    """Rogue planets coexist with any star-like object: 20 existence checks
    per hex, so about ten worlds at standard density."""
    random.seed(7)
    totals = [len(generate_empty_hex(4).rogue_worlds) for _ in range(50)]
    assert sum(totals) / len(totals) == pytest.approx(10, abs=2.5)


def test_populate_empty_hexes_skips_charted_systems():
    random.seed(3)
    sector = wm.generate_sector(width=4, height=4)
    charted = set(sector.systems)
    deep = populate_empty_hexes(sector, density_target=4)
    assert deep is sector.deep_space
    for hex_coord, survey in deep.items():
        assert hex_coord not in charted
        assert not survey.is_empty
        assert survey.hex_coord == hex_coord


# -------------------------------------------------------------- nebulae

def test_nebula_types_and_central_objects():
    """A planetary nebula carries a newly formed white dwarf; a supernova
    remnant may hold a neutron star or black hole (WBH pp.229-230)."""
    random.seed(8)
    seen = set()
    for _ in range(200):
        nebula = generate_nebula()
        seen.add(nebula['type'])
        if nebula['type'] == 'Planetary Nebula':
            central = nebula['central_object']
            assert central is not None
            assert central.spectral_type == 'D'
            # A brand new white dwarf sits on the 0.000 column: 100,000K,
            # scaled by its mass against the table's 0.6 baseline
            assert central.temp_k == pytest.approx(
                100000 * central.mass / 0.6, rel=1e-3)
            assert nebula['hexes'] in (1, 7)
        elif nebula['type'] == 'Supernova Remnant':
            central = nebula['central_object']
            if central is not None:
                assert central.spectral_type in ('Neutron Star', 'Pulsar',
                                                 'Black Hole')
    assert seen == {'Planetary Nebula', 'Dark Nebula',
                    'Ionised Hydrogen Nebula', 'Supernova Remnant'}


# --------------------------------------------------------- star clusters

def test_star_cluster_systems_share_an_age():
    """A cluster hex holds 2D+5 systems, all of the same age (WBH p.231)."""
    systems = generate_star_cluster_hex("Cluster")
    assert 7 <= len(systems) <= 17
    assert len({s.age_gyr for s in systems}) == 1
    assert systems[0].age_gyr <= 1.8       # 1D x 1D x 50 Myr


# ------------------------------------------------------ artificial worlds

def test_artificial_world_types_are_tech_gated():
    """A TL15 civilisation cannot build a Dyson sphere (TL29)."""
    for _ in range(50):
        low = generate_artificial_world(max_tech_level=8)
        assert 'TL' in low.notes[0]
        tl = int(low.notes[0].split('TL')[1].split(')')[0])
        assert tl <= 8
    high = {generate_artificial_world(max_tech_level=29).name for _ in range(200)}
    assert 'Dyson Sphere' in high


def test_artificial_world_table_matches_the_book():
    names = {t['name']: t['tl'] for t in ARTIFICIAL_WORLD_TYPES}
    assert names['Station Module'] == 6
    assert names['Spin Habitat'] == 8
    assert names['Ring Moon'] == 16
    assert names['Ringworld'] == 27
    assert names['Dyson Sphere'] == 29
    # World-sized and larger constructs use Size code X
    assert all(t['size_code'] in ('0', 'X', None) for t in ARTIFICIAL_WORLD_TYPES)


# ------------------------------------------------------ jump restrictions

def test_empty_hex_jump_dms():
    """The extra Astrogation check's target DMs (WBH p.223)."""
    assert jump_dm_for_target('White Dwarf') == -2
    assert jump_dm_for_target('Brown Dwarf') == -2
    assert jump_dm_for_target('Black Hole') == -3
    assert jump_dm_for_target('Gas Giant') == -3
    assert jump_dm_for_target('Terrestrial') == -4
    assert jump_dm_for_target('Deep Space') == -6
    assert jump_dm_for_target('anything unlisted') == -6


def test_jump_restriction_notes():
    protostar = generate_protostar_system("Proto")
    notes = " ".join(jump_restrictions(protostar))
    assert 'Protostar' in notes

    primordial = generate_primordial_system("Prim")
    assert 'Primordial' in " ".join(jump_restrictions(primordial))

    pulsar = generate_dead_star_system("Pulse", 'Pulsar')
    notes = " ".join(jump_restrictions(pulsar))
    assert 'DM-4' in notes
    assert 'Empty Hex Jump DMs' in notes

    ordinary = wm.generate_full_system("Ordinary")
    assert 'Empty Hex Jump DMs' not in " ".join(jump_restrictions(ordinary))
