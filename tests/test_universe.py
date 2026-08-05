"""Tests for the guided universe creation entry point (SCG pp.3-8)."""
import random

import pytest

import worldmaker as wm
from worldmaker.classes import Sector
from worldmaker.universe import (
    ANOMALY_KINDS,
    DENSITY_TARGETS,
    SOPHONT_PREVALENCE,
    TECHNOLOGY_LEVELS,
    TRAJECTORIES,
    UNIVERSE_PRESETS,
    Anomaly,
    Universe,
    build_default_timeline,
    create_universe,
    generate_universe_sector,
)
from worldmaker.sector import hex_distance
from worldmaker.utils import Utils


@pytest.fixture(autouse=True)
def _seeded():
    random.seed(90210)


# ------------------------------------------------------------- the settings

def test_defaults_match_standard_space():
    """Standard space puts a system in a hex on 1D 4+ (SCG p.9)."""
    universe = create_universe("Default")
    assert universe.density_target == 4
    assert DENSITY_TARGETS['standard'] == 4


def test_density_range_suits_jump_1_to_jump_6():
    """The book notes jump-1 to jump-6 ships suit a 2-in-6 to 5-in-6 chance
    of a system per hex."""
    assert DENSITY_TARGETS['cluster'] < DENSITY_TARGETS['dense']
    assert DENSITY_TARGETS['dense'] < DENSITY_TARGETS['standard']
    assert DENSITY_TARGETS['standard'] < DENSITY_TARGETS['scattered']
    assert DENSITY_TARGETS['scattered'] < DENSITY_TARGETS['sparse']
    playable = [DENSITY_TARGETS[k] for k in
                ('cluster', 'dense', 'standard', 'scattered')]
    assert playable == [2, 3, 4, 5]


def test_technology_ceiling_and_trajectory_dm():
    universe = create_universe("T", technology='early', trajectory='decline')
    assert universe.max_tech_level == 9
    assert universe.population_dm == -1
    assert create_universe("T", trajectory='expansion').population_dm == 1
    assert create_universe("T", trajectory='stasis').population_dm == 0


def test_unknown_settings_are_rejected():
    for key, value in (('density', 'crowded'), ('technology', 'godlike'),
                       ('trajectory', 'sideways'),
                       ('sophont_prevalence', 'everywhere')):
        with pytest.raises(ValueError):
            create_universe("Bad", **{key: value})
    with pytest.raises(ValueError):
        create_universe("Bad", preset='nonexistent')


def test_presets_are_all_valid():
    for name in UNIVERSE_PRESETS:
        universe = create_universe(f"Preset {name}", preset=name)
        assert universe.density in DENSITY_TARGETS
        assert universe.technology in TECHNOLOGY_LEVELS
        assert universe.trajectory in TRAJECTORIES
        assert universe.sophont_prevalence in SOPHONT_PREVALENCE
        assert universe.polity_count >= 1
        assert universe.background


def test_overrides_beat_the_preset():
    universe = create_universe("T", preset='frontier', density='dense',
                               polity_count=7)
    assert universe.density == 'dense'
    assert universe.polity_count == 7
    # Untouched preset values survive
    assert universe.trajectory == UNIVERSE_PRESETS['frontier']['trajectory']


# ------------------------------------------------------------- sophonts

def test_sophont_prevalence_scales_with_region_size():
    full = Sector(width=32, height=40)
    sub = Sector(width=8, height=10)
    common = create_universe("T", sophont_prevalence='common')
    assert common.sophont_counts(full)[0] > common.sophont_counts(sub)[0]

    none = create_universe("T", sophont_prevalence='none')
    assert none.sophont_counts(full) == (0, 0)

    standard = create_universe("T", sophont_prevalence='standard')
    rare = create_universe("T", sophont_prevalence='rare')
    assert standard.sophont_counts(full)[0] > rare.sophont_counts(full)[0]


def test_no_sophonts_universe_generates_none():
    universe = create_universe("Empty", preset='charted_space',
                               sophont_prevalence='none')
    sector = generate_universe_sector(universe, "S", width=8, height=10)
    assert sector.native_sophonts == {}


# ------------------------------------------------------------- anomalies

def test_anomaly_kinds_are_validated():
    with pytest.raises(ValueError):
        Anomaly(kind='gravity_storm')
    for kind in ANOMALY_KINDS:
        assert Anomaly(kind=kind).description


def test_anomaly_radius_covers_the_right_hexes():
    universe = create_universe("T")
    anomaly = universe.add_anomaly('barren', "Zone", centre="1010", radius=2)
    assert "1010" in anomaly.hexes
    for hex_coord in anomaly.hexes:
        assert hex_distance("1010", hex_coord) <= 2
    # A radius-2 patch on a hex grid is 19 hexes
    assert len(anomaly.hexes) == 19
    assert anomaly.hexes == sorted(set(anomaly.hexes))


def test_anomaly_explicit_hex_list():
    universe = create_universe("T")
    anomaly = universe.add_anomaly('ruins', "Relics",
                                   hexes=["0101", "0102", "0101"])
    assert anomaly.hexes == ["0101", "0102"]
    assert universe.anomalies_at("0101") == [anomaly]
    assert universe.anomalies_at("3030") == []


def test_rift_and_cluster_change_the_density_target():
    """Rift and cluster anomalies act during generation, per hex."""
    universe = create_universe("T", density='standard')
    universe.add_anomaly('rift', "Gap", hexes=["0101"])
    universe.add_anomaly('cluster', "Knot", hexes=["0202"])
    assert universe.density_target_for("0101") == DENSITY_TARGETS['rift']
    assert universe.density_target_for("0202") == DENSITY_TARGETS['cluster']
    assert universe.density_target_for("0303") == 4


def test_rift_region_stays_empty():
    universe = create_universe("T", preset='charted_space')
    universe.add_anomaly('rift', "The Gap", centre="0404", radius=2)
    sector = generate_universe_sector(universe, "S", width=8, height=10)
    rift_hexes = set(universe.anomalies[0].hexes)
    assert not (rift_hexes & set(sector.systems)), "systems generated in a rift"
    assert sector.systems, "the rest of the sector should still be populated"


def test_cluster_region_is_denser():
    """A cluster fills nearly every hex it covers."""
    universe = create_universe("T", density='sparse')
    universe.add_anomaly('cluster', "Knot", centre="0404", radius=2)
    sector = generate_universe_sector(universe, "S", width=8, height=10)
    cluster_hexes = [h for h in universe.anomalies[0].hexes
                     if int(h[:2]) <= 8 and int(h[2:]) <= 10]
    inside = sum(1 for h in cluster_hexes if h in sector.systems)
    outside_hexes = [f"{c:02d}{r:02d}" for c in range(1, 9)
                     for r in range(1, 11)
                     if f"{c:02d}{r:02d}" not in universe.anomalies[0].hexes]
    outside = sum(1 for h in outside_hexes if h in sector.systems)
    assert inside / len(cluster_hexes) > outside / len(outside_hexes)


def test_barren_anomaly_empties_worlds():
    universe = create_universe("T", preset='charted_space')
    universe.add_anomaly('barren', "Quiet Zone", centre="0404", radius=3)
    sector = generate_universe_sector(universe, "S", width=8, height=10)
    affected = [h for h in universe.anomalies[0].hexes if h in sector.systems]
    assert affected, "no systems fell inside the anomaly"
    for hex_coord in affected:
        mainworld = sector.systems[hex_coord].mainworld
        assert mainworld.uwp.population == '0'
        assert mainworld.uwp.starport == 'X'
        assert 'Ba' in mainworld.trade_codes
        assert sector.systems[hex_coord].bases == []


def test_supernova_anomaly_sterilises_and_red_zones():
    universe = create_universe("T", preset='charted_space')
    universe.add_anomaly('supernova', "Blast", centre="0404", radius=3)
    sector = generate_universe_sector(universe, "S", width=8, height=10)
    affected = [h for h in universe.anomalies[0].hexes if h in sector.systems]
    assert affected
    for hex_coord in affected:
        system = sector.systems[hex_coord]
        assert system.travel_zone == 'R'
        assert system.mainworld.biomass_rating == 0
        assert system.mainworld.atmosphere_taint['type'] == \
            'Radioactive Particulates'


def test_tech_inhibitor_caps_tech_level():
    universe = create_universe("T", preset='charted_space')
    universe.add_anomaly('tech_inhibitor', "Null Field", centre="0404", radius=3)
    sector = generate_universe_sector(universe, "S", width=8, height=10)
    affected = [h for h in universe.anomalies[0].hexes if h in sector.systems]
    assert affected
    for hex_coord in affected:
        mainworld = sector.systems[hex_coord].mainworld
        assert Utils.from_eHex(mainworld.uwp.tech_level) <= 5
        assert mainworld.uwp.starport not in ('A', 'B', 'C')


def test_warfare_downgrades_starports():
    universe = create_universe("T", preset='charted_space')
    universe.add_anomaly('warfare', "The Long War", centre="0404", radius=3)
    sector = generate_universe_sector(universe, "S", width=8, height=10)
    affected = [h for h in universe.anomalies[0].hexes if h in sector.systems]
    assert affected
    for hex_coord in affected:
        system = sector.systems[hex_coord]
        assert system.mainworld.uwp.starport != 'A'
        assert system.travel_zone in ('A', 'R')


def test_plague_and_hazardous_jump_raise_travel_zones():
    for kind in ('plague', 'hazardous_jump'):
        random.seed(5)
        universe = create_universe("T", preset='charted_space')
        universe.add_anomaly(kind, kind, centre="0404", radius=3)
        sector = generate_universe_sector(universe, "S", width=8, height=10)
        affected = [h for h in universe.anomalies[0].hexes
                    if h in sector.systems]
        assert affected
        for hex_coord in affected:
            assert sector.systems[hex_coord].travel_zone in ('A', 'R')


def test_anomalies_outside_the_sector_are_harmless():
    """An anomaly whose hexes fall outside the generated region must leave
    every world alone."""
    universe = create_universe("T", preset='charted_space')
    universe.add_anomaly('supernova', "Far Away", centre="3030", radius=2)
    sector = generate_universe_sector(universe, "S", width=8, height=10)
    assert sector.systems
    for system in sector.systems.values():
        notes = " ".join(system.mainworld.notes) if system.mainworld else ""
        assert "Far Away" not in notes


# -------------------------------------------------------------- timeline

def test_timeline_is_ordered_and_anchored_to_the_current_year():
    universe = create_universe("T", preset='charted_space', current_year=1105)
    timeline = build_default_timeline(universe)
    assert timeline
    years = [e.year for e in timeline]
    assert years == sorted(years)
    assert all(e.year <= 1105 for e in timeline)


def test_timeline_reflects_the_trajectory():
    collapse = create_universe("T", trajectory='collapse')
    build_default_timeline(collapse)
    assert any('starflight is lost' in e.event for e in collapse.timeline)

    recovery = create_universe("T", trajectory='recovery')
    build_default_timeline(recovery)
    assert any('rediscovered' in e.event for e in recovery.timeline)


def test_timeline_records_anomaly_events():
    universe = create_universe("T", preset='charted_space')
    universe.add_anomaly('supernova', "Kellerman's Star", hexes=["0101"])
    build_default_timeline(universe)
    assert any("Kellerman's Star" in e.event for e in universe.timeline)


def test_add_event_keeps_order():
    universe = create_universe("T")
    universe.add_event(1105, "Now")
    universe.add_event(-2000, "Long ago")
    universe.add_event(500, "Midway")
    assert [e.year for e in universe.timeline] == [-2000, 500, 1105]


# ------------------------------------------------------------- reporting

def test_describe_covers_every_choice():
    universe = create_universe("Foreven Reach", preset='frontier')
    universe.add_anomaly('barren', "The Quiet Zone", centre="0404", radius=1)
    build_default_timeline(universe)
    text = universe.describe()
    assert "# Foreven Reach" in text
    for expected in ("Theme", "Star density", "Maximum Tech Level",
                     "Trajectory", "Native sophonts", "Interstellar polities",
                     "Background", "Anomalies", "Timeline",
                     "The Quiet Zone"):
        assert expected in text, expected


# ------------------------------------------------------ end-to-end effects

def test_tech_ceiling_holds_across_the_sector():
    universe = create_universe("Low Tech", preset='charted_space',
                               technology='early')
    sector = generate_universe_sector(universe, "S", width=8, height=10)
    worlds = [s.mainworld for s in sector.systems.values() if s.mainworld]
    assert worlds
    for mainworld in worlds:
        assert Utils.from_eHex(mainworld.uwp.tech_level) <= 9


def test_polity_count_is_respected():
    universe = create_universe("T", preset='charted_space', polity_count=2)
    sector = generate_universe_sector(universe, "S", width=16, height=20)
    assert len(sector.polities) <= 2


def test_density_setting_changes_system_count():
    random.seed(17)
    sparse = generate_universe_sector(
        create_universe("Sparse", preset='charted_space', density='sparse'),
        "S", width=8, height=10)
    random.seed(17)
    dense = generate_universe_sector(
        create_universe("Dense", preset='charted_space', density='dense'),
        "S", width=8, height=10)
    assert len(sparse.systems) < len(dense.systems)


def test_generated_sector_still_exports():
    """A universe-driven sector must work with the rest of the package."""
    universe = create_universe("Export", preset='frontier')
    universe.add_anomaly('barren', "Quiet", centre="0404", radius=1)
    sector = generate_universe_sector(universe, "S", width=8, height=10)
    text = wm.export_sector_sec_file(sector)
    rows = wm.parse_t5_column(text)
    assert len(rows) == sum(1 for s in sector.systems.values()
                            if s.mainworld is not None)
    svg = wm.generate_subsector_svg(sector, "S")
    assert svg.startswith("<svg") and svg.endswith("</svg>")
