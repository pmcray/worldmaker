"""Finding a particular kind of world in a generated sector.

A sector holds hundreds of systems and thousands of bodies. When a Referee
wants one specific *sort* of place - a habitable world in a Sun-like star's
habitable zone, outside a rival power's space, at a technology level that
leaves it worth visiting - scanning by eye is hopeless.

`find_worlds` scores every body in a sector against a `WorldProfile`: hard
filters that a candidate must satisfy, and a weighted comparison of the
UWP digits that decides the ranking. Weights matter more than they might
seem: "Earth-like" means Size, Atmosphere and Hydrographics above all, and
a match on those with the wrong Law Level is a far better answer than the
reverse.

`ERITH` is a shipped profile for exactly that search.
"""
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from .stellar import type_letter_of
from .utils import Utils

# The UWP digits a profile can match on, in their conventional order.
UWP_FIELDS = ('size', 'atmosphere', 'hydrographics', 'population',
              'government', 'law_level', 'tech_level')


@dataclass
class WorldProfile:
    """The kind of world being looked for.

    `targets` maps UWP fields to the value wanted; `weights` says how much
    each matters; `tolerances` gives the deviation that costs nothing (so a
    Law Level "a notch higher or lower" scores as an exact hit)."""
    name: str = "World"
    description: str = ""
    targets: Dict[str, int] = field(default_factory=dict)
    weights: Dict[str, float] = field(default_factory=dict)
    tolerances: Dict[str, int] = field(default_factory=dict)
    # Hard filters
    star_types: Tuple[str, ...] = ()
    habitable_zone_only: bool = False
    habitable_zone_width: float = 1.0
    exclude_allegiances: Tuple[str, ...] = ()
    require_allegiances: Tuple[str, ...] = ()
    min_habitability: int = 0
    mainworld_only: bool = False
    # Mean surface temperature band in Kelvin. An "Earth-like" world that
    # sits at 220K is not Earth-like at all, so this is a hard filter.
    temperature_range: Optional[Tuple[float, float]] = None

    def weight_for(self, field_name: str) -> float:
        return self.weights.get(field_name, 1.0)

    def tolerance_for(self, field_name: str) -> int:
        return self.tolerances.get(field_name, 0)


@dataclass
class Match:
    """One candidate world and how well it fits."""
    hex: str = ""
    system: Any = None
    body: Any = None
    score: float = 0.0
    is_mainworld: bool = False
    star: Any = None
    notes: List[str] = field(default_factory=list)
    field_scores: Dict[str, float] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return getattr(self.body, 'name', '') or getattr(self.system, 'name', '')

    @property
    def uwp(self) -> str:
        return str(getattr(self.body, 'uwp', ''))

    def summary(self) -> str:
        role = "mainworld" if self.is_mainworld else "secondary world"
        star = getattr(self.star, 'spectral_type', '?')
        allegiance = getattr(self.system, 'allegiance', '')
        return (f"{self.hex}  {self.name:14s} {self.uwp}  {self.score:5.1f}%  "
                f"{role:16s} {star:8s} {allegiance}")


# ------------------------------------------------------------- the search

def _parent_star(system: Any, body: Any) -> Optional[Any]:
    """The star a body actually orbits, following a moon to its planet."""
    group = getattr(body, 'parent_star_group', None)
    if not group:
        parent = getattr(body, 'parent_body', None)
        group = getattr(parent, 'parent_star_group', None)
    star = next((s for s in getattr(system, 'stars', [])
                 if s.designation == group), None)
    return star or getattr(system, 'primary_star', None)


def _orbit_number(body: Any) -> float:
    orbit = getattr(body, 'orbit_num', 0.0) or 0.0
    if not orbit:
        parent = getattr(body, 'parent_body', None)
        orbit = getattr(parent, 'orbit_num', 0.0) or 0.0
    return orbit


def in_habitable_zone(system: Any, body: Any, width: float = 1.0) -> bool:
    """Whether a body sits within `width` Orbit#s of its star's habitable
    zone centre."""
    star = _parent_star(system, body)
    if star is None or not star.hzco:
        return False
    orbit = _orbit_number(body)
    if not orbit:
        return False
    return abs(orbit - star.hzco) <= width


def _passes_filters(system: Any, body: Any, profile: WorldProfile,
                    star: Any) -> bool:
    if profile.mainworld_only and not getattr(body, 'is_mainworld', False):
        return False

    if profile.star_types:
        letter = type_letter_of(getattr(star, 'spectral_type', '') or '')
        if letter not in profile.star_types:
            return False

    if profile.habitable_zone_only and not in_habitable_zone(
            system, body, profile.habitable_zone_width):
        return False

    allegiance = (getattr(system, 'allegiance', '') or '').strip()
    if profile.exclude_allegiances:
        for excluded in profile.exclude_allegiances:
            if allegiance == excluded or allegiance.startswith(excluded):
                return False
    if profile.require_allegiances:
        if not any(allegiance == wanted or allegiance.startswith(wanted)
                   for wanted in profile.require_allegiances):
            return False

    if profile.min_habitability:
        if (getattr(body, 'habitability_rating', 0) or 0) < profile.min_habitability:
            return False

    if profile.temperature_range:
        low, high = profile.temperature_range
        temperature = getattr(body, 'mean_temperature', 0.0) or 0.0
        if not (low <= temperature <= high):
            return False

    return True


def _field_score(actual: int, target: int, tolerance: int) -> float:
    """How well one UWP digit matches, from 1.0 (within tolerance) down to
    0.0 (hopeless). The falloff is gentle so a near miss still counts."""
    deviation = max(0, abs(actual - target) - max(0, tolerance))
    if deviation == 0:
        return 1.0
    return max(0.0, 1.0 - deviation / 6.0)


def score_world(body: Any, profile: WorldProfile) -> Tuple[float, Dict[str, float]]:
    """Scores a body's UWP against a profile, as a percentage."""
    uwp = getattr(body, 'uwp', None)
    if uwp is None or not profile.targets:
        return 0.0, {}

    total_weight = 0.0
    earned = 0.0
    per_field: Dict[str, float] = {}

    for field_name, target in profile.targets.items():
        actual = Utils.from_eHex(getattr(uwp, field_name, 0))
        weight = profile.weight_for(field_name)
        value = _field_score(actual, target, profile.tolerance_for(field_name))
        per_field[field_name] = round(value, 3)
        earned += value * weight
        total_weight += weight

    if total_weight <= 0:
        return 0.0, per_field
    return round(100.0 * earned / total_weight, 2), per_field


def find_worlds(sector: Any, profile: WorldProfile, limit: int = 10,
                minimum_score: float = 0.0) -> List[Match]:
    """Every body in a sector that passes the profile's filters, best first.

    Secondary worlds are searched alongside mainworlds, because the world a
    Referee wants is not always the one whose UWP the map prints."""
    matches: List[Match] = []

    for hex_coord, system in getattr(sector, 'systems', {}).items():
        for body in system.all_bodies:
            if getattr(body, 'is_ring', False):
                continue
            if getattr(body, 'body_type', '') == 'Gas Giant':
                continue

            star = _parent_star(system, body)
            if not _passes_filters(system, body, profile, star):
                continue

            score, per_field = score_world(body, profile)
            if score < minimum_score:
                continue

            matches.append(Match(
                hex=hex_coord, system=system, body=body, score=score,
                is_mainworld=bool(getattr(body, 'is_mainworld', False)),
                star=star, field_scores=per_field))

    matches.sort(key=lambda m: (-m.score, m.hex))
    return matches[:limit] if limit else matches


def best_world(sector: Any, profile: WorldProfile) -> Optional[Match]:
    """The single closest match, or None if nothing passes the filters."""
    found = find_worlds(sector, profile, limit=1)
    return found[0] if found else None


def describe_matches(matches: Sequence[Match], profile: WorldProfile) -> str:
    """A readable table of search results."""
    if not matches:
        return f"No world in this sector matches {profile.name}."
    lines = [f"Closest matches for {profile.name}:",
             f"  {profile.description}" if profile.description else "",
             "",
             "  Hex   Name           UWP         Score  Role             "
             "Star     Allegiance"]
    lines = [line for line in lines if line != ""] + [""]
    for match in matches:
        lines.append(f"  {match.summary()}")
    return "\n".join(lines)


# ---------------------------------------------------------------- profiles

# Terra's own profile, as the handbook's survey form gives it: D867974-8.
# Size 8, Atmosphere 6, Hydrographics 7 is what "Earth-like" means, and
# Government 7 - balkanisation - is what Earth actually has.
ERITH = WorldProfile(
    name="Erith",
    description=("A very Earth-like world: Terra's own size, atmosphere and "
                 "hydrographics, a balkanised government and a "
                 "pre-industrial technology, in the habitable zone of an "
                 "F, G or K star and outside Zhodani space."),
    targets={
        'size': 8, 'atmosphere': 6, 'hydrographics': 7,
        'population': 8, 'government': 7, 'law_level': 1, 'tech_level': 1,
    },
    # Physical Earth-likeness dominates: a world that is the right size,
    # air and water with the wrong law is still Erith; the reverse is not.
    weights={
        'size': 3.0, 'atmosphere': 4.0, 'hydrographics': 3.0,
        'population': 1.5, 'government': 2.0,
        'law_level': 0.5, 'tech_level': 0.5,
    },
    # "Tech and Law Levels could be a notch higher or lower"
    tolerances={'law_level': 1, 'tech_level': 1,
                'population': 1, 'hydrographics': 1},
    star_types=('F', 'G', 'K'),
    habitable_zone_only=True,
    habitable_zone_width=1.5,
    exclude_allegiances=('Zh',),
    min_habitability=6,
    # Liquid water at the surface, and a climate a Traveller could walk
    # around in without equipment. Terra's mean is 288K.
    temperature_range=(268.0, 305.0),
)


GARDEN_WORLD = WorldProfile(
    name="Garden world",
    description="Benign, well-watered and comfortably settled.",
    targets={'size': 8, 'atmosphere': 6, 'hydrographics': 6,
             'population': 6},
    weights={'size': 2.0, 'atmosphere': 3.0, 'hydrographics': 2.0,
             'population': 1.0},
    tolerances={'size': 1, 'hydrographics': 2, 'population': 2},
    star_types=('F', 'G', 'K'),
    habitable_zone_only=True,
    min_habitability=8,
    temperature_range=(260.0, 315.0),
)


REFUELLING_STOP = WorldProfile(
    name="Refuelling stop",
    description="Water to skim and nobody to object.",
    targets={'hydrographics': 8, 'population': 0, 'law_level': 0},
    weights={'hydrographics': 3.0, 'population': 1.0, 'law_level': 1.0},
    tolerances={'hydrographics': 2, 'population': 1, 'law_level': 1},
)


PROFILES: Dict[str, WorldProfile] = {
    'erith': ERITH,
    'garden': GARDEN_WORLD,
    'refuelling': REFUELLING_STOP,
}


# ------------------------------------------------------------- imposing

def impose_profile(target: Any, profile: WorldProfile,
                   regenerate: bool = True) -> Any:
    """Makes a world actually match a profile, rather than merely come close.

    A combination like Erith's - a populous, balkanised, pre-industrial
    world - is one the dice rarely produce, because generation ties Tech
    Level to starport and population. Searching finds the nearest thing;
    this makes it the thing. Everything downstream of the UWP is rebuilt so
    the world stays internally consistent.

    Accepts a Match or a world directly, and returns the world."""
    from .government import generate_government_details
    from .nations import generate_nations
    from .population import generate_population_details
    from .technology import generate_technology_profile
    from .worldmap import generate_world_terrain

    world = getattr(target, 'body', None) or target

    for field_name, value in profile.targets.items():
        setattr(world.uwp, field_name, Utils.eHex(value))
    # The physical body must agree with the profile it now presents
    world.size_code = world.uwp.size
    world.atmosphere_code = world.uwp.atmosphere
    world.hydrographics_code = world.uwp.hydrographics

    if not regenerate:
        return world

    generate_population_details(world)
    generate_government_details(world)
    generate_technology_profile(world)
    if Utils.from_eHex(world.uwp.government) == 7:
        generate_nations(world, terrain=generate_world_terrain(world))
    return world


def make_erith(sector: Any, name: str = "Erith", owner: str = None,
               culture_family: str = None,
               proprietary: bool = True) -> Optional[Match]:
    """Finds the sector's most Earth-like world and makes it Erith.

    The whole workflow in one call: search, impose the profile, rebuild the
    world's nations, optionally give the nations a culture palette, and
    record the proprietor who keeps the place as it is. Returns the Match,
    whose `body` is the finished world."""
    from .cultures import apply_template_palette

    match = best_world(sector, ERITH)
    if match is None:
        return None

    world = impose_profile(match, ERITH)
    world.name = name
    match.system.name = name

    if culture_family:
        apply_template_palette(world, family=culture_family)

    if proprietary:
        make_proprietary(world, owner)
        for nation in getattr(world, 'nations', None) or []:
            nation.notes.append(
                f"Within the freehold of {world.proprietor['owner']}")
    else:
        # Asking for no proprietor means no proprietor, even if this world
        # was given one by an earlier call.
        world.proprietor = None

    match.score = score_world(world, ERITH)[0]
    match.notes.append(f"Imposed the {ERITH.name} profile on this world")
    return match


# ------------------------------------------------------- proprietary worlds

def make_proprietary(world: Any, owner: str = None,
                     suppress_technology: bool = True,
                     set_government: bool = None) -> Dict[str, Any]:
    """Marks a world as privately held - the estate of a family, a trust or
    a corporation rather than a state.

    Traveller's Government code 1 is "Company/Corporation", which covers a
    world owned outright. A proprietor with reason to keep the place as it
    is explains what dice rarely produce: a prime world left deliberately
    undeveloped, with a low Tech Level and almost no law because there is
    almost no government.

    On a balkanised world the title and the ground disagree, and the
    government code is left alone by default: someone holds the freehold,
    while the surface remains a patchwork of states who may or may not
    acknowledge it. That absentee-landlord arrangement is more interesting
    than either fact alone, so it is the default rather than a special
    case."""
    owner = owner or _proprietor_name()
    balkanised = Utils.from_eHex(getattr(world.uwp, 'government', 0)) == 7

    if set_government is None:
        set_government = not balkanised

    if set_government:
        world.uwp.government = '1'
        world.government_type = "Company/Corporation"

    if suppress_technology:
        world.notes.append(
            f"Held by {owner}: development deliberately restrained, and the "
            f"world's Tech Level reflects the proprietor's policy rather "
            f"than its people's capacity")
    world.notes.append(f"Proprietary world: the freehold of {owner}")
    if balkanised and not set_government:
        world.notes.append(
            "Title and ground disagree: the freehold is undisputed on paper, "
            "while the surface remains divided between its own states")

    holding = {
        'owner': owner,
        'kind': 'proprietary world',
        'government_code': 1 if set_government else
                           Utils.from_eHex(world.uwp.government),
        'suppressed_technology': bool(suppress_technology),
        'absentee': bool(balkanised and not set_government),
    }
    world.proprietor = holding
    return holding


_FAMILY_NAMES = ["Aldwyn", "Bellamy", "Carrow", "Devereaux", "Elsinore",
                 "Fairhurst", "Grieve", "Halloran", "Ingelow", "Jardine",
                 "Kessler", "Lachaise", "Moncrieff", "Norrington", "Oakhurst",
                 "Pemberton", "Quillan", "Rothesay", "Sandhurst", "Thorne"]

_HOUSE_FORMS = ["the {} family", "House {}", "the {} Trust",
                "{} Holdings", "the {} interest"]


def _proprietor_name() -> str:
    import random
    return random.choice(_HOUSE_FORMS).format(random.choice(_FAMILY_NAMES))
