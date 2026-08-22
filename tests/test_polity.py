"""Tests for procedural polity generation (SCG pp.40-49)."""
import random

import pytest

import worldmaker as wm
from worldmaker.classes import Sector
from worldmaker.polity import (
    _allegiance_code,
    _jump_range_for_tech,
    _polity_type_for,
    define_foreven_polities,
    generate_polities,
)
from worldmaker.sector import hex_distance
from worldmaker.utils import Utils


@pytest.fixture(scope="module")
def sectors():
    out = []
    for seed in (1105, 7, 99):
        random.seed(seed)
        out.append(wm.generate_full_sector(f"Reach{seed}"))
    return out


# --------------------------------------------------------------- helpers

def test_jump_range_follows_tech_level():
    """SCG p.41: TL9-10 reaches jump-1, TL11 jump-2, TL12+ jump-3, TL15+ 4."""
    assert _jump_range_for_tech(8) == 0
    assert _jump_range_for_tech(9) == 1
    assert _jump_range_for_tech(10) == 1
    assert _jump_range_for_tech(11) == 2
    assert _jump_range_for_tech(12) == 3
    assert _jump_range_for_tech(14) == 3
    assert _jump_range_for_tech(15) == 4


def test_polity_type_scales_with_size():
    assert _polity_type_for(11, 1, False) == "Single-System State"
    assert _polity_type_for(11, 5, False) == "Pocket Empire"
    assert _polity_type_for(11, 20, False) == "Interstellar State"
    assert _polity_type_for(13, 40, False) == "Interstellar Empire"
    assert _polity_type_for(9, 3, True) == "Major Race Polity"


def test_allegiance_codes_are_unique_two_char():
    used = set()
    codes = [_allegiance_code(n, used) for n in
             ("Aslan", "Avalar", "Aardvark", "Aaa", "Aa")]
    assert all(len(c) == 2 for c in codes)
    assert len(set(codes)) == len(codes)


# ------------------------------------------------------------- structure

def test_polities_are_generated(sectors):
    for sec in sectors:
        assert sec.polities, "no polities generated"
        assert 1 <= len(sec.polities) <= 5


def test_capitals_are_real_capable_worlds(sectors):
    """A capital must be an inhabited world with jump capability."""
    for sec in sectors:
        for p in sec.polities:
            assert p.capital_hex in sec.systems
            mw = sec.systems[p.capital_hex].mainworld
            assert mw is not None
            assert Utils.from_eHex(mw.uwp.tech_level) >= 9, (
                f"{p.name} capital is TL{mw.uwp.tech_level}, below jump drive")


def test_capitals_are_separated(sectors):
    """Capitals must be far enough apart to have distinct spheres."""
    for sec in sectors:
        caps = [p.capital_hex for p in sec.polities]
        for i in range(len(caps)):
            for j in range(i + 1, len(caps)):
                assert hex_distance(caps[i], caps[j]) >= 4


def test_territory_does_not_overlap(sectors):
    for sec in sectors:
        claimed = [h for p in sec.polities for h in p.controlled_systems]
        assert len(claimed) == len(set(claimed)), "two polities claim one system"


def test_capital_is_inside_own_territory(sectors):
    for sec in sectors:
        for p in sec.polities:
            assert p.capital_hex in p.controlled_systems


def test_territory_is_contiguous_within_jump_range(sectors):
    """Expansion follows jump links, so every claimed system must be within
    the polity's jump range of another of its systems."""
    for sec in sectors:
        for p in sec.polities:
            if len(p.controlled_systems) < 2:
                continue
            mw = sec.systems[p.capital_hex].mainworld
            jump = _jump_range_for_tech(Utils.from_eHex(mw.uwp.tech_level))
            owned = set(p.controlled_systems)
            for h in p.controlled_systems:
                if h == p.capital_hex:
                    continue
                assert any(0 < hex_distance(h, other) <= jump
                           for other in owned if other != h), (
                    f"{p.name}: {h} is beyond jump-{jump} of any other holding")


def test_allegiance_recorded_on_systems(sectors):
    for sec in sectors:
        for p in sec.polities:
            for h in p.controlled_systems:
                assert sec.systems[h].allegiance == p.allegiance_code


def test_independent_space_remains(sectors):
    """A sector should not be wholly carved up; the SCG's own example leaves
    substantial unaligned space."""
    for sec in sectors:
        claimed = sum(len(p.controlled_systems) for p in sec.polities)
        fraction = claimed / len(sec.systems)
        assert 0.05 < fraction < 0.85, f"{fraction:.0%} of the sector claimed"


def test_defence_index_in_range(sectors):
    all_polities = [p for sec in sectors for p in sec.polities]
    assert all_polities
    for p in all_polities:
        assert 1 <= p.defense_index <= 12


def test_defence_index_rises_with_territory_all_else_equal(sectors):
    """Defence index is jump range plus industry plus size, so size alone
    does not order two polities - a small high-technology state can outrank
    a large backward one. What must hold is that among polities whose
    capitals share a Tech Level, and so a jump range, more territory never
    means a lower index."""
    from worldmaker.utils import Utils

    by_tech = {}
    for sec in sectors:
        for p in sec.polities:
            capital = sec.systems.get(p.capital_hex)
            if capital is None or capital.mainworld is None:
                continue
            tech = Utils.from_eHex(capital.mainworld.uwp.tech_level)
            by_tech.setdefault(tech, []).append(
                (len(p.controlled_systems), p.defense_index))

    compared = 0
    for tech, entries in by_tech.items():
        entries.sort()
        for (size_a, index_a), (size_b, index_b) in zip(entries, entries[1:]):
            if size_a == size_b:
                continue
            compared += 1
            assert index_b >= index_a, (
                f"at TL{tech}, {size_b} worlds scored {index_b} but "
                f"{size_a} worlds scored {index_a}")
    assert compared > 0, "no comparable polities in the sample"


def test_polity_names_and_codes_unique(sectors):
    for sec in sectors:
        names = [p.name for p in sec.polities]
        codes = [p.allegiance_code for p in sec.polities]
        assert len(set(names)) == len(names)
        assert len(set(codes)) == len(codes)


def test_polity_sizes_vary(sectors):
    """Ambition varies, so a sector should not produce identical-sized states."""
    sizes = [len(p.controlled_systems) for sec in sectors for p in sec.polities]
    assert len(set(sizes)) > 3, f"polity sizes barely vary: {sorted(sizes)}"


def test_empty_sector_yields_no_polities():
    sec = Sector(name="Void", width=8, height=10)
    generate_polities(sec)
    assert sec.polities == []


def test_foreven_layout_still_available():
    """The canonical SCG example layout is retained for reproducibility."""
    random.seed(5)
    sec = wm.generate_full_sector("Foreven")
    define_foreven_polities(sec)
    codes = {p.allegiance_code for p in sec.polities}
    assert codes == {"Zh", "Av", "Im"}
    assert any(p.name == "Third Imperium" for p in sec.polities)
