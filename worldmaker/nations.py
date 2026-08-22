"""Nations on a balkanised world (WBH pp.155-156, 159).

A Government code of 7 means "no recognised central government that has
effective control over the entire world". The subordinate states "have
effective sovereignty or localised dominant control over their territories
and people", and the book is explicit that "each of these subordinate
governments could be rolled for separately".

That has two consequences the single-line UWP hides:

- The UWP's Law Level "refers to the government nearest the starport"
  (Government Types table, code 7). Every other nation has its own.
- The handbook's own survey forms print a *separate* Law Level and
  technology profile per faction - Zed Prime's form carries two of each,
  tagged (I) and (II).

So a balkanised world is not one society but many, at different levels of
law and technology, which is exactly what makes one a usable setting: a
single planet can hold a nation at TL 2 and its neighbour at TL 4 without
either being a fudge.

Nation counts follow the book: 1D nations per faction, and "on a roll of 5,
the Referee may choose to multiply the result by 10 minus the world's PCR,
and on a roll of 6, also multiply the result by the world's Population code
minus D3". That can reach hundreds, which the book says "should be
considered as flavour, not as a prelude to developing the details of
hundreds of nations" - so the true count is recorded and only a bounded
number are detailed.
"""
import math
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .classes import CulturalProfile
from .government import GOVERNMENT_TYPES
from .utils import Utils

WATER_TERRAIN = {'ocean', 'sea', 'ice'}

# How many nations to work up in full, however many the rolls produce.
DEFAULT_DETAIL_LIMIT = 12


@dataclass
class Nation:
    """One sovereign state on a balkanised world."""
    id: int = 0
    name: str = ""
    faction_id: int = 0
    government_code: int = 0
    government_type: str = ""
    law_level: int = 0
    law_profile: str = ""
    tech_level: int = 0
    technology_profile: str = ""
    population: int = 0
    population_share: float = 0.0
    culture: Optional[CulturalProfile] = None
    culture_template: str = ""
    territory: List[Tuple[int, int]] = field(default_factory=list)
    land_share: float = 0.0
    cities: List[Dict[str, Any]] = field(default_factory=list)
    capital: str = ""
    holds_starport: bool = False
    notes: List[str] = field(default_factory=list)

    @property
    def profile(self) -> str:
        """A compact profile in the handbook's own idiom: government code,
        law profile and Tech Level."""
        return (f"{Utils.eHex(self.government_code)}-"
                f"{self.law_profile or Utils.eHex(self.law_level)}-"
                f"{Utils.eHex(self.tech_level)}")

    def summary(self) -> str:
        seat = " (holds the starport)" if self.holds_starport else ""
        return (f"{self.name}{seat}: {self.government_type}, "
                f"Law {Utils.eHex(self.law_level)}, "
                f"TL {Utils.eHex(self.tech_level)}, "
                f"population {self.population:,}")


# --------------------------------------------------------------- counting

def nations_per_faction(pcr: int, population_code: int) -> int:
    """1D nations in a faction, with the book's two escalations (WBH p.156).

    A roll of 5 multiplies by 10 minus the world's PCR; a roll of 6 also
    multiplies by the Population code minus D3, never less than 2."""
    roll = Utils.D6()
    if roll < 5:
        return roll
    count = roll * max(1, 10 - pcr)
    if roll == 6:
        count *= max(2, population_code - Utils.D3())
    return count


def total_nation_count(world: Any, factions: Sequence[Dict[str, Any]]) -> int:
    """How many sovereign states the world actually has."""
    pcr = getattr(world, 'pcr', 5) or 5
    population_code = Utils.from_eHex(world.uwp.population)
    return sum(nations_per_faction(pcr, population_code) for _ in factions)


# ---------------------------------------------------------------- naming

_NATION_STEMS = [
    "Aldar", "Bryne", "Caldis", "Doran", "Elmere", "Fen", "Gasq", "Harroway",
    "Isk", "Jerath", "Kald", "Lorn", "Mersk", "Novar", "Orrin", "Pell",
    "Quarn", "Rhoss", "Sarn", "Thane", "Ulmar", "Veth", "Wold", "Xanth",
    "Yarrow", "Zeld", "Amrit", "Brack", "Corrin", "Dunmar", "Esk", "Fyrd",
    "Galt", "Hollin", "Irun", "Jorvik", "Kessel", "Lyth", "Marrow", "Nyle",
]

_NATION_FORMS = {
    'republic': ["Republic of {}", "{} Republic", "Free State of {}",
                 "Commonwealth of {}"],
    'monarchy': ["Kingdom of {}", "{} Crown", "Realm of {}", "Principality of {}"],
    'council': ["{} League", "{} Compact", "Confederation of {}",
                "{} Assembly"],
    'autocracy': ["{} Dominion", "{} Ascendancy", "Protectorate of {}",
                  "{} Directorate"],
    'corporate': ["{} Combine", "{} Concern", "{} Holdings", "{} Trust"],
    'clan': ["Clans of {}", "{} Tribes", "{} Marches", "Free Peoples of {}"],
}

# Which naming register suits which Government code
_FORM_FOR_GOVERNMENT = {
    0: 'clan', 1: 'corporate', 2: 'republic', 3: 'autocracy', 4: 'council',
    5: 'autocracy', 6: 'autocracy', 7: 'council', 8: 'republic',
    9: 'republic', 10: 'autocracy', 11: 'autocracy', 12: 'autocracy',
    13: 'autocracy', 14: 'monarchy', 15: 'monarchy',
}


def generate_nation_name(government_code: int, used: set) -> str:
    """A state name in a register that suits its government."""
    form_key = _FORM_FOR_GOVERNMENT.get(government_code, 'republic')
    forms = _NATION_FORMS[form_key]
    for _ in range(200):
        name = random.choice(forms).format(random.choice(_NATION_STEMS))
        if name not in used:
            used.add(name)
            return name
    i = 2
    while f"{name} {i}" in used:
        i += 1
    used.add(f"{name} {i}")
    return f"{name} {i}"


# ------------------------------------------------------------- territory

def land_cells(terrain: List[List[str]]) -> List[Tuple[int, int]]:
    """Every habitable surface cell of an icosahedral terrain map."""
    return [(face, i) for face, cells in enumerate(terrain)
            for i, kind in enumerate(cells) if kind not in WATER_TERRAIN]


def _face_band(face: int) -> int:
    """The icosahedral net's three latitude bands (worldmap's layout):
    faces 0-4 north, 5-14 equatorial, 15-19 south."""
    if face < 5:
        return 0
    if face < 15:
        return 1
    return 2


def _cell_distance(a: Tuple[int, int], b: Tuple[int, int],
                   per_face: int) -> float:
    """A rough surface distance between two cells.

    The flattened net does not carry true cross-face adjacency, so this
    prefers the same face, then neighbouring faces in the same latitude
    band, and finally anything else. Good enough to grow coherent
    territories; it is not a geodesic."""
    face_a, i_a = a
    face_b, i_b = b
    if face_a == face_b:
        return abs(i_a - i_b) / max(1, per_face)
    band_gap = abs(_face_band(face_a) - _face_band(face_b))
    # Faces are arranged around the world, so the gap wraps
    step = min(abs(face_a - face_b), 20 - abs(face_a - face_b))
    return 1.0 + band_gap * 2.0 + step * 0.25


def assign_territories(nations: List[Nation], terrain: List[List[str]]) -> None:
    """Divides the world's land between the nations.

    Each nation takes the land nearest its seat, so territories come out as
    coherent blocks rather than scattered cells."""
    land = land_cells(terrain)
    if not land or not nations:
        return

    per_face = max(len(face) for face in terrain) or 1
    seeds = random.sample(land, min(len(nations), len(land)))

    for nation in nations:
        nation.territory = []

    for cell in land:
        nearest = min(range(len(seeds)),
                      key=lambda k: _cell_distance(cell, seeds[k], per_face))
        nations[nearest % len(nations)].territory.append(cell)

    for nation in nations:
        nation.land_share = round(100.0 * len(nation.territory) / len(land), 1)


# -------------------------------------------------------------- detailing

def _nation_law_profile(law: int) -> str:
    """Law Level subcodes for one nation, in the O-WECPR form."""
    from .government import _law_subcode
    parts = [_law_subcode(law) for _ in range(5)]
    return f"{Utils.eHex(law)}-" + "".join(Utils.eHex(p) for p in parts)


def _nation_tech_level(world_tl: int, government_code: int) -> int:
    """A nation's Tech Level, spread around the world's.

    The world's headline Tech Level describes the starport's neighbourhood;
    the rest of the planet can run well ahead of or behind it."""
    spread = Utils.D6(2) - 7          # -5 to +5, centred on zero
    if government_code in (0, 7):
        spread -= 1                   # fragmented states industrialise slowly
    elif government_code in (1, 9):
        spread += 1                   # bureaucracies and corporations invest
    return max(0, min(33, world_tl + spread // 2))


def _distribute_population(total: int, count: int) -> List[int]:
    """Splits a world's population between its nations, unevenly - a few
    large states and a tail of small ones."""
    if count <= 0 or total <= 0:
        return []
    weights = [random.random() ** 2 + 0.05 for _ in range(count)]
    scale = total / sum(weights)
    shares = [int(w * scale) for w in weights]
    shares[0] += total - sum(shares)
    return shares


def generate_nations(world: Any, terrain: List[List[str]] = None,
                     detail_limit: int = DEFAULT_DETAIL_LIMIT,
                     culture_template: str = None) -> List[Nation]:
    """Builds the sovereign states of a balkanised world (WBH pp.155-156).

    Returns the nations worked up in full. `world.nation_count` records how
    many the rolls actually produced, which may be far more. Pass a
    `culture_template` name to draw the nations' cultures from the palette
    in `cultures.py` instead of rolling them procedurally."""
    from .society import generate_government, generate_law_level
    from .technology import generate_technology_profile
    from .cultures import culture_for_template, procedural_culture

    if Utils.from_eHex(world.uwp.government) != 7:
        world.nations = []
        world.nation_count = 0
        return []

    factions = getattr(world, 'factions', None) or []
    if not factions:
        world.nations = []
        world.nation_count = 0
        return []

    population_code = Utils.from_eHex(world.uwp.population)
    world_tl = Utils.from_eHex(world.uwp.tech_level)
    total_population = getattr(world, 'total_population', 0) or 0

    # The true count, per the book, then a bounded number to detail
    count = total_nation_count(world, factions)
    world.nation_count = count
    detailed = max(1, min(detail_limit, count))

    shares = _distribute_population(total_population, detailed)
    used_names = set()
    nations: List[Nation] = []

    for index in range(detailed):
        faction = factions[index % len(factions)]
        # "Balkanised world factions each roll for a Government code using
        # the same Population code as the world" (WBH p.159)
        government_code = (faction.get('government_code')
                           if index < len(factions)
                           else generate_government(population_code))
        government_code = max(0, min(15, government_code))
        law_level = generate_law_level(government_code)
        tech_level = _nation_tech_level(world_tl, government_code)

        nation = Nation(
            id=index + 1,
            name=generate_nation_name(government_code, used_names),
            faction_id=faction.get('id', index + 1),
            government_code=government_code,
            government_type=GOVERNMENT_TYPES.get(government_code, 'Unknown'),
            law_level=law_level,
            law_profile=_nation_law_profile(law_level),
            tech_level=tech_level,
            population=shares[index] if index < len(shares) else 0,
        )
        if government_code == 7:
            # The book notes a faction rolling 7 is itself balkanised, and
            # that this can spiral; recorded rather than recursed into.
            nation.notes.append(
                "Internally divided: this state is itself balkanised")
        nation.population_share = (
            round(100.0 * nation.population / total_population, 1)
            if total_population else 0.0)

        if culture_template:
            nation.culture = culture_for_template(culture_template, nation)
            nation.culture_template = culture_template
        else:
            nation.culture = procedural_culture(nation, world)

        nations.append(nation)

    # The UWP's Law Level and Tech Level describe the starport's neighbour
    # (WBH p.156, Government Types table, code 7).
    if nations:
        seat = max(nations, key=lambda n: n.population)
        seat.holds_starport = True
        seat.law_level = Utils.from_eHex(world.uwp.law_level)
        seat.law_profile = getattr(world, 'law_profile', '') or \
            _nation_law_profile(seat.law_level)
        seat.tech_level = world_tl
        seat.notes.append(
            "The world's UWP Law Level and Tech Level describe this state, "
            "as the government nearest the starport")

    if terrain is not None:
        assign_territories(nations, terrain)

    _assign_cities(world, nations)

    for nation in nations:
        _build_technology_profile(nation, generate_technology_profile)

    world.nations = nations
    return nations


def _build_technology_profile(nation: Nation, generator) -> None:
    """Gives a nation its own technology profile, as the handbook's survey
    forms print one per faction."""
    from .classes import UWP, PlanetaryBody

    stand_in = PlanetaryBody(
        uwp=UWP(starport='C',
                size='8', atmosphere='6', hydrographics='7',
                population=Utils.eHex(min(15, max(0, _population_code(nation)))),
                government=Utils.eHex(nation.government_code),
                law_level=Utils.eHex(nation.law_level),
                tech_level=Utils.eHex(nation.tech_level)))
    stand_in.law_weapons = nation.law_level
    generator(stand_in)
    nation.technology_profile = stand_in.technology_profile


def _population_code(nation: Nation) -> int:
    if nation.population <= 0:
        return 0
    return int(math.log10(nation.population))


def _assign_cities(world: Any, nations: List[Nation]) -> None:
    """Hands the world's major cities to its nations.

    The book asks for this directly: "Each city would receive at least a
    faction code, to be developed in the Government section" (p.154)."""
    cities = getattr(world, 'major_cities', None) or []
    if not cities or not nations:
        return

    # The capital goes to the state holding the starport; the rest fall to
    # nations in proportion to their populations.
    ordered = sorted(nations, key=lambda n: n.population, reverse=True)
    for index, city in enumerate(cities):
        nation = ordered[index % len(ordered)]
        if city.get('is_capital'):
            nation = next((n for n in nations if n.holds_starport), ordered[0])
        city['nation'] = nation.name
        city['faction'] = nation.faction_id
        nation.cities.append(city)
        if not nation.capital or city.get('is_capital'):
            nation.capital = city['name']


def describe_nations(world: Any) -> str:
    """A readable rundown of a balkanised world's states."""
    nations = getattr(world, 'nations', None) or []
    if not nations:
        return "No nations: this world is not balkanised."

    total = getattr(world, 'nation_count', len(nations))
    lines = [f"{getattr(world, 'name', '') or 'World'} ({world.uwp}) - "
             f"{total} sovereign states"]
    if total > len(nations):
        lines.append(f"  {len(nations)} detailed below; the rest are flavour")
    lines.append("")
    for nation in nations:
        lines.append(f"  {nation.summary()}")
        detail = [f"land {nation.land_share}%"] if nation.land_share else []
        if nation.culture_template:
            detail.append(f"culture: {nation.culture_template}")
        if nation.cities:
            detail.append(f"cities: {', '.join(c['name'] for c in nation.cities)}")
        if detail:
            lines.append(f"      {'; '.join(detail)}")
    return "\n".join(lines)
