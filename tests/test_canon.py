"""Tests for the canonical sector overlay.

These never touch the network: the fixture below reproduces the shape of
travellermap.com's T5 tab data, including the placeholder rows a Referee's
reserve is mostly made of.
"""
import random

import pytest

import worldmaker as wm
from worldmaker.canon import (
    ALLEGIANCE_NAMES,
    NON_ALIGNED_CODES,
    SCG_FOREVEN,
    CanonicalSector,
    CanonicalWorld,
    _bases_from_codes,
    _split_stellar,
    apply_canon,
    apply_canonical_world,
    canonical_polities,
    establish_canon_polities,
    expand_polity_from_capital,
    merge_canon,
    parse_travellermap_tab,
    scg_foreven,
)
from worldmaker.stellar import build_star_from_type
from worldmaker.utils import Utils

# Same columns and conventions as travellermap's Foreven data: a named world
# with a full profile, a client state, an independent world, and the
# placeholder rows that make up most of a reserve sector.
FIXTURE = "\t".join([
    "Sector", "SS", "Hex", "Name", "UWP", "Bases", "Remarks", "Zone", "PBG",
    "Allegiance", "Stars", "{Ix}", "(Ex)", "[Cx]", "Nobility", "W", "RU"]) + "\n" + "\n".join([
    "\t".join(["Test", "A", "0101", "Zdovesil", "A65588A-9", "KM", "Cp", "",
               "103", "ZhIN", "M1 V M3 V", "", "", "", "", "", ""]),
    "\t".join(["Test", "A", "0102", "", "???????-?", "", "", "", "???",
               "ZhIN", "", "", "", "", "", "", ""]),
    "\t".join(["Test", "A", "0103", "", "???????-?", "", "", "", "???",
               "ZhIN", "", "", "", "", "", "", ""]),
    "\t".join(["Test", "A", "0204", "Hollis", "A370642-C", "NS", "De Ni", "A",
               "303", "CsIm", "M3 V", "", "", "", "", "", ""]),
    "\t".join(["Test", "A", "0305", "Alenzar", "C000414-9", "", "As Ni", "",
               "513", "CsIm", "M0 III", "", "", "", "", "", ""]),
    "\t".join(["Test", "A", "0406", "Freehold", "C694655-8", "", "Ag Ni", "",
               "006", "Na", "G2 V", "", "", "", "", "", ""]),
    "\t".join(["Test", "A", "0507", "", "???????-?", "", "", "", "???",
               "XXXX", "", "", "", "", "", "", ""]),
    "\t".join(["Test", "A", "0608", "", "???????-?", "", "", "", "???",
               "XXXX", "", "", "", "", "", "", ""]),
])


@pytest.fixture(scope="module")
def canon():
    return parse_travellermap_tab(FIXTURE, name="Test", source="fixture")


@pytest.fixture
def sector(canon):
    random.seed(4242)
    return wm.generate_full_sector("Test", width=8, height=10, canon=canon)


# ---------------------------------------------------------------- parsing

def test_parses_every_row(canon):
    assert len(canon.worlds) == 8
    assert canon.name == "Test"
    assert set(canon.hexes) == {"0101", "0102", "0103", "0204", "0305",
                                "0406", "0507", "0608"}


def test_established_world_fields(canon):
    world = canon.worlds["0101"]
    assert world.name == "Zdovesil"
    assert world.uwp == "A65588A-9"
    assert world.bases == "KM"
    assert world.trade_codes == ["Cp"]
    assert world.allegiance == "ZhIN"
    assert world.stars == "M1 V M3 V"
    assert world.has_uwp and world.has_name and world.has_allegiance


def test_placeholders_recognised(canon):
    blank = canon.worlds["0507"]
    assert not blank.has_uwp        # ???????-?
    assert not blank.has_name
    assert not blank.has_allegiance  # XXXX
    assert not blank.has_pbg         # ???
    # A reserve fixes the position even when nothing else is known
    assert blank.hex == "0507"


def test_pbg_decoded(canon):
    world = canon.worlds["0305"]     # PBG 513
    assert world.has_pbg
    assert world.population_digit == 5
    assert world.planetoid_belts == 1
    assert world.gas_giants == 3


def test_allegiance_groups_exclude_unclaimed(canon):
    groups = canon.allegiance_groups()
    assert groups["ZhIN"] == ["0101", "0102", "0103"]
    assert groups["CsIm"] == ["0204", "0305"]
    assert groups["Na"] == ["0406"]
    assert "XXXX" not in groups


def test_summary_reports_the_split(canon):
    text = canon.summary()
    assert "8 canonical systems" in text
    assert "Zhodani Consulate" in text
    assert "named worlds: 4" in text


def test_rejects_data_without_a_hex_column():
    with pytest.raises(ValueError):
        parse_travellermap_tab("Name\tUWP\nfoo\tA000000-0")


def test_empty_input_is_harmless():
    empty = parse_travellermap_tab("")
    assert empty.worlds == {}


# ----------------------------------------------------------------- merge

def test_merge_overlay_fills_gaps_without_losing_positions(canon):
    overlay = CanonicalSector(name="Guide")
    overlay.worlds["0102"] = CanonicalWorld(hex="0102", name="Tlebria",
                                            allegiance="ZhIN",
                                            source="guide p.6")
    overlay.worlds["0909"] = CanonicalWorld(hex="0909", name="Extra")
    merged = merge_canon(canon, overlay)

    assert len(merged.worlds) == 9              # the overlay adds a system
    assert merged.worlds["0102"].name == "Tlebria"
    assert merged.worlds["0102"].source == "guide p.6"
    # Base data the overlay leaves blank survives
    assert merged.worlds["0101"].uwp == "A65588A-9"
    # The original is untouched
    assert "0909" not in canon.worlds
    assert canon.worlds["0102"].name == ""


def test_merge_does_not_let_placeholders_overwrite(canon):
    overlay = CanonicalSector(name="Guide")
    overlay.worlds["0101"] = CanonicalWorld(hex="0101", uwp="???????-?",
                                            name="")
    merged = merge_canon(canon, overlay)
    assert merged.worlds["0101"].uwp == "A65588A-9"
    assert merged.worlds["0101"].name == "Zdovesil"


# ------------------------------------------------------- the guide's tier

def test_scg_foreven_tier_is_cited():
    tier = scg_foreven()
    assert len(tier.worlds) == len(SCG_FOREVEN)
    for world in tier.worlds.values():
        assert world.source, f"{world.name} has no citation"
    names = {w.name for w in tier.worlds.values()}
    assert {"Zdovesil", "Tlebria", "Hollis", "Alenzar", "Raschev",
            "Avalar", "Parthinia"} == names


def test_double_adventure_worlds_are_recorded():
    """Alenzar and Raschev come from Double Adventure 5."""
    tier = scg_foreven()
    for hex_coord in ("3229", "3230"):
        assert "Double Adventure 5" in tier.worlds[hex_coord].source


def test_parthinia_is_independent():
    """The Guide describes Parthinia as an independent world."""
    assert scg_foreven().worlds["3018"].allegiance == "Na"


# -------------------------------------------------------------- polities

def test_canonical_polities_from_allegiance(canon):
    polities = canonical_polities(canon)
    codes = {p.allegiance_code for p in polities}
    assert codes == {"ZhIN", "CsIm"}       # Na is not a state
    zhodani = next(p for p in polities if p.allegiance_code == "ZhIN")
    assert zhodani.name == "Zhodani Consulate"
    assert zhodani.controlled_systems == ["0101", "0102", "0103"]
    assert zhodani.capital_hex == "0101"   # the Cp trade code


def test_client_states_get_no_capital(canon):
    clients = next(p for p in canonical_polities(canon)
                   if p.allegiance_code == "CsIm")
    assert clients.capital_hex == ""
    assert clients.polity_type == "Client States"


def test_non_aligned_never_becomes_a_polity(canon):
    assert all(p.allegiance_code not in NON_ALIGNED_CODES
               for p in canonical_polities(canon))
    assert "Na" in NON_ALIGNED_CODES


def test_unknown_allegiance_code_still_yields_a_polity():
    canon = CanonicalSector(name="X")
    canon.worlds["0101"] = CanonicalWorld(hex="0101", allegiance="Qq")
    polity = canonical_polities(canon)[0]
    assert polity.allegiance_code == "Qq"
    assert polity.name == "Qq"             # falls back to the code


# ---------------------------------------------------------- applying it

def test_generation_places_systems_exactly_at_canonical_hexes(sector, canon):
    assert set(sector.systems) == set(canon.hexes)


def test_canonical_uwps_are_not_overwritten(sector, canon):
    for world in canon.established_worlds():
        assert str(sector.systems[world.hex].mainworld.uwp) == world.uwp


def test_canonical_names_and_bases_applied(sector):
    assert sector.systems["0101"].mainworld.name == "Zdovesil"
    assert set(sector.systems["0204"].bases) == {"Naval", "Scout"}
    # A fully profiled world with a blank Bases column has no bases
    assert sector.systems["0305"].bases == []


def test_canonical_zone_and_allegiance_applied(sector):
    assert sector.systems["0204"].travel_zone == "A"
    assert sector.systems["0101"].allegiance == "ZhIN"
    assert sector.systems["0406"].allegiance == "Na"


def test_canonical_stars_rebuilt(sector):
    stars = [s.spectral_type for s in sector.systems["0101"].stars]
    assert stars == ["M1 V", "M3 V"]
    assert sector.systems["0305"].stars[0].spectral_type == "M0 III"
    # The rebuilt star carries real physical values, not placeholders
    primary = sector.systems["0101"].primary_star
    assert primary.mass > 0 and primary.luminosity > 0 and primary.hzco > 0


def test_canonical_pbg_applied(sector):
    system = sector.systems["0305"]        # PBG 513
    assert system.planetoid_belt_count == 1
    assert system.gas_giant_count == 3
    assert system.mainworld.population_digit == 5


def test_worlds_carry_their_citation(sector):
    notes = " ".join(sector.systems["0101"].mainworld.notes)
    assert "Canonical world" in notes


def test_procedural_polities_never_claim_canonical_space(sector, canon):
    reserved = {h for h, w in canon.worlds.items() if w.has_allegiance}
    for polity in sector.polities:
        if polity.allegiance_code in ("ZhIN", "CsIm"):
            continue
        assert not (set(polity.controlled_systems) & reserved)


def test_no_two_polities_claim_the_same_world(sector):
    seen = {}
    for polity in sector.polities:
        for hex_coord in polity.controlled_systems:
            assert hex_coord not in seen, (
                f"{hex_coord} claimed by {seen.get(hex_coord)} and "
                f"{polity.allegiance_code}")
            seen[hex_coord] = polity.allegiance_code


def test_polity_territory_matches_system_allegiance(sector):
    for polity in sector.polities:
        for hex_coord in polity.controlled_systems:
            assert sector.systems[hex_coord].allegiance == polity.allegiance_code


# ------------------------------------------------------------------ modes

def test_seed_mode_keeps_positions_and_borders_but_regenerates_worlds(canon):
    random.seed(11)
    sector = wm.generate_full_sector("Test", width=8, height=10, canon=canon,
                                     canon_mode='seed')
    assert set(sector.systems) == set(canon.hexes)
    assert sector.systems["0101"].allegiance == "ZhIN"
    # The world itself is the Referee's to invent
    generated = [str(sector.systems[w.hex].mainworld.uwp) != w.uwp
                 for w in canon.established_worlds()]
    assert any(generated), "seed mode should not pin UWPs"


def test_positions_mode_keeps_only_the_star_placements(canon):
    random.seed(12)
    sector = wm.generate_full_sector("Test", width=8, height=10, canon=canon,
                                     canon_mode='positions')
    assert set(sector.systems) == set(canon.hexes)
    assert not any(p.allegiance_code == "ZhIN" for p in sector.polities)


def test_unknown_mode_is_rejected(canon):
    sector = wm.generate_sector(4, 4)
    with pytest.raises(ValueError):
        apply_canon(sector, canon, mode='invent')


# --------------------------------------------------------------- helpers

def test_base_codes_map_to_names():
    assert _bases_from_codes("NS") == ["Naval", "Scout"]
    assert _bases_from_codes("") == []
    assert "Military" in _bases_from_codes("KM")
    # Legacy single-letter A means naval and scout together
    assert set(_bases_from_codes("A")) == {"Naval", "Scout"}


def test_stellar_string_splits_into_stars():
    assert _split_stellar("M1 V M3 V") == ["M1 V", "M3 V"]
    assert _split_stellar("G2 V") == ["G2 V"]
    assert _split_stellar("F7 V BD M3 V") == ["F7 V BD", "M3 V"]
    assert _split_stellar("") == []


def test_build_star_from_type_covers_the_real_classes():
    for spectral in ("M1 V", "K9 V", "G2 V", "F7 V", "M0 III", "D", "BD"):
        star = build_star_from_type("A", spectral)
        assert star is not None, spectral
        assert star.mass > 0, spectral
        assert star.luminosity > 0, spectral
    assert build_star_from_type("A", "not a star") is None
    assert build_star_from_type("A", "") is None


def test_hotter_stars_are_more_luminous():
    cool = build_star_from_type("A", "M5 V")
    warm = build_star_from_type("A", "G2 V")
    assert warm.luminosity > cool.luminosity
    assert warm.hzco > cool.hzco


def test_apply_canonical_world_leaves_a_system_without_a_mainworld_alone():
    from worldmaker.classes import StellarSystem
    system = StellarSystem(name="Empty")
    apply_canonical_world(system, CanonicalWorld(hex="0101", name="Nowhere"))
    assert system.name == "Empty"


# ------------------------------------------------------------- expansion

def test_expand_polity_from_capital_grows_into_free_space(canon):
    random.seed(5)
    sector = wm.generate_full_sector("Test", width=8, height=10, canon=canon)
    from worldmaker.classes import Polity
    small = Polity(name="Avalar Consulate", allegiance_code="Av",
                   capital_hex="0406", controlled_systems=["0406"])
    sector.polities.append(small)
    expand_polity_from_capital(sector, small, jump=2, budget=4)
    assert len(small.controlled_systems) > 1
    # It must not have taken anything another polity holds
    others = {h for p in sector.polities if p is not small
              for h in p.controlled_systems}
    assert not (set(small.controlled_systems) & others)


def test_expansion_without_a_capital_is_a_no_op(canon):
    random.seed(6)
    sector = wm.generate_full_sector("Test", width=8, height=10, canon=canon)
    from worldmaker.classes import Polity
    orphan = Polity(name="Nowhere", allegiance_code="Nw", capital_hex="")
    expand_polity_from_capital(sector, orphan)
    assert orphan.controlled_systems == []


def test_canon_expand_reserves_before_procedural_polities(canon):
    random.seed(9)
    sector = wm.generate_full_sector("Test", width=8, height=10, canon=canon,
                                     canon_expand={'CsIm': 4})
    clients = next(p for p in sector.polities if p.allegiance_code == 'CsIm')
    assert len(clients.controlled_systems) >= 2
    seen = set()
    for polity in sector.polities:
        assert not (set(polity.controlled_systems) & seen)
        seen |= set(polity.controlled_systems)


# ---------------------------------------------------------- integration

def test_canonical_sector_still_exports_and_renders(sector):
    text = wm.export_sector_sec_file(sector)
    rows = wm.parse_t5_column(text)
    assert len(rows) == len(sector.systems)
    by_hex = {r['Hex']: r for r in rows}
    assert by_hex["0101"]["Name"] == "Zdovesil"
    assert by_hex["0101"]["UWP"] == "A65588A-9"
    assert by_hex["0101"]["A"] == "ZhIN"
    svg = wm.generate_subsector_svg(sector, "Test")
    assert svg.startswith("<svg") and svg.endswith("</svg>")


def test_canon_works_alongside_a_universe(canon):
    random.seed(13)
    universe = wm.create_universe("Test", preset='frontier')
    sector = wm.generate_full_sector("Test", width=8, height=10,
                                     universe=universe, canon=canon)
    # Canon fixes the positions; the universe still caps technology
    assert set(sector.systems) == set(canon.hexes)
    for hex_coord, system in sector.systems.items():
        if hex_coord in {w.hex for w in canon.established_worlds()}:
            continue     # canonical worlds keep their own Tech Level
        assert Utils.from_eHex(system.mainworld.uwp.tech_level) <= \
            universe.max_tech_level
