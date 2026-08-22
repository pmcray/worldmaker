"""Secondary world populations (WBH p.155).

The mainworld carries the system's UWP, but it is rarely the only inhabited
body. The handbook's rule is short and worth quoting: other worlds "may have
a population, either affiliated with the mainworld or independent", they
"almost always have a smaller population than the mainworld", and inhospitable
ones "are subject to Tech Level restrictions on habitation".

The procedure, following the book and its Zed Prime worked example:

1. The maximum offworld Population code is the mainworld's minus 1D. If that
   is zero or less, no other body in the system is inhabited and no further
   checks are needed.
2. Every other significant body rolls 1D. A 5 or 6 means nobody lives there;
   otherwise the roll is that body's Population code, capped by step 1.
3. A world nobody could survive on at the system's Tech Level stays empty.
4. Inhabited secondary worlds get their own social characteristics - a
   colony answering to the mainworld, or an independent settlement.

This is what lets a system's most interesting world be somewhere other than
its mainworld.
"""
import random
from typing import Any, List, Optional

from .utils import Utils
from .population import generate_population_details, minimum_sustainable_tl

# Bodies that never carry a population of their own.
_UNINHABITABLE_TYPES = {'Gas Giant'}


def max_secondary_population(mainworld: Any) -> int:
    """Maximum Population code for any other world in the system: the
    mainworld's Population minus 1D (WBH p.155).

    The book also states the strict limit - one less than the mainworld's -
    and offers this roll as the quicker route, since a result of zero or
    less settles the whole system at once."""
    pop = Utils.from_eHex(getattr(mainworld, 'uwp', None)
                          and mainworld.uwp.population or 0)
    return min(pop - 1, pop - Utils.D6())


def secondary_population_code(cap: int) -> int:
    """A single body's Population code: 1D, where 5 or 6 means no population
    (the book's own method in the Zed Prime example), capped by the system's
    maximum."""
    if cap <= 0:
        return 0
    roll = Utils.D6()
    if roll >= 5:
        return 0
    return max(0, min(roll, cap))


def can_be_inhabited(body: Any, tech_level: int) -> bool:
    """Whether a world's environment can be survived at a given Tech Level
    (WBH p.155, referring to the Tech Level and Environment table)."""
    return minimum_sustainable_tl(body) <= tech_level


def _fill_physical_uwp(body: Any) -> None:
    """Copies a body's physical characteristics into its UWP.

    Planets carried these only on the body itself, so their UWP read
    `X000000-0` however large and wet the world was; moons already had
    them. Every body now presents a UWP that describes it."""
    if getattr(body, 'body_type', '') == 'Gas Giant':
        return          # a gas giant has no UWP-describable surface

    uwp = body.uwp
    size = str(getattr(body, 'size_code', '') or '0')
    if getattr(body, 'body_type', '') == 'Planetoid Belt':
        size = '0'
    uwp.size = size if len(size) == 1 else '0'
    uwp.atmosphere = str(getattr(body, 'atmosphere_code', '') or '0')
    uwp.hydrographics = str(getattr(body, 'hydrographics_code', '') or '0')


def _secondary_starport(population: int) -> str:
    """A secondary world's starport. Most are landing strips or nothing at
    all, but a well-placed one can be a genuine port - the book's own
    example gives Zed Secundus a Class C freeport."""
    roll = Utils.D6(2) + population
    if roll >= 13:
        return 'C'
    if roll >= 11:
        return 'D'
    if roll >= 8:
        return 'E'
    return 'X'


def _detail_secondary_world(body: Any, system: Any, mainworld: Any,
                            population: int) -> None:
    """Gives an inhabited secondary world its own social characteristics."""
    from .society import generate_government, generate_law_level
    from .government import generate_government_details
    from .technology import generate_technology_profile

    mainworld_tl = Utils.from_eHex(mainworld.uwp.tech_level)
    uwp = body.uwp

    _fill_physical_uwp(body)
    uwp.population = Utils.eHex(population)

    # "Affiliated with the mainworld or independent" (WBH p.155). An
    # affiliated world is a colony answering elsewhere; the book has a
    # government code for exactly that.
    affiliated = Utils.D6() <= 4
    if affiliated:
        government = 6                     # Captive Government / Colony
        body.notes.append("Secondary world: colony of the mainworld")
    else:
        government = generate_government(population)
        body.notes.append("Secondary world: independent settlement")
    uwp.government = Utils.eHex(government)
    uwp.law_level = Utils.eHex(generate_law_level(government))

    # A colony rarely outpaces the world that planted it, and nowhere can
    # fall below what its own environment demands.
    floor = minimum_sustainable_tl(body)
    if affiliated:
        tech_level = max(floor, mainworld_tl - random.randint(0, 2))
    else:
        tech_level = max(floor, mainworld_tl - random.randint(0, 4))
    uwp.tech_level = Utils.eHex(max(0, tech_level))

    uwp.starport = _secondary_starport(population)

    body.population_digit = Utils.D6() + 3
    body.is_secondary_world = True
    body.affiliated = affiliated

    generate_population_details(body)
    generate_government_details(body)
    generate_technology_profile(body)


def settlement_appeal(body: Any) -> int:
    """How much reason there is to settle a body at all.

    The handbook is explicit that a Referee should not check everything:
    "Checking every vacuum world for a minute chance of biomass will
    undoubtably result in too many worlds with life", and for populations,
    "Rather than check every significant body in the system...". Somewhere
    worth living is somewhere habitable, somewhere worth mining, or a belt
    where belters can work."""
    appeal = getattr(body, 'habitability_rating', 0) or 0
    appeal += (getattr(body, 'resource_rating', 0) or 0) // 2
    if getattr(body, 'body_type', '') == 'Planetoid Belt':
        appeal += 4          # belter communities need no atmosphere
    return appeal


def settlement_candidates(system: Any, mainworld: Any, tech_level: int,
                          limit: int = 6) -> List[Any]:
    """The bodies worth checking for a population, best prospects first."""
    candidates = []
    for body in system.all_bodies:
        if body is mainworld or getattr(body, 'is_ring', False):
            continue
        if getattr(body, 'body_type', '') in _UNINHABITABLE_TYPES:
            continue
        if not can_be_inhabited(body, tech_level):
            continue
        if settlement_appeal(body) < 4:
            continue         # nothing here worth the trip
        candidates.append(body)

    candidates.sort(key=settlement_appeal, reverse=True)
    return candidates[:limit]


def generate_secondary_populations(system: Any, limit: int = 6) -> List[Any]:
    """Applies the WBH p.155 procedure to a whole system.

    Returns the bodies that came out inhabited. Every other body still gets
    its physical characteristics written into its UWP, so a survey of the
    system describes each world even where nobody lives."""
    mainworld = system.mainworld
    if mainworld is None:
        return []

    # Every body presents a UWP describing itself, inhabited or not
    for body in system.all_bodies:
        if body is not mainworld and not getattr(body, 'is_ring', False):
            _fill_physical_uwp(body)

    mainworld_tl = Utils.from_eHex(mainworld.uwp.tech_level)
    cap = max_secondary_population(mainworld)
    if cap <= 0:
        # The book's shortcut: nothing else in this system is inhabited, and
        # no further checks are needed.
        return []

    inhabited = []
    for body in settlement_candidates(system, mainworld, mainworld_tl, limit):
        population = secondary_population_code(cap)
        if population <= 0:
            continue
        _detail_secondary_world(body, system, mainworld, population)
        inhabited.append(body)

    return inhabited
