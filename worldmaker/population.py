"""Population detail: concentration, urbanisation and major cities
(WBH pp.148-156).

Expands the single Population digit of the UWP into a significant digit, a
population concentration rating, an urbanisation percentage and a set of named
major cities with populations.
"""
import random
from typing import Any, Dict, List

from .utils import Utils

PCR_DESCRIPTIONS = {
    0: "Extremely Dispersed", 1: "Highly Dispersed",
    2: "Moderately Dispersed", 3: "Partially Dispersed",
    4: "Slightly Dispersed", 5: "Slightly Concentrated",
    6: "Partially Concentrated", 7: "Moderately Concentrated",
    8: "Highly Concentrated", 9: "Extremely Concentrated",
}

_CITY_PREFIXES = ["New", "Port", "Fort", "Mount", "Lake", "Grand", "Upper",
                  "Lower", "North", "South", "East", "West", "Old"]
_CITY_STEMS = ["Haven", "Landing", "Reach", "Crossing", "Ridge", "Vale",
               "Harbour", "Terrace", "Station", "Gate", "Springs", "Falls",
               "Basin", "Heights", "Junction", "Mesa", "Delta", "Anchorage"]


def minimum_sustainable_tl(world: Any) -> int:
    """Tech Level and Environment table (WBH p.175): the lowest Tech Level at
    which a world's environment can be survived. The highest applicable
    minimum wins."""
    atm = Utils.from_eHex(getattr(world, 'atmosphere_code', 0)
                          or world.uwp.atmosphere)
    hab = getattr(world, 'habitability_rating', 10)

    minimum = 0
    if atm in (0, 1, 10):
        minimum = max(minimum, 8)
    if atm in (2, 3, 13, 14):
        minimum = max(minimum, 5)
    if atm in (4, 7, 9):
        minimum = max(minimum, 3)
    if atm == 11:
        minimum = max(minimum, 9)
    if atm == 12:
        minimum = max(minimum, 10)
    if atm in (16, 17):
        minimum = max(minimum, 14)
    if atm == 15:
        minimum = max(minimum, 8)

    if hab == 0:
        minimum = max(minimum, 8)
    elif hab <= 2:
        minimum = max(minimum, 5)
    elif hab <= 7:
        minimum = max(minimum, 3)

    return minimum


def calculate_pcr(world: Any, min_sustainable_tl: int) -> int:
    """Population Concentration Rating (WBH p.150).

    Small populations may live in a single settlement (PCR 9); otherwise roll
    1D with DMs for size, technology, government and trade codes."""
    uwp = world.uwp
    pop = Utils.from_eHex(uwp.population)
    size = Utils.from_eHex(uwp.size)
    tl = Utils.from_eHex(uwp.tech_level)
    gov = Utils.from_eHex(uwp.government)
    codes = world.trade_codes or []

    if pop == 0:
        return 0

    # A small population may be gathered into one settlement area
    if pop < 6 and Utils.D6() > pop:
        return 9

    dm = 0
    if size == 1:
        dm += 2
    elif size in (2, 3):
        dm += 1
    if any('Tidally Locked' in n for n in getattr(world, 'notes', [])):
        dm += 2  # twilight zone world
    if min_sustainable_tl >= 8:
        dm += 3
    elif min_sustainable_tl >= 3:
        dm += 1
    if pop == 8:
        dm -= 1
    elif pop >= 9:
        dm -= 2
    if gov == 7:
        dm -= 2
    if tl <= 1:
        dm -= 2
    elif tl <= 3:
        dm -= 1
    elif tl <= 9:
        dm += 1
    if 'Ag' in codes:
        dm -= 2
    if 'In' in codes:
        dm += 1
    if 'Na' in codes:
        dm -= 1
    if 'Ri' in codes:
        dm += 1

    pcr = Utils.D6() + dm
    floor = 1 if pop >= 9 else 0
    return max(floor, min(9, pcr))


def calculate_urbanisation(world: Any, pcr: int, min_sustainable_tl: int) -> int:
    """Urbanisation Percentage table (WBH p.151), with its DM minima and
    maxima applied."""
    uwp = world.uwp
    pop = Utils.from_eHex(uwp.population)
    size = Utils.from_eHex(uwp.size)
    tl = Utils.from_eHex(uwp.tech_level)
    gov = Utils.from_eHex(uwp.government)
    law = Utils.from_eHex(uwp.law_level)
    codes = world.trade_codes or []

    if pop == 0:
        return 0

    dm = 0
    if pcr <= 2:
        dm += -3 + pcr
    elif pcr >= 7:
        dm += -6 + pcr
    if min_sustainable_tl <= 3:
        dm -= 1
    if size == 0:
        dm += 2

    minimum = None
    maximum = None

    if pop == 8:
        dm += 1
    elif pop == 9:
        dm += 2
        minimum = 18 + Utils.D6()
    elif pop >= 10:
        dm += 4
        minimum = 50 + Utils.D6()

    if gov == 0:
        dm -= 2
    if law >= 9:
        dm += 1

    if tl <= 2:
        dm -= 2
        maximum = 20 + Utils.D6()
    elif tl == 3:
        dm -= 1
        maximum = 30 + Utils.D6()
    elif tl == 4:
        dm += 1
        maximum = 60 + Utils.D6()
    elif tl <= 9:
        dm += 2
        maximum = 90 + Utils.D6()
    else:
        dm += 1

    if 'Ag' in codes:
        dm -= 2
        ag_max = 90 + Utils.D6()
        maximum = ag_max if maximum is None else min(maximum, ag_max)

    roll = Utils.D6(2) + dm

    if roll <= 0:
        pct = max(0, Utils.D6() // 6)          # less than 1%
    elif roll == 1:
        pct = Utils.D6()
    elif roll == 2:
        pct = 6 + Utils.D6()
    elif roll == 3:
        pct = 12 + Utils.D6()
    elif roll == 4:
        pct = 18 + Utils.D6()
    elif roll == 5:
        pct = 22 + Utils.D6() * 2 + random.randint(1, 2)
    elif roll == 6:
        pct = 34 + Utils.D6() * 2 + random.randint(1, 2)
    elif roll == 7:
        pct = 46 + Utils.D6() * 2 + random.randint(1, 2)
    elif roll == 8:
        pct = 58 + Utils.D6() * 2 + random.randint(1, 2)
    elif roll == 9:
        pct = 70 + Utils.D6() * 2 + random.randint(1, 2)
    elif roll == 10:
        pct = 84 + Utils.D6()
    elif roll == 11:
        pct = 90 + Utils.D6()
    elif roll == 12:
        pct = 96 + Utils.D3()
    else:
        pct = 100

    # A minimum supersedes a conflicting maximum (WBH p.151)
    if maximum is not None:
        pct = min(pct, maximum)
    if minimum is not None:
        pct = max(pct, minimum)

    return max(0, min(100, int(pct)))


def _city_name(used: set) -> str:
    for _ in range(100):
        if Utils.D6() >= 5:
            name = f"{random.choice(_CITY_PREFIXES)} {random.choice(_CITY_STEMS)}"
        else:
            name = random.choice(_CITY_STEMS)
        if name not in used:
            used.add(name)
            return name
    name = f"{random.choice(_CITY_STEMS)} {len(used) + 1}"
    used.add(name)
    return name


def calculate_major_cities(world: Any, pcr: int, urban_pct: int,
                           total_population: int) -> List[Dict[str, Any]]:
    """Determines the number and population of major cities (WBH pp.153-155).

    City count is 2D - 3 + urbanisation x 20 / 3; the population split follows
    the book's cases by PCR and city count."""
    if total_population <= 0 or urban_pct <= 0:
        return []

    total_urban = int(total_population * urban_pct / 100.0)
    if total_urban <= 0:
        return []

    if pcr == 0:
        # Case 1: no true major cities; the largest settlement is modest
        largest = min(total_urban // 100, (Utils.D6() + 2) * 10000)
        if largest < 100:
            largest = max(total_urban // 10, Utils.D6() + 1)
        used = set()
        return [{'name': _city_name(used), 'population': int(largest),
                 'is_capital': True, 'starport': ''}]

    if pcr == 9 and Utils.from_eHex(world.uwp.population) < 6:
        # A small population gathered into a single settlement area: one city
        # holds all of it (WBH p.150).
        used = set()
        return [{'name': _city_name(used), 'population': int(total_urban),
                 'is_capital': True,
                 'starport': world.uwp.starport
                 if world.uwp.starport in 'ABC' else ''}]

    count = int(round(Utils.D6(2) - 3 + urban_pct * 20 / 300.0))
    count = max(1, min(10, count))  # the book suggests capping detail at ten

    # The major cities hold the bulk of the urban population; the remainder
    # lives in smaller towns.
    major_share = 0.6 + pcr * 0.04
    total_major = int(total_urban * min(0.95, major_share))
    if total_major <= 0:
        return []

    used = set()
    cities = []
    remaining = total_major

    if count == 1:
        cities.append({'name': _city_name(used), 'population': total_major})
    else:
        for i in range(count):
            if i == count - 1:
                share = remaining
            else:
                fraction = (Utils.D6() + 3) * 0.10
                fraction *= (1 + (Utils.D6(2) - 7) * 0.02)  # variance
                share = int(remaining * min(0.9, max(0.01, fraction)))
                # Every city keeps at least 1% of the major city population
                share = max(share, total_major // 100)
            share = max(1, min(share, remaining))
            cities.append({'name': _city_name(used), 'population': int(share)})
            remaining -= share
            if remaining <= 0:
                break

        if remaining > 0:
            cities[0]['population'] += remaining

    cities.sort(key=lambda c: c['population'], reverse=True)
    for i, city in enumerate(cities):
        city['is_capital'] = (i == 0)
        # The largest cities are the ones with their own port facilities
        port = world.uwp.starport
        if i == 0 and port in 'ABC':
            city['starport'] = port
        elif i < 3 and port in 'AB':
            city['starport'] = 'D'
        else:
            city['starport'] = ''

    return cities


def generate_population_details(world: Any) -> None:
    """Computes and records population concentration, urbanisation and major
    cities for a world."""
    uwp = world.uwp
    pop = Utils.from_eHex(uwp.population)

    if not getattr(world, 'population_digit', 0) and pop > 0:
        world.population_digit = Utils.D6() + 3

    world.minimum_sustainable_tl = minimum_sustainable_tl(world)

    if pop == 0:
        world.pcr = 0
        world.pcr_description = ""
        world.urbanisation_pct = 0
        world.total_population = 0
        world.urban_population = 0
        world.major_cities = []
        world.population_profile = "0-0-0-0%-0"
        return

    world.total_population = int(world.population_digit * (10 ** pop))
    world.pcr = calculate_pcr(world, world.minimum_sustainable_tl)
    world.pcr_description = PCR_DESCRIPTIONS.get(world.pcr, "")
    world.urbanisation_pct = calculate_urbanisation(
        world, world.pcr, world.minimum_sustainable_tl)
    world.urban_population = int(world.total_population
                                 * world.urbanisation_pct / 100.0)
    world.major_cities = calculate_major_cities(
        world, world.pcr, world.urbanisation_pct, world.total_population)

    # Population profile: [code]-[P value]-[PCR]-[urbanisation%]-[# cities]
    world.population_profile = (
        f"{uwp.population}-{world.population_digit}-{world.pcr}"
        f"-{world.urbanisation_pct}%-{len(world.major_cities)}")
