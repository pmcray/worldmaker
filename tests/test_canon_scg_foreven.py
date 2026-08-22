"""Tests for the Sector Construction Guide's full worked Foreven.

These are hermetic: they exercise the tier's own data and apply it to a small
generated sector built from the tier itself, so nothing here needs the
travellermap cache.
"""
import random

import pytest

import worldmaker as wm
from worldmaker.canon import (
    SCG_AVALAR,
    SCG_BARREN,
    SCG_FOREVEN_FULL,
    SCG_FOREVEN_TECH_CEILINGS,
    SCG_IMPERIAL_CAGE,
    SCG_NATIVE_SOPHONTS,
    SCG_SCATTERED_SETTLEMENTS,
    SCG_TLESHO_UNION,
    SCG_ZHODANI_WAYPOINTS,
    CanonicalSector,
    CanonicalWorld,
    _raise_starport,
    _survey_designation,
    apply_canonical_world,
    canonical_polities,
    merge_canon,
    place_canonical_sophonts,
    scg_foreven,
    scg_foreven_full,
)
from worldmaker.classes import PlanetaryBody, Star, StellarSystem, UWP
from worldmaker.utils import Utils


@pytest.fixture(scope="module")
def full():
    return scg_foreven_full()


def _system(uwp="C567777-8", name="Generated"):
    """A minimal system whose mainworld canon can be applied to."""
    system = StellarSystem(name=name)
    system.stars.append(Star(designation="A", spectral_type="G2 V",
                             mass=1.0, luminosity=1.0, hzco=3.0))
    world = PlanetaryBody(name=name, parent_star_group="A",
                          body_type="Terrestrial", is_mainworld=True,
                          size_code=uwp[1], atmosphere_code=uwp[2],
                          hydrographics_code=uwp[3],
                          uwp=UWP(starport=uwp[0], size=uwp[1],
                                  atmosphere=uwp[2], hydrographics=uwp[3],
                                  population=uwp[4], government=uwp[5],
                                  law_level=uwp[6], tech_level=uwp[8]))
    system.stars[0].orbiting_bodies.append(world)
    return system, world


# ------------------------------------------------------------- the data

def test_the_full_tier_layers_over_the_reserve_tier(full):
    """Nothing the reserve documentation establishes is lost."""
    for hex_coord, world in scg_foreven().worlds.items():
        merged = full.worlds[hex_coord]
        assert merged.name == world.name
        if world.has_uwp:
            assert merged.uwp == world.uwp


def test_every_entry_carries_a_citation(full):
    for world in full.worlds.values():
        assert world.source, f"{world.hex} has no citation"
        assert "SCG" in world.source or "travellermap" in world.source


def test_the_avalar_consulate_has_its_twenty_seven_systems(full):
    """"After determining the border, the Avalar Consulate consists of 27
    systems" (SCG p.45)."""
    avalar = [w for w in full.worlds.values() if w.allegiance == "Av"]
    assert len(avalar) == 27
    assert len(SCG_AVALAR) == 27
    for world in avalar:
        assert world.has_uwp and world.has_name


def test_avalar_is_the_consulates_capital(full):
    polities = canonical_polities(full)
    consulate = next(p for p in polities if p.allegiance_code == "Av")
    assert consulate.name == "Avalar Consulate"
    assert consulate.capital_hex == "1636"
    assert full.worlds["1636"].uwp == "A75599C-C"


def test_the_consulate_holds_nine_billion_of_its_ten_point_seven(full):
    """"the total population of these systems is 10.7 billion, of which 9
    billion reside on Avalar itself" (SCG p.45). The UWP's Population digit
    is an order of magnitude, so this checks the shape of the claim: Avalar
    is a whole order of magnitude above every other world it rules."""
    populations = {w.hex: Utils.from_eHex(w.uwp[4])
                   for w in full.worlds.values() if w.allegiance == "Av"}
    assert populations["1636"] == 9
    others = [p for h, p in populations.items() if h != "1636"]
    assert max(others) <= 8


def test_the_tlesho_union_is_four_systems_of_one_species(full):
    hexes = {w.hex for w in SCG_TLESHO_UNION}
    assert hexes == {"0720", "0819", "0820", "0919"}
    for world in SCG_TLESHO_UNION:
        assert world.allegiance == "TlU"
        assert world.sophont == "Tlinzha"
        assert world.zone == "A"        # they fire on unauthorised visitors
        assert Utils.from_eHex(world.uwp[8]) == 10
    # Only the homeworld evolved them
    homeworlds = [w for w in SCG_TLESHO_UNION if not w.sophont_transplanted]
    assert [w.hex for w in homeworlds] == ["0720"]


def test_tlesho_carries_the_class_a_upgrade_and_its_stars(full):
    """The world table prints B998844-A; the narrative upgrades the starport
    to Class A to support a starfaring minor race (SCG p.25)."""
    tlesho = full.worlds["0720"]
    assert tlesho.uwp == "A998844-A"
    assert tlesho.physical_profile == "998"
    assert tlesho.stars == "F5 V M3 V"       # an M3 dwarf orbiting an F5


def test_native_sophont_worlds_and_ancients_ruins_are_separated(full):
    natives = [w for w in SCG_NATIVE_SOPHONTS if not w.ruins]
    ruins = [w for w in SCG_NATIVE_SOPHONTS if w.ruins]
    assert len(natives) == 7 and len(ruins) == 4
    for world in natives:
        assert world.sophont == "Native"
        assert not world.sophont_transplanted
    for world in ruins:
        assert world.barren and not world.has_sophont
    assert {w.hex for w in ruins} == {"1726", "2615", "2740", "3006"}


def test_physical_profiles_match_the_printed_uwps(full):
    """The guide prints a physical column and a UWP side by side. Every
    transcribed profile agrees with its UWP - including 2328, where the guide
    contradicts itself and the UWP is taken as the fact."""
    for world in full.worlds.values():
        if world.physical_profile and world.has_uwp:
            assert world.physical_profile == world.uwp[1:4], world.hex
    assert full.worlds["2328"].physical_profile == "87A"
    assert "755" in full.worlds["2328"].source      # the discrepancy is kept


def test_scattered_settlements_all_arrived_from_elsewhere(full):
    assert len(SCG_SCATTERED_SETTLEMENTS) == 10
    for world in SCG_SCATTERED_SETTLEMENTS:
        assert world.has_sophont
        assert world.sophont_transplanted, world.hex
    species = {w.sophont for w in SCG_SCATTERED_SETTLEMENTS}
    assert species == {"Chirper", "Aslan", "Minor Human", "Solomani",
                       "Droyne", "Vargr"}


def test_the_five_zhodani_red_zones(full):
    """"five Zhodani worlds could qualify as Red Zones, four to protect
    natives, the fifth to interdict a system with known Ancients
    artefacts" (SCG p.63)."""
    red = {h for h, w in full.worlds.items()
           if w.zone == "R" and w.allegiance == "ZhIN"}
    assert red == {"0103", "0214", "0408", "1303", "3006"}
    assert full.worlds["3006"].ruins        # the Ancients site


def test_the_barren_zone_is_fourteen_worlds(full):
    assert len(SCG_BARREN) == 14
    assert {w.hex for w in SCG_BARREN} == {
        "1124", "1224", "1325",                     # first cluster
        "1422", "1423", "1523", "1622",             # second cluster
        "0822", "1218", "1319", "1419",             # periphery
        "2209", "2309", "2310"}                     # inside the Consulate
    for world in SCG_BARREN:
        assert world.barren
        assert world.starport in ("X", "E")


def test_the_chokepoint_has_no_gas_giant(full):
    """1423 is "the only jump-2 link between the clusters" and has no gas
    giant, forcing an ocean refuelling (SCG p.8)."""
    assert full.worlds["1423"].gas_giant == "X"
    assert "ocean refuelling" in full.worlds["1423"].source


def test_the_two_garden_worlds_keep_a_landing_area(full):
    """Barren worlds get Class X, "except the garden worlds of 1224 and 1325,
    which will receive Class E" (SCG p.27)."""
    assert full.worlds["1224"].starport == "E"
    assert full.worlds["1325"].starport == "E"
    others = [w for w in SCG_BARREN if w.hex not in ("1224", "1325")]
    assert all(w.starport == "X" for w in others)


def test_route_waypoints_and_the_cage_annotate_rather_than_survey(full):
    """A "put a naval base here" entry never places a star of its own."""
    for world in SCG_ZHODANI_WAYPOINTS + SCG_IMPERIAL_CAGE:
        assert world.annotation_only
        assert world.starport_floor == "B"
        assert world.bases
        assert world.hex not in full.hexes
    assert {w.hex for w in SCG_ZHODANI_WAYPOINTS} == {
        "1102", "1701", "2602", "2802", "3201"}
    assert {w.hex for w in SCG_IMPERIAL_CAGE} == {"3135", "3228"}


def test_the_waypoint_discrepancy_is_recorded_not_resolved_silently(full):
    """The guide lists 2602 on p.27 and 2802 on p.63. Both are carried, and
    each says so."""
    assert "2802" in full.worlds["2602"].source
    assert "2602" in full.worlds["2802"].source


def test_an_annotation_stops_being_one_once_a_survey_places_a_star():
    """Merging a real survey row under the annotation establishes the hex."""
    survey = CanonicalSector(name="Foreven")
    survey.worlds["2602"] = CanonicalWorld(hex="2602", uwp="???????-?",
                                           allegiance="ZhIN", source="survey")
    merged = merge_canon(survey, scg_foreven_full())
    assert not merged.worlds["2602"].annotation_only
    assert "2602" in merged.hexes
    assert merged.worlds["2602"].starport_floor == "B"
    # and the hex the survey has no star at stays an annotation
    assert merged.worlds["2802"].annotation_only
    assert "2802" not in merged.hexes


def test_tech_level_ceilings_bind_by_polity(full):
    assert SCG_FOREVEN_TECH_CEILINGS == {"ZhIN": 14, "Av": 12}
    assert full.max_tech_level_for("1636") == 12      # Avalar
    assert full.max_tech_level_for("1212") == 14      # Zdovesil, Zhodani
    assert full.max_tech_level_for("0720") is None    # the Tlesho Union
    assert full.max_tech_level_for("9999") is None


def test_no_avalar_world_exceeds_its_consulates_ceiling(full):
    for world in SCG_AVALAR:
        assert Utils.from_eHex(world.uwp[8]) <= 12, world.name


def test_the_tier_does_not_claim_to_be_canon():
    assert "None of it is canon" in scg_foreven_full.__doc__


# --------------------------------------------------------------- applying

def test_a_physical_profile_reshapes_the_world_without_a_uwp():
    system, world = _system("C567777-8")
    apply_canonical_world(system, CanonicalWorld(hex="0101",
                                                 physical_profile="6A6"))
    assert (world.size_code, world.atmosphere_code,
            world.hydrographics_code) == ("6", "A", "6")
    assert world.uwp.atmosphere == "A"
    assert world.uwp.population == "7"      # society untouched


def test_barren_empties_the_whole_society():
    system, world = _system("B78A899-D")
    system.bases = ["Naval"]
    apply_canonical_world(system, CanonicalWorld(hex="0101", barren=True,
                                                 starport="X"))
    assert str(world.uwp).startswith("X78A000-0")
    assert world.total_population == 0
    assert system.bases == []
    assert "Ba" in world.trade_codes
    assert any("Barren" in n for n in world.notes)


def test_a_barren_world_gets_a_scout_service_designation():
    random.seed(11)
    system, world = _system("C567777-8")
    apply_canonical_world(system, CanonicalWorld(hex="0101", barren=True,
                                                 starport="X"))
    assert world.name == system.name
    profile, _, sequence = world.name.partition("-")
    assert profile == "567"
    assert sequence.isdigit() and len(sequence) == 3


def test_a_named_barren_world_keeps_its_name():
    system, world = _system("C567777-8")
    apply_canonical_world(system, CanonicalWorld(hex="0101", name="Ash",
                                                 barren=True, starport="X"))
    assert world.name == "Ash"


def test_a_garden_world_keeps_its_cleared_landing_area():
    system, world = _system("C567777-8")
    apply_canonical_world(system, CanonicalWorld(hex="0101", barren=True,
                                                 starport="E"))
    assert world.uwp.starport == "E"


def test_a_starport_floor_only_ever_raises():
    for before, after in (("X", "B"), ("E", "B"), ("C", "B"),
                          ("B", "B"), ("A", "A")):
        system, world = _system(f"{before}567777-8")
        apply_canonical_world(system, CanonicalWorld(hex="0101",
                                                     starport_floor="B"))
        assert world.uwp.starport == after, before


def test_an_unknown_floor_is_ignored():
    system, world = _system("C567777-8")
    _raise_starport(world, "Q")
    assert world.uwp.starport == "C"


def test_gas_giants_can_be_required_or_forbidden():
    system, _ = _system()
    apply_canonical_world(system, CanonicalWorld(hex="0101", gas_giant="G"))
    assert system.gas_giant_count >= 1
    apply_canonical_world(system, CanonicalWorld(hex="0101", gas_giant="X"))
    assert system.gas_giant_count == 0


def test_an_ancients_site_is_flagged_as_ruins():
    system, world = _system()
    apply_canonical_world(system, CanonicalWorld(hex="0101", ruins=True,
                                                 barren=True))
    assert world.extinct_sophont
    assert any("Ancients" in n for n in world.notes)


def test_climate_is_recorded():
    system, world = _system()
    apply_canonical_world(system, CanonicalWorld(hex="0101",
                                                 climate="Temperate"))
    assert any("Temperate" in n for n in world.notes)


def test_survey_designation_reads_off_the_profile():
    random.seed(3)
    _, world = _system("XA00000-0")
    assert _survey_designation(world).startswith("A00-")


# -------------------------------------------------------------- sophonts

def test_canonical_sophonts_are_placed_by_species():
    sector = wm.Sector(name="Foreven", width=32, height=40)
    placed = place_canonical_sophonts(sector, scg_foreven_full())
    assert placed == len(scg_foreven_full().sophont_worlds())
    assert sector.native_sophonts["0720"].name == "Tlinzha"
    assert sector.native_sophonts["0935"].name == "Droyne"
    assert sector.native_sophonts["0131"].name == "Aslan"
    assert sector.native_sophonts["1303"].name == "Chirper"


def test_an_unnamed_native_species_still_gets_rolled():
    """The guide records "Native" where it has not invented a name."""
    random.seed(9)
    sector = wm.Sector(name="Foreven", width=32, height=40)
    place_canonical_sophonts(sector, scg_foreven_full())
    native = sector.native_sophonts["1927"]
    assert native.name and native.name != "Native"
    assert not native.is_major
    assert native.morphology                 # rolled on the D66 table


def test_a_settlement_says_it_is_not_a_homeworld():
    sector = wm.Sector(name="Foreven", width=32, height=40)
    place_canonical_sophonts(sector, scg_foreven_full())
    assert "not their homeworld" in sector.native_sophonts["0104"].history_summary
    assert "not their homeworld" not in sector.native_sophonts["0720"].history_summary


def test_the_tlinzha_are_catalogued_rather_than_rolled():
    tlinzha = wm.get_catalogued_race("Tlinzha", "0720")
    assert not tlinzha.is_major
    assert "Octopod" in tlinzha.limb_count
    assert "Protocols" in tlinzha.history_summary


def test_an_uncatalogued_species_is_not_turned_into_a_human():
    """get_major_race falls back to Imperial Human; the catalogue lookup
    must not, or a published species would silently vanish."""
    assert wm.get_major_race("Ithklur", "0101").name == "Ithklur"
    assert wm.get_major_race("Ithklur", "0101").morphology.startswith("Bilateral (Vilani")
    unknown = wm.get_catalogued_race("Ithklur", "0101")
    assert unknown.name == "Ithklur"
    assert unknown.morphology == ""          # nothing invented
    assert "0101" in unknown.history_summary


# ------------------------------------------------------- generating with it

@pytest.fixture(scope="module")
def sector(full):
    random.seed(1105)
    return wm.generate_full_sector("Foreven", canon=full, canon_mode="pin")


def test_a_sector_generates_from_the_tier_alone(sector, full):
    assert set(sector.systems) == full.hexes
    # 78 entries, seven of which only annotate a system the survey places
    assert len(full.worlds) == 78
    assert len(sector.systems) == 71


def test_every_established_world_is_pinned(sector, full):
    for hex_coord, world in full.worlds.items():
        if not world.has_uwp or hex_coord not in sector.systems:
            continue
        assert str(sector.systems[hex_coord].mainworld.uwp) == world.uwp


def test_the_four_polities_are_established(sector):
    by_code = {p.allegiance_code: p for p in sector.polities}
    assert by_code["Av"].capital_hex == "1636"
    assert len(by_code["Av"].controlled_systems) == 27
    assert by_code["TlU"].capital_hex == "0720"
    assert len(by_code["TlU"].controlled_systems) == 4
    # The Zhodani route waypoints annotate systems this tier alone does not
    # place, so only the 13 hexes it does establish are held here.
    assert len(by_code["ZhIN"].controlled_systems) == 13


def test_barren_worlds_belong_to_nobody(sector, full):
    """A zone where colonies fail is not somebody's province."""
    for world in SCG_BARREN:
        system = sector.systems[world.hex]
        assert Utils.from_eHex(system.mainworld.uwp.population) == 0
        if world.allegiance:
            continue           # the three inside the Zhodani border
        assert system.allegiance in ("Na", "")
        assert not any(world.hex in p.controlled_systems
                       for p in sector.polities)


def test_the_tech_ceilings_hold_across_the_sector(sector, full):
    for hex_coord, system in sector.systems.items():
        ceiling = full.max_tech_level_for(hex_coord)
        if ceiling is None:
            continue
        assert Utils.from_eHex(system.mainworld.uwp.tech_level) <= ceiling


def test_the_sector_still_exports_and_renders(sector):
    assert wm.generate_sector_svg(sector).startswith("<svg")
    rows = wm.export_sector_t5_column(sector).splitlines()
    assert len(rows) >= len(sector.systems)
    frame = wm.create_sector_dataframe(sector)
    assert len(frame) == len(sector.systems)


def test_seed_mode_keeps_the_map_but_gives_the_worlds_back(full):
    random.seed(1105)
    sector = wm.generate_full_sector("Foreven", canon=full, canon_mode="seed")
    assert set(sector.systems) == full.hexes
    assert sector.systems["1636"].allegiance == "Av"
    # Nothing the guide invented about the worlds survives
    assert sector.systems["1636"].name != "Avalar"
    assert str(sector.systems["1636"].mainworld.uwp) != "A75599C-C"


def test_positions_mode_drops_the_sophonts_too(full):
    random.seed(1105)
    sector = wm.generate_full_sector("Foreven", canon=full,
                                     canon_mode="positions")
    assert set(sector.systems) == full.hexes
    assert "Tlinzha" not in {s.name for s in sector.native_sophonts.values()}
