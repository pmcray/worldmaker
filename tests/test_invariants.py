"""Internal-consistency tests: things that must hold for the code to be doing
what it says it does (regardless of book fidelity)."""
import math
import random

import pytest

import worldmaker as wm
from worldmaker.utils import Utils
from worldmaker.sector import is_adjacent, hex_distance

N_SYSTEMS = 300


@pytest.fixture(scope="module")
def systems():
    random.seed(1105)
    return [wm.generate_full_system(f"Sys{i}") for i in range(N_SYSTEMS)]


def test_generation_never_crashes(systems):
    assert len(systems) == N_SYSTEMS


def test_every_system_has_a_primary(systems):
    for s in systems:
        assert s.primary_star is not None
        assert s.primary_star.mass > 0
        assert s.primary_star.luminosity > 0


def test_world_counts_match_bodies(systems):
    for s in systems:
        placed = len(s.all_worlds)
        expected = s.total_worlds  # empty orbits hold no body
        assert placed == expected, (
            f"{s.name}: placed {placed} bodies but total_worlds={expected} "
            f"(GG={s.gas_giant_count} PB={s.planetoid_belt_count} "
            f"TP={s.terrestrial_planet_count})"
        )


def test_orbits_are_positive_and_sorted(systems):
    for s in systems:
        for star in s.stars:
            if star.is_composite:
                continue
            orbits = [w.orbit_num for w in star.orbiting_bodies]
            assert orbits == sorted(orbits)
            for w in star.orbiting_bodies:
                assert w.orbit_num >= 0, f"{s.name} {w.designation}: negative orbit"
                assert w.orbit_au >= 0


def test_eccentricity_in_range(systems):
    for s in systems:
        for w in s.all_worlds:
            assert 0.0 <= w.eccentricity < 1.0


def test_periods_positive(systems):
    for s in systems:
        for w in s.all_worlds:
            if w.orbit_au > 0:
                assert w.period_years > 0


def test_uwp_string_format(systems):
    for s in systems:
        for w in s.all_worlds:
            if w.is_mainworld:
                u = str(w.uwp)
                assert len(u) == 9 and u[7] == "-", f"malformed UWP {u!r}"


def test_secondary_stars_have_orbits(systems):
    """Secondary (Close/Near/Far) stars must be placed in an orbit before
    forbidden-zone / Hill-sphere logic can work. WBH p.27 assigns Orbit#
    ranges (Close 1-5, Near 6-10, Far 11-15 +/- variance)."""
    checked = 0
    for s in systems:
        for star in s.stars:
            if star.orbit_class in ("Close", "Near", "Far"):
                checked += 1
                assert star.orbit_num > 0, (
                    f"{s.name}: {star.orbit_class} star {star.designation} has "
                    f"orbit_num={star.orbit_num} - never assigned"
                )
    assert checked > 0, "no multi-star systems generated in sample"


def test_satellite_orbits_are_populated(systems):
    """Satellite dataclass has orbit_pd / period_hours fields (WBH pp.75-78:
    moon orbit location in planetary diameters, Roche limit, period formula).
    If populated, they must be positive."""
    sats = [
        sat
        for s in systems
        for w in s.all_worlds
        for sat in w.satellites
        if not sat.is_ring
    ]
    assert sats, "no satellites generated in sample"
    populated = [sat for sat in sats if sat.orbit_pd > 0]
    assert populated, (
        f"none of {len(sats)} generated moons has an orbital distance; "
        "WBH moon placement is not implemented"
    )


def test_hex_adjacency_is_symmetric():
    for c1 in range(1, 9):
        for r1 in range(1, 11):
            for c2 in range(1, 9):
                for r2 in range(1, 11):
                    h1, h2 = f"{c1:02d}{r1:02d}", f"{c2:02d}{r2:02d}"
                    assert is_adjacent(h1, h2) == is_adjacent(h2, h1)


def _traveller_hex_distance(h1, h2):
    """Reference implementation: offset -> cube coords, standard hex metric
    (matches travellermap.com; Traveller columns are staggered, odd columns
    shifted down half a hex)."""
    def to_cube(h):
        col, row = int(h[:2]), int(h[2:])
        q = col
        r = row - (col + (col & 1)) // 2
        x = q
        z = r
        y = -x - z
        return x, y, z

    a, b = to_cube(h1), to_cube(h2)
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]), abs(a[2] - b[2]))


def test_adjacency_matches_true_hex_metric():
    """Every pair at true hex distance 1 must be adjacent and vice versa."""
    mism = []
    for c1 in range(1, 9):
        for r1 in range(1, 11):
            for c2 in range(1, 9):
                for r2 in range(1, 11):
                    h1, h2 = f"{c1:02d}{r1:02d}", f"{c2:02d}{r2:02d}"
                    if h1 == h2:
                        continue
                    truth = _traveller_hex_distance(h1, h2) == 1
                    if is_adjacent(h1, h2) != truth:
                        mism.append((h1, h2, truth))
    assert not mism, f"{len(mism)} adjacency mismatches, e.g. {mism[:6]}"


def test_hex_distance_is_hex_metric():
    """Jump routes/wave propagation need parsec (hex) distance, not Euclidean."""
    bad = []
    for c2 in range(1, 9):
        for r2 in range(1, 11):
            h2 = f"{c2:02d}{r2:02d}"
            d_code = hex_distance("0101", h2)
            d_true = _traveller_hex_distance("0101", h2)
            if round(d_code) != d_true:
                bad.append((h2, d_code, d_true))
    assert not bad, f"{len(bad)} distance errors, e.g. {bad[:6]}"


def test_starport_population_dm_ordering():
    """Mongoose starport DMs: Pop<=2 is DM-2, Pop 3-4 DM-1. The elif chain
    must test <=2 before <=4 or DM-2 is unreachable."""
    from worldmaker import society

    random.seed(7)
    # Statistical check: with pop=1 the mean starport roll should be 2D-2,
    # i.e. 'X' on raw 2..4 -> P(X) = P(2D<=4) = 6/36 ~ 16.7%.
    n = 20000
    xs = sum(1 for _ in range(n) if society.generate_starport(1) == "X")
    frac = xs / n
    assert frac > 0.12, (
        f"P(starport X | pop 1) = {frac:.3f}; expected ~0.167 with DM-2. "
        "DM-2 branch is unreachable (elif ordering bug)"
    )


def test_orbits_within_available_zones(systems):
    """Placed worlds should sit inside the star's computed available orbit
    ranges (the whole point of forbidden zones)."""
    outside = 0
    total = 0
    for s in systems:
        star = s.primary_star
        if not star.available_orbits:
            continue
        for w in star.orbiting_bodies:
            total += 1
            if not any(a <= w.orbit_num <= b for a, b in star.available_orbits):
                outside += 1
    assert total > 0
    assert outside == 0, f"{outside}/{total} worlds placed inside forbidden zones"


def test_worlds_do_not_pile_onto_one_orbit(systems):
    """Two worlds cannot occupy the same Orbit#.

    A wide spread used to walk the outer worlds past the end of the orbit
    table, where every one of them snapped onto the outermost Orbit# - whole
    systems ended up stacked at 20.0, at 78,700 AU."""
    from collections import Counter

    duplicates = 0
    total = 0
    for s in systems:
        orbits = [round(w.orbit_num, 2) for w in s.all_worlds]
        total += len(orbits)
        duplicates += sum(count - 1
                          for count in Counter(orbits).values() if count > 1)
    assert total > 0
    # A handful may still coincide where the available orbits are genuinely
    # exhausted, but it must be rare rather than routine.
    assert duplicates <= total * 0.01, (
        f"{duplicates}/{total} worlds share an orbit with another")


def test_outermost_orbit_is_not_a_dumping_ground(systems):
    """Worlds should not collect on the last Orbit# of the table."""
    at_edge = sum(1 for s in systems for w in s.all_worlds
                  if round(w.orbit_num, 2) >= 20.0)
    total = sum(len(s.all_worlds) for s in systems)
    assert total > 0
    assert at_edge <= total * 0.05, (
        f"{at_edge}/{total} worlds sit at the outermost Orbit#")


def test_sector_generation_and_exports():
    random.seed(3)
    sec = wm.generate_sector(8, 10)
    assert 20 <= len(sec.systems) <= 60  # ~50% of 80 hexes
    txt = wm.export_sector_sec_file(sec)
    assert txt.count("\n") >= len(sec.systems)
    svg = wm.generate_subsector_svg(sec, "Test")
    assert svg.startswith("<svg") and svg.endswith("</svg>")
    import xml.etree.ElementTree as ET

    ET.fromstring(svg)  # well-formed XML
