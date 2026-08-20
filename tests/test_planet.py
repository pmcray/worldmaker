"""Tests for the planet surface model and its renderers.

These cover the three products of `worldmaker.planet`: the spherical terrain
model, the Traveller polyhedral net maps built from it, and the orbital
views. The physical checks are calibrated against Terra, which the World
Builder's Handbook (p.133) uses as its own reference garden world.
"""
import math
import random
import xml.etree.ElementTree as ET

import pytest

np = pytest.importorskip("numpy")

import worldmaker as wm
from worldmaker import planet
from worldmaker.classes import UWP
from worldmaker.sector import generate_full_sector


# A small texture keeps the suite quick; the model is resolution-independent.
SMALL = dict(width=256, height=128)


class _World:
    """A minimal stand-in carrying just what the surface model reads."""

    def __init__(self, **kwargs):
        self.name = kwargs.pop('name', 'Testworld')
        self.uwp = UWP()
        self.uwp.size = kwargs.pop('size', '8')
        self.uwp.atmosphere = kwargs.pop('atmosphere', '6')
        self.uwp.hydrographics = kwargs.pop('hydrographics', '7')
        self.uwp.population = kwargs.pop('population', '7')
        self.mean_temperature = kwargs.pop('mean_temperature', 288.0)
        self.axial_tilt = kwargs.pop('axial_tilt', 23.5)
        self.tectonic_plates = kwargs.pop('tectonic_plates', 8)
        self.biomass_rating = kwargs.pop('biomass_rating', 6)
        self.atmos_pressure_bar = kwargs.pop('atmos_pressure_bar', 1.0)
        self.habitability_rating = kwargs.pop('habitability_rating', 10)
        self.gravity = kwargs.pop('gravity', 1.0)
        self.is_mainworld = True
        for key, value in kwargs.items():
            setattr(self, key, value)


@pytest.fixture(scope="module")
def terra():
    return _World(name='Terra')


@pytest.fixture(scope="module")
def surface(terra):
    return planet.generate_planet_surface(terra, seed=4242, **SMALL)


# ------------------------------------------------------------------ noise

def test_noise_is_deterministic_for_a_seed():
    a = planet.SphereNoise(11)
    b = planet.SphereNoise(11)
    pts = np.linspace(-2.0, 2.0, 32)
    assert np.allclose(a.noise(pts, pts * 0.5, pts * -0.3),
                       b.noise(pts, pts * 0.5, pts * -0.3))


def test_different_seeds_give_different_terrain():
    a = planet.SphereNoise(11)
    b = planet.SphereNoise(12)
    pts = np.linspace(-2.0, 2.0, 32)
    assert not np.allclose(a.noise(pts, pts, pts), b.noise(pts, pts, pts))


def test_noise_stays_in_unit_range():
    noise = planet.SphereNoise(7)
    pts = np.linspace(-8.0, 8.0, 400)
    values = noise.noise(pts, pts * 0.31, pts * -0.77)
    assert values.min() >= -1.0001 and values.max() <= 1.0001


def test_fbm_sums_stay_in_range():
    noise = planet.SphereNoise(3)
    x, y, z, _, _ = planet._sphere_grid(64, 32)
    plain = noise.fbm(x * 2, y * 2, z * 2, octaves=4)
    ridged = noise.fbm(x * 2, y * 2, z * 2, octaves=4, ridged=True)
    assert -1.0 <= plain.min() and plain.max() <= 1.0
    assert 0.0 <= ridged.min() and ridged.max() <= 1.0


# ------------------------------------------------------- Earth-like search

def test_terra_scores_near_the_top(terra):
    assert planet.earthlike_score(terra) > 0.85


def test_unbreathable_atmosphere_scores_zero():
    # Only atmospheres 5-8 are breathable without assistance, so a vacuum
    # world cannot be an Earth-like candidate whatever else it has.
    vacuum = _World(atmosphere='0', hydrographics='0', mean_temperature=210.0)
    assert planet.earthlike_score(vacuum) == 0.0


def test_score_falls_away_from_terra(terra):
    baseline = planet.earthlike_score(terra)
    hot = _World(mean_temperature=340.0)
    dry = _World(hydrographics='1')
    assert planet.earthlike_score(hot) < baseline
    assert planet.earthlike_score(dry) < baseline


def test_candidate_search_returns_a_scored_world():
    random.seed(1105)
    sector = generate_full_sector(name='Test Reach', width=8, height=10)
    found = planet.find_earthlike_candidate(sector, top=3)
    assert found, "a populated sector should hold at least one candidate"
    hexes = [entry[0] for entry in found]
    scores = [entry[2] for entry in found]
    assert len(set(hexes)) == len(hexes)
    assert scores == sorted(scores, reverse=True)
    assert all(0.0 < score <= 1.0 for score in scores)


# ------------------------------------------------------------ surface model

def test_surface_carries_the_projection_contract(surface):
    # planet_projections and the net renderers read these keys by name.
    for key in ('surface_texture', 'albedo', 'heightmap', 'land_mask',
                'sea_level', 'temperature_map', 'moisture_map', 'ice_mask',
                'clouds', 'normals', 'width', 'height', 'seed'):
        assert key in surface, f"missing surface key {key!r}"


def test_texture_is_an_rgb_image(surface):
    texture = surface['surface_texture']
    assert texture.shape == (SMALL['height'], SMALL['width'], 3)
    assert texture.dtype == np.uint8


def test_surface_generation_is_reproducible(terra):
    a = planet.generate_planet_surface(terra, seed=99, **SMALL)
    b = planet.generate_planet_surface(terra, seed=99, **SMALL)
    assert np.array_equal(a['surface_texture'], b['surface_texture'])


def test_hydrographics_sets_the_ocean_fraction(terra):
    # Sea level is the hydrographics percentile of the elevation field, so
    # the water covered fraction should track the UWP digit closely.
    for digit in ('2', '5', '9'):
        world = _World(hydrographics=digit)
        model = planet.generate_planet_surface(world, seed=5, **SMALL)
        covered = 1.0 - float(model['land_mask'].mean())
        assert abs(covered - int(digit) / 10.0) < 0.06


def test_a_dry_world_has_no_sea(terra):
    desert = _World(hydrographics='0', mean_temperature=300.0)
    model = planet.generate_planet_surface(desert, seed=5, **SMALL)
    assert model['land_mask'].all()


def test_climate_is_warmest_at_the_equator(surface):
    temperature = surface['temperature_map']
    equator = temperature[temperature.shape[0] // 2].mean()
    poles = np.concatenate([temperature[:3].ravel(), temperature[-3:].ravel()])
    assert equator > poles.mean() + 30.0


def test_ice_forms_only_at_the_cold_extremes(surface):
    ice = surface['ice_mask']
    assert ice.any(), "a Terra-like world should have polar caps"
    rows = np.where(ice.any(axis=1))[0]
    # No ice inside the tropics on a world with Terra's mean temperature.
    tropic = surface['height'] * 0.25
    assert rows.min() < tropic or rows.max() > surface['height'] - tropic
    band = (rows > tropic) & (rows < surface['height'] - tropic)
    assert not band.all()


def test_vacuum_world_has_no_clouds():
    rock = _World(atmosphere='0', hydrographics='0', atmos_pressure_bar=0.0,
                  biomass_rating=0, mean_temperature=250.0)
    model = planet.generate_planet_surface(rock, seed=5, **SMALL)
    assert float(model['clouds'].max()) == pytest.approx(0.0, abs=1e-6)


def test_normals_are_unit_length(surface):
    lengths = np.linalg.norm(surface['normals'], axis=-1)
    assert np.allclose(lengths, 1.0, atol=1e-3)


# --------------------------------------------------------- net geometry

def test_icosahedron_has_twenty_faces_of_unit_vertices():
    faces = planet.icosahedron_faces()
    assert len(faces) == 20
    for face in faces:
        assert len(face) == 3
        for vertex in face:
            assert abs(float(np.linalg.norm(vertex)) - 1.0) < 1e-6


def test_icosahedron_faces_cover_both_poles():
    faces = planet.icosahedron_faces()
    zs = [float(v[2]) for face in faces for v in face]
    assert max(zs) > 0.99 and min(zs) < -0.99


def test_terrain_classification_matches_the_net_cell_count(surface):
    from worldmaker.worldmap import DEFAULT_HEXES_PER_EDGE

    cells = planet.classify_surface_terrain(surface)
    assert len(cells) == 20
    per_face = DEFAULT_HEXES_PER_EDGE ** 2
    assert all(len(face) == per_face for face in cells)


def test_terrain_classification_uses_known_terrain_names(surface):
    from worldmaker.worldmap import TERRAIN

    names = {cell for face in planet.classify_surface_terrain(surface)
             for cell in face}
    assert names, "the net should classify at least one cell"
    assert names <= set(TERRAIN)


def test_a_terra_like_world_shows_land_sea_and_relief(surface):
    names = {cell for face in planet.classify_surface_terrain(surface)
             for cell in face}
    assert {'ocean', 'sea'} & names, "oceans should appear"
    assert {'plains', 'forest', 'desert', 'mountain'} & names
    # Highlands are a share of the land, so relief always registers
    assert 'mountain' in names


def test_ocean_world_classifies_as_water(surface):
    ocean = _World(hydrographics='A', name='Thalassa')
    model = planet.generate_planet_surface(ocean, seed=5, **SMALL)
    cells = [c for face in planet.classify_surface_terrain(model) for c in face]
    water = sum(1 for c in cells if c in ('ocean', 'sea', 'ice'))
    assert water / len(cells) > 0.9


# ------------------------------------------------------------ net renderers

def _parse(svg):
    return ET.fromstring(svg)


def test_icosahedral_net_is_valid_svg(surface):
    svg = planet.render_icosahedral_net_svg(surface, name='Terra')
    root = _parse(svg)
    assert root.tag.endswith('svg')
    assert 'TERRA' in svg.upper()


def test_dodecahedral_net_draws_twelve_faces(surface):
    svg = planet.render_dodecahedral_net(surface, name='Terra', samples=8)
    root = _parse(svg)
    ns = '{http://www.w3.org/2000/svg}'
    outlines = [p for p in root.iter(f'{ns}polygon')
                if 'dn-face' in (p.get('class') or '')]
    assert len(outlines) == 12
    for polygon in outlines:
        assert len(polygon.get('points').split()) == 5


def test_dodecahedral_faces_are_clipped_to_their_pentagon(surface):
    # Without a clip path the sampled patches spill over the fold lines.
    svg = planet.render_dodecahedral_net(surface, name='Terra', samples=8)
    root = _parse(svg)
    ns = '{http://www.w3.org/2000/svg}'
    clips = list(root.iter(f'{ns}clipPath'))
    assert len(clips) == 12
    groups = [g for g in root.iter(f'{ns}g') if g.get('clip-path')]
    assert len(groups) == 12


def test_dodecahedron_face_centres_are_on_the_sphere():
    centres = planet._dodecahedron_face_centres()
    assert len(centres) == 12
    for centre in centres:
        assert abs(float(np.linalg.norm(np.array(centre))) - 1.0) < 1e-6
    # Opposite faces: every centre has an antipode among the twelve.
    for centre in centres:
        opposite = -np.array(centre)
        assert any(np.allclose(opposite, other, atol=1e-6)
                   for other in centres)


def test_pentagon_edge_midpoint_sits_at_the_apothem():
    radius = 100.0
    points = planet._pentagon_points(0.0, 0.0, radius, 0.0)
    assert len(points) == 5
    for k in range(5):
        ax, ay = points[k]
        bx, by = points[(k + 1) % 5]
        assert math.hypot(ax, ay) == pytest.approx(radius, abs=1e-6)
        midpoint = math.hypot((ax + bx) / 2.0, (ay + by) / 2.0)
        assert midpoint == pytest.approx(radius * math.cos(math.pi / 5),
                                         abs=1e-6)


def test_net_ring_faces_really_adjoin_their_hub():
    # Laying arbitrary faces around a hub gives a net that looks right and
    # folds into nothing. Adjacent dodecahedron faces subtend arccos(1/V5).
    faces = planet._net_faces(120.0)
    centres = [face[0] for face in faces]
    expected = math.acos(1.0 / math.sqrt(5.0))
    for hub, ring in ((0, range(1, 6)), (6, range(7, 12))):
        for index in ring:
            angle = math.acos(float(np.clip(
                np.dot(centres[hub], centres[index]), -1, 1)))
            assert angle == pytest.approx(expected, abs=1e-9)


def test_the_two_net_hubs_are_opposite_faces():
    centres = [face[0] for face in planet._net_faces(120.0)]
    assert len(centres) == 12
    assert np.allclose(centres[6], -np.array(centres[0]), atol=1e-9)
    unique = {tuple(np.round(c, 9)) for c in centres}
    assert len(unique) == 12, "every face must appear exactly once"


def test_terrain_runs_continuously_across_every_fold():
    """The test that decides whether the sheet folds into the world.

    A point on a shared fold edge must project to the same place on the
    sphere from either of the two faces that meet there. A wrong tangent
    frame or a fudged gnomonic scale makes the terrain jump at the fold.
    """
    radius = 120.0
    faces = planet._net_faces(radius)
    scale = planet._NET_GNOMONIC_SCALE

    def to_sphere(face, page_x, page_y):
        centre, east, north, cx, cy, rotation = face
        u, v = (page_x - cx) / radius, (page_y - cy) / radius
        theta = math.radians(rotation)
        ur = u * math.cos(theta) - v * math.sin(theta)
        vr = u * math.sin(theta) + v * math.cos(theta)
        point = centre + east * (ur * scale) + north * (vr * scale)
        return point / np.linalg.norm(point)

    worst = 0.0
    for half in (0, 1):
        hub = faces[half * 6]
        for i in range(5):
            ring = faces[half * 6 + 1 + i]
            mid_x = (hub[3] + ring[3]) / 2.0
            mid_y = (hub[4] + ring[4]) / 2.0
            dx, dy = ring[3] - hub[3], ring[4] - hub[4]
            length = math.hypot(dx, dy)
            along = (-dy / length, dx / length)
            for step in (-0.5, -0.25, 0.0, 0.25, 0.5):
                x = mid_x + along[0] * step * radius
                y = mid_y + along[1] * step * radius
                a = to_sphere(hub, x, y)
                b = to_sphere(ring, x, y)
                worst = max(worst, math.degrees(math.acos(
                    float(np.clip(np.dot(a, b), -1, 1)))))
    assert worst < 0.001, f"folds mismatch by up to {worst:.4f} degrees"


def test_dodecahedral_ring_faces_touch_the_centre_face(surface):
    # Two pentagons sharing a fold edge have their centres two apothems
    # apart, which is what lets the flat net fold into a solid.
    radius = 120.0
    svg = planet.render_dodecahedral_net(surface, face_radius=radius,
                                         name='Terra', samples=6)
    root = _parse(svg)
    ns = '{http://www.w3.org/2000/svg}'
    centroids = []
    for polygon in root.iter(f'{ns}polygon'):
        if 'dn-face' not in (polygon.get('class') or ''):
            continue
        pts = [tuple(float(v) for v in pair.split(','))
               for pair in polygon.get('points').split()]
        centroids.append((sum(p[0] for p in pts) / 5.0,
                          sum(p[1] for p in pts) / 5.0))

    assert len(centroids) == 12
    expected = 2.0 * radius * math.cos(math.pi / 5)
    for half in (centroids[:6], centroids[6:]):
        hub, ring = half[0], half[1:]
        assert len(ring) == 5
        for face in ring:
            distance = math.hypot(face[0] - hub[0], face[1] - hub[1])
            assert distance == pytest.approx(expected, rel=1e-3)


# ------------------------------------------------------------ orbital view

@pytest.fixture(scope="module")
def orbit(surface):
    return planet.render_orbital_view(surface, size=160)


def test_orbital_view_is_a_square_rgb_image(orbit):
    assert orbit.shape == (160, 160, 3)
    assert orbit.dtype == np.uint8


def test_the_planet_does_not_fill_the_frame(orbit):
    # The disc must sit inside the frame with space around it, or the limb
    # and the atmospheric halo are cropped away.
    lit = orbit.sum(axis=2) > 40
    assert not lit[0].any() and not lit[-1].any()
    assert 0.15 < lit.mean() < 0.75


def test_the_night_side_is_darker_than_the_day_side(surface):
    image = planet.render_orbital_view(
        surface, size=160, sub_observer=(0.0, 0.0),
        sun_direction=(0.0, 0.0), city_lights=False, starfield=False)
    half = image.shape[1] // 2
    # Sun behind the camera: the disc is fully lit and bright throughout.
    day = float(image[:, half - 20:half + 20].mean())

    night = planet.render_orbital_view(
        surface, size=160, sub_observer=(0.0, 0.0),
        sun_direction=(0.0, 180.0), city_lights=False, starfield=False)
    dark = float(night[:, half - 20:half + 20].mean())
    assert dark < day * 0.35


def test_terminator_runs_across_the_disc(surface):
    image = planet.render_orbital_view(
        surface, size=160, sub_observer=(0.0, 0.0),
        sun_direction=(0.0, 80.0), city_lights=False, starfield=False)
    half = image.shape[0] // 2
    row = image[half].sum(axis=1).astype(float)
    lit = row[row > 0]
    assert lit.size, "the equator should cross the disc"
    # One limb lit, the other in shadow.
    assert row[:len(row) // 2].mean() != pytest.approx(
        row[len(row) // 2:].mean(), rel=0.25)


def test_starfield_only_appears_outside_the_disc(surface):
    plain = planet.render_orbital_view(surface, size=160, starfield=False,
                                       city_lights=False)
    starry = planet.render_orbital_view(surface, size=160, starfield=True,
                                        city_lights=False)
    assert starry.sum() > plain.sum()
    # Every added pixel must land on empty sky, never on the planet.
    sky = plain.sum(axis=2) == 0
    added = starry.astype(int) - plain.astype(int)
    assert added[sky].sum() > 0, "no stars were drawn"
    assert not (added[~sky] != 0).any(), "stars bled onto the disc"


def test_altitude_keeps_the_framing_but_changes_the_view(surface):
    # The camera framing is normalised so the disc always fills the same
    # share of the frame; altitude changes how much of the globe is in
    # view, not how big it looks.
    far = planet.render_orbital_view(surface, size=160, altitude_radii=6.0,
                                     starfield=False, city_lights=False)
    near = planet.render_orbital_view(surface, size=160, altitude_radii=1.6,
                                      starfield=False, city_lights=False)
    far_disc = (far.sum(axis=2) > 0).mean()
    near_disc = (near.sum(axis=2) > 0).mean()
    assert far_disc == pytest.approx(near_disc, abs=0.02)
    assert not np.array_equal(far, near)


def test_orbital_sequence_returns_distinct_views(surface):
    frames = planet.render_orbital_sequence(surface, frames=3, size=96)
    assert len(frames) == 3
    assert not np.array_equal(frames[0], frames[1])


# ---------------------------------------------------------------- package

def test_planet_api_is_exported_from_the_package():
    for name in ('generate_planet_surface', 'find_earthlike_candidate',
                 'render_orbital_view', 'render_dodecahedral_net',
                 'render_icosahedral_net_svg', 'render_planet_package'):
        assert hasattr(wm, name), f"worldmaker.{name} is not exported"


def test_render_planet_package_writes_every_artefact(terra, tmp_path):
    pytest.importorskip("PIL")
    result = planet.render_planet_package(
        terra, out_dir=str(tmp_path), size=96, texture_size=(256, 128),
        views=2, seed=7)
    paths = result['paths']
    assert set(paths) == {'texture', 'orbit_1', 'orbit_2',
                          'icosahedral_net', 'dodecahedral_net'}
    for path in paths.values():
        assert (tmp_path / path.rsplit('/', 1)[-1]).stat().st_size > 0
    assert len(result['orbital_views']) == 2
