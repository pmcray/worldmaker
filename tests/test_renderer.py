"""Tests for the classic 1981-style map renderers.

These guard the drawing layer: that each map convention actually reaches the
SVG, that geometry stays inside the canvas, and that the modern-style
artefacts the audit flagged (UWP strings in hexes, pastel allegiance fills)
have not come back.
"""
import math
import random
import re
import xml.etree.ElementTree as ET

import pytest

import worldmaker as wm
from worldmaker.sector import (
    _LEGEND_ITEMS,
    _legend_layout,
    generate_full_sector,
    generate_sector_svg,
    generate_subsector_svg,
    hex_distance,
    hex_neighbors,
    merge_subsectors,
)
from worldmaker.utils import Utils

SVG_NS = "{http://www.w3.org/2000/svg}"


@pytest.fixture(scope="module")
def sector():
    random.seed(1105)
    return generate_full_sector("Test Reach")


@pytest.fixture(scope="module")
def sector_svg(sector):
    return generate_sector_svg(sector)


@pytest.fixture(scope="module")
def subsector_svg(sector):
    return generate_subsector_svg(sector, "Subsector A")


# ------------------------------------------------------------ well-formedness

def test_both_scales_are_wellformed_svg(sector_svg, subsector_svg):
    for svg in (sector_svg, subsector_svg):
        root = ET.fromstring(svg)
        assert root.tag == f"{SVG_NS}svg"
        assert root.get("viewBox")


def test_content_fits_inside_viewbox(sector_svg, subsector_svg):
    """Nothing should be drawn outside the canvas - the old renderer let the
    bottom hex row overflow its frame."""
    for svg in (sector_svg, subsector_svg):
        root = ET.fromstring(svg)
        _, _, vb_w, vb_h = (float(v) for v in root.get("viewBox").split())
        ys, xs = [], []
        for poly in root.iter(f"{SVG_NS}polygon"):
            for pt in poly.get("points").split():
                px, py = (float(v) for v in pt.split(","))
                xs.append(px)
                ys.append(py)
        assert xs and ys
        assert min(xs) >= -0.5 and max(xs) <= vb_w + 0.5
        assert min(ys) >= -0.5 and max(ys) <= vb_h + 0.5

        # The legend box must also sit fully inside the canvas
        boxes = [r for r in root.iter(f"{SVG_NS}rect")
                 if "cm-legend-box" in (r.get("class") or "")]
        assert len(boxes) == 1
        box = boxes[0]
        bottom = float(box.get("y")) + float(box.get("height"))
        right = float(box.get("x")) + float(box.get("width"))
        assert bottom <= vb_h + 0.5, f"legend overflows canvas: {bottom} > {vb_h}"
        assert right <= vb_w + 0.5


def test_hex_count_matches_window(sector_svg, subsector_svg):
    sector_hexes = ET.fromstring(sector_svg).iter(f"{SVG_NS}polygon")
    assert sum(1 for _ in sector_hexes) == 32 * 40
    sub_hexes = ET.fromstring(subsector_svg).iter(f"{SVG_NS}polygon")
    assert sum(1 for _ in sub_hexes) == 8 * 10


def test_hexes_are_regular_and_flat_topped(subsector_svg):
    """Classic Traveller hexes are flat-topped with vertices at 0/60/.../300
    degrees; all six sides equal."""
    root = ET.fromstring(subsector_svg)
    poly = next(iter(root.iter(f"{SVG_NS}polygon")))
    pts = [tuple(float(v) for v in p.split(",")) for p in poly.get("points").split()]
    assert len(pts) == 6
    sides = [math.dist(pts[i], pts[(i + 1) % 6]) for i in range(6)]
    assert max(sides) - min(sides) < 0.15, f"irregular hex: {sides}"
    # A flat-topped hex has two vertices sharing the maximum x (the flat right
    # edge is vertical), i.e. width == 2R and height == sqrt(3)R
    width = max(p[0] for p in pts) - min(p[0] for p in pts)
    height = max(p[1] for p in pts) - min(p[1] for p in pts)
    assert abs(height / width - math.sqrt(3) / 2) < 0.02


# --------------------------------------------------------- classic conventions

def _is_legend(el):
    return "cm-legend-glyph" in (el.get("class") or "")


def _map_elements(svg, tag, cls):
    """Elements of the map itself, excluding the legend's sample glyphs.

    Classes are matched as whole tokens: 'cm-world' must not also pick up
    'cm-world-dry'."""
    root = ET.fromstring(svg)
    return [e for e in root.iter(f"{SVG_NS}{tag}")
            if cls in (e.get("class") or "").split() and not _is_legend(e)]


def _texts(svg, cls):
    root = ET.fromstring(svg)
    return [t.text for t in root.iter(f"{SVG_NS}text")
            if cls in (t.get("class") or "") and t.text
            and not _is_legend(t)]


def test_starport_letters_are_drawn(sector, subsector_svg):
    """The starport class letter is the most prominent glyph on classic maps."""
    ports = _texts(subsector_svg, "cm-port")
    assert ports, "no starport letters rendered"
    assert set(ports) <= set("ABCDEX"), f"unexpected starport codes: {set(ports)}"
    # Every system in the window must contribute exactly one letter
    in_window = [h for h, sy in sector.systems.items()
                 if int(h[:2]) <= 8 and int(h[2:]) <= 10
                 and sy.mainworld is not None]
    assert len(ports) == len(in_window)


def test_no_uwp_strings_in_hexes(sector_svg, subsector_svg):
    """The originals never printed UWPs on the map; the previous renderer did."""
    uwp_re = re.compile(r"[ABCDEX][0-9A-Z]{6}-[0-9A-Z]")
    for svg in (sector_svg, subsector_svg):
        hits = [t for t in ET.fromstring(svg).iter(f"{SVG_NS}text")
                if t.text and uwp_re.fullmatch(t.text.strip())]
        assert not hits, f"UWP strings rendered on map: {[h.text for h in hits][:3]}"


def test_no_pastel_allegiance_fills(sector_svg):
    """Hexes are unfilled black-ink outlines, not coloured allegiance blocks."""
    root = ET.fromstring(sector_svg)
    for poly in root.iter(f"{SVG_NS}polygon"):
        assert "hex-fill" not in (poly.get("class") or "")
        assert poly.get("fill") is None


def test_hex_numbers_on_every_hex(subsector_svg):
    nums = _texts(subsector_svg, "cm-hexnum")
    assert len(nums) == 80
    assert set(nums) == {f"{c:02d}{r:02d}" for c in range(1, 9) for r in range(1, 11)}


def test_wet_and_dry_world_glyphs_differ(sector, sector_svg):
    """Solid disc for worlds with free-standing water, open circle for dry.
    The counts must match the generated data exactly."""
    wet = _map_elements(sector_svg, "circle", "cm-world")
    dry = _map_elements(sector_svg, "circle", "cm-world-dry")
    exp_dry = sum(1 for s in sector.systems.values()
                  if s.mainworld is not None
                  and s.mainworld.uwp.size != '0'
                  and Utils.from_eHex(s.mainworld.uwp.hydrographics) == 0)
    exp_wet = sum(1 for s in sector.systems.values()
                  if s.mainworld is not None
                  and s.mainworld.uwp.size != '0'
                  and Utils.from_eHex(s.mainworld.uwp.hydrographics) > 0)
    assert len(dry) == exp_dry
    assert len(wet) == exp_wet
    assert wet, "no worlds rendered at all"


def test_dry_world_renders_as_open_circle():
    """A desert mainworld draws an open circle, not a filled disc. Built
    explicitly so the case does not depend on the sample."""
    from worldmaker.classes import PlanetaryBody, Sector, Star, StellarSystem, UWP

    sec = Sector(name="Dry Test", width=8, height=10)
    for hex_coord, hyd in (("0101", "0"), ("0202", "7")):
        system = StellarSystem(name=f"Sys{hex_coord}")
        star = Star(designation="A", spectral_type="G2 V", mass=1.0)
        body = PlanetaryBody(
            name="Testworld", body_type="Terrestrial", size_code="6",
            is_mainworld=True,
            uwp=UWP(starport="C", size="6", atmosphere="6", hydrographics=hyd,
                    population="4", government="2", law_level="3",
                    tech_level="9"),
        )
        star.orbiting_bodies.append(body)
        system.stars.append(star)
        sec.systems[hex_coord] = system

    svg = generate_subsector_svg(sec, "Dry Test")
    assert len(_map_elements(svg, "circle", "cm-world-dry")) == 1
    assert len(_map_elements(svg, "circle", "cm-world")) == 1


def test_belt_glyph_used_for_size_zero_mainworlds():
    """Asteroid-belt mainworlds get a scatter of dots, not an ordinary disc.

    Habitability-based selection (WBH p.133) rarely picks a vacuum belt, so
    the case is built explicitly rather than waited for."""
    from worldmaker.classes import PlanetaryBody, Sector, Star, StellarSystem, UWP

    sec = Sector(name="Belt Test", width=8, height=10)
    for hex_coord, size in (("0101", "0"), ("0202", "6")):
        system = StellarSystem(name=f"Sys{hex_coord}")
        star = Star(designation="A", spectral_type="G2 V", mass=1.0)
        body = PlanetaryBody(
            name="Testworld",
            body_type="Planetoid Belt" if size == "0" else "Terrestrial",
            size_code=size,
            is_mainworld=True,
            uwp=UWP(starport="C", size=size, atmosphere="0" if size == "0" else "6",
                    hydrographics="0" if size == "0" else "5",
                    population="4", government="2", law_level="3",
                    tech_level="9"),
        )
        star.orbiting_bodies.append(body)
        system.stars.append(star)
        sec.systems[hex_coord] = system

    svg = generate_subsector_svg(sec, "Belt Test")
    n_belt_dots = len(_map_elements(svg, "circle", "cm-belt"))
    assert n_belt_dots == 5, f"expected one 5-dot belt glyph, got {n_belt_dots}"
    # The Size 6 world is drawn as an ordinary disc, not a belt
    assert len(_map_elements(svg, "circle", "cm-world")) == 1


def test_gas_giant_marker_is_upper_right(sector, subsector_svg):
    """Classic maps put a small filled circle at the hex's upper right."""
    root = ET.fromstring(subsector_svg)
    ggs = _map_elements(subsector_svg, "circle", "cm-gg")
    expected = sum(1 for h, s in sector.systems.items()
                   if int(h[:2]) <= 8 and int(h[2:]) <= 10
                   and s.gas_giant_count > 0
                   and s.mainworld is not None)
    assert len(ggs) == expected
    # Confirm offset direction against the hex centres
    hexnums = {t.text: (float(t.get("x")), float(t.get("y")))
               for t in root.iter(f"{SVG_NS}text")
               if "cm-hexnum" in (t.get("class") or "")}
    assert hexnums
    for gg in ggs:
        gx, gy = float(gg.get("cx")), float(gg.get("cy"))
        # nearest hex-number label is above-centre of the same hex
        nx, ny = min(hexnums.values(), key=lambda p: math.dist(p, (gx, gy)))
        assert gx > nx, "gas giant marker is not right of hex centre"


def test_base_glyphs_match_generated_bases(sector, subsector_svg):
    naval = _texts(subsector_svg, "cm-base").count("★")
    scout = _texts(subsector_svg, "cm-base").count("▲")
    in_window = [s for h, s in sector.systems.items()
                 if int(h[:2]) <= 8 and int(h[2:]) <= 10
                 and s.mainworld is not None]
    exp_naval = sum(1 for s in in_window
                    if any(b in s.bases for b in ("Naval", "Zhodani Naval")))
    exp_scout = sum(1 for s in in_window if "Scout" in s.bases)
    assert naval == exp_naval
    assert scout == exp_scout


def test_travel_zone_rings_drawn(sector, sector_svg):
    amber = _map_elements(sector_svg, "circle", "cm-zone-amber")
    red = _map_elements(sector_svg, "circle", "cm-zone-red")
    exp_amber = sum(1 for s in sector.systems.values() if s.travel_zone == "A")
    exp_red = sum(1 for s in sector.systems.values() if s.travel_zone == "R")
    assert exp_amber > 0 and exp_red > 0, "generator produced no travel zones"
    assert len(amber) == exp_amber
    assert len(red) == exp_red
    # Amber is broken, Red is solid
    assert amber[0].get("stroke-dasharray")
    assert not red[0].get("stroke-dasharray")


def test_polity_borders_drawn_as_dashed_lines(sector, sector_svg):
    """Borders are dashed and chained into continuous polylines rather than
    drawn as one disconnected segment per hex edge."""
    borders = _map_elements(sector_svg, "polyline", "cm-border")
    assert borders, "no polity borders traced"
    assert all(b.get("stroke-dasharray") for b in borders)

    # Every segment of every chain runs along a hex edge, so all segments are
    # the same length (the hex radius).
    lengths = set()
    total_segments = 0
    for polyline in borders:
        pts = [tuple(float(v) for v in p.split(","))
               for p in polyline.get("points").split()]
        assert len(pts) >= 2
        for i in range(len(pts) - 1):
            lengths.add(round(math.dist(pts[i], pts[i + 1]), 1))
            total_segments += 1
    assert max(lengths) - min(lengths) < 0.2, (
        f"border segments vary in length: {sorted(lengths)}")

    # Chaining must actually reduce the element count well below the number
    # of segments drawn
    assert len(borders) < total_segments / 2, (
        f"{len(borders)} polylines for {total_segments} segments - "
        "edges are not being chained")


def test_border_edges_chain_into_paths():
    """_chain_edges links shared endpoints into the longest runs it can."""
    from worldmaker.sector import _chain_edges

    # A square traced as four separate edges should come back as one loop
    square = [((0.0, 0.0), (1.0, 0.0)), ((1.0, 0.0), (1.0, 1.0)),
              ((1.0, 1.0), (0.0, 1.0)), ((0.0, 1.0), (0.0, 0.0))]
    chains = _chain_edges(square)
    assert len(chains) == 1
    assert len(chains[0]) == 5          # four edges, closed back to the start

    # Two edges sharing no endpoint stay separate
    disjoint = [((5.0, 5.0), (6.0, 5.0)), ((9.0, 9.0), (9.0, 8.0))]
    assert len(_chain_edges(disjoint)) == 2

    # Every distinct input edge is represented exactly once
    chains = _chain_edges(square + disjoint)
    segments = sum(len(c) - 1 for c in chains)
    assert segments == len(square) + len(disjoint)

    # A repeated edge is drawn only once
    assert sum(len(c) - 1 for c in _chain_edges(square + square)) == len(square)


def test_xboat_routes_drawn_and_within_jump_range(sector, sector_svg):
    xboat = [r for r in sector.routes if r[2] == "xboat"]
    assert xboat, "no Xboat network generated"
    for h1, h2, _ in xboat:
        assert hex_distance(h1, h2) <= 4, f"{h1}-{h2} exceeds jump-4"
        for h in (h1, h2):
            mw = sector.systems[h].mainworld
            assert mw.uwp.starport in ("A", "B"), \
                f"Xboat stop {h} has starport {mw.uwp.starport}"
    drawn = _map_elements(sector_svg, "line", "cm-xboat")
    assert len(drawn) == len(xboat)


def test_xboat_network_is_acyclic_and_connects_hubs(sector):
    """Kruskal over jump-range edges: one link per merge, so edges < hubs."""
    hubs = {h for h, s in sector.systems.items()
            if s.mainworld is not None
            and s.mainworld.uwp.starport in ("A", "B")}
    xboat = [r for r in sector.routes if r[2] == "xboat"]
    assert len(xboat) < len(hubs), "Xboat network contains cycles"


def test_legend_lists_every_convention(sector_svg, subsector_svg):
    for svg in (sector_svg, subsector_svg):
        labels = " ".join(_texts(svg, "cm-legend-text"))
        for term in ("World", "Asteroid belt", "Gas giant", "Naval base",
                     "Scout base", "Amber zone", "Red zone", "Xboat route",
                     "Polity border"):
            assert term in labels, f"legend missing {term!r}"


def test_legend_reflows_to_fit_narrow_maps():
    """At subsector width the five-across layout overlapped its own labels."""
    font = 14.0
    wide_cols, _, _ = _legend_layout(1400, font)
    narrow_cols, narrow_rows, narrow_h = _legend_layout(360, font)
    assert wide_cols > narrow_cols
    assert narrow_cols * narrow_rows >= len(_LEGEND_ITEMS)
    assert 360 / narrow_cols >= font * 12, "legend cells too narrow for labels"


def test_subsector_grid_only_on_full_sector_maps(sector, sector_svg, subsector_svg):
    letters = set(_texts(sector_svg, "cm-sslabel"))
    assert letters == set("ABCDEFGHIJKLMNOP")
    assert not _texts(subsector_svg, "cm-sslabel")


# ------------------------------------------------------------------- windowing

def test_subsector_window_selects_correct_hexes(sector):
    """Subsector F is columns 9-16, rows 11-20 of the sector."""
    svg = generate_subsector_svg(sector, "Subsector F", origin_col=9, origin_row=11)
    nums = set(_texts(svg, "cm-hexnum"))
    assert nums == {f"{c:02d}{r:02d}"
                    for c in range(9, 17) for r in range(11, 21)}


def test_full_sector_is_coherent(sector):
    """Single-pass generation: unique names sector-wide and polities placed in
    sector coordinates (the old code re-tiled a subsector-scale polity block
    into all sixteen subsectors)."""
    names = [s.mainworld.name for s in sector.systems.values()
             if s.mainworld is not None]
    assert len(names) == len(set(names)), "duplicate mainworld names"
    assert sector.polities

    for polity in sector.polities:
        # Capital and territory must lie inside the sector
        assert polity.capital_hex in sector.systems
        for h in polity.controlled_systems:
            col, row = int(h[:2]), int(h[2:])
            assert 1 <= col <= sector.width and 1 <= row <= sector.height

    # Allegiance codes are unique and territory does not overlap
    codes = [p.allegiance_code for p in sector.polities]
    assert len(codes) == len(set(codes))
    all_claimed = [h for p in sector.polities for h in p.controlled_systems]
    assert len(all_claimed) == len(set(all_claimed)), "overlapping territory"

    # Every claimed system carries its polity's allegiance, and there is
    # genuinely independent space left over
    for polity in sector.polities:
        for h in polity.controlled_systems:
            assert sector.systems[h].allegiance == polity.allegiance_code
    unaligned = sum(1 for s in sector.systems.values() if s.allegiance == "Na")
    assert unaligned > 0, "no independent worlds left in the sector"


def test_legacy_subsector_list_still_renders():
    """generate_sector_svg used to take a list of sixteen subsectors."""
    random.seed(7)
    subs = [wm.generate_sector(8, 10) for _ in range(16)]
    merged = merge_subsectors(subs, "Legacy")
    assert merged.width == 32 and merged.height == 40
    svg = generate_sector_svg(subs)
    ET.fromstring(svg)
    assert sum(1 for _ in ET.fromstring(svg).iter(f"{SVG_NS}polygon")) == 32 * 40


def test_hex_neighbors_agree_with_distance_metric():
    for col in range(2, 31):
        for row in range(2, 39):
            for direction, (nc, nr) in hex_neighbors(col, row).items():
                d = hex_distance(f"{col:02d}{row:02d}", f"{nc:02d}{nr:02d}")
                assert d == 1, f"{direction} of {col:02d}{row:02d} is {d} pc away"
