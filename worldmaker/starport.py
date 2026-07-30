"""Starport facilities and world military forces (WBH pp.193-208).

Expands the starport class letter into the facilities, capacities and bases
the Starport Facilities table defines, and derives the world's military
branches, their relative effect and its total military budget.
"""
import math
import random
from typing import Any, Dict, List

from .utils import Utils

# Starport Facilities table (WBH p.194): the target number a 2D roll must
# meet for each facility, plus the fuel and repair services available.
STARPORT_FACILITIES = {
    'A': {'highport': 6,  'fuel': 'Refined',   'repair': 'Overhaul',
          'shipyard': 'Starship',  'naval': 8,  'scout': 10, 'military': 8,
          'corsair': None},
    'B': {'highport': 8,  'fuel': 'Refined',   'repair': 'Overhaul',
          'shipyard': 'Spacecraft', 'naval': 8, 'scout': 9,  'military': 8,
          'corsair': None},
    'C': {'highport': 10, 'fuel': 'Unrefined', 'repair': 'Major',
          'shipyard': 'Small craft', 'naval': None, 'scout': 9, 'military': 10,
          'corsair': None},
    'D': {'highport': 12, 'fuel': 'Unrefined', 'repair': 'Minor',
          'shipyard': None, 'naval': None, 'scout': None, 'military': 8,
          'corsair': 12},
    'E': {'highport': None, 'fuel': None, 'repair': None,
          'shipyard': None, 'naval': None, 'scout': None, 'military': None,
          'corsair': 10},
    'X': {'highport': None, 'fuel': None, 'repair': None,
          'shipyard': None, 'naval': None, 'scout': None, 'military': None,
          'corsair': 10},
}

# Starport capacities in tons (WBH p.196)
STARPORT_CAPACITY = {
    'A': {'berthing': 'Improved', 'docking': 100000, 'berthing_cost': 1000,
          'bay_size': 2500, 'commercial': 25000, 'residential': 10000,
          'shipyard_tons': 25000},
    'B': {'berthing': 'Civilian', 'docking': 50000, 'berthing_cost': 500,
          'bay_size': 1000, 'commercial': 5000, 'residential': 2500,
          'shipyard_tons': 10000},
    'C': {'berthing': 'Civilian', 'docking': 20000, 'berthing_cost': 100,
          'bay_size': 0, 'commercial': 100, 'residential': 100,
          'shipyard_tons': 200},
    'D': {'berthing': 'Basic', 'docking': 400, 'berthing_cost': 10,
          'bay_size': 0, 'commercial': 100, 'residential': 0,
          'shipyard_tons': 0},
    'E': {'berthing': '', 'docking': 0, 'berthing_cost': 0, 'bay_size': 0,
          'commercial': 0, 'residential': 0, 'shipyard_tons': 0},
    'X': {'berthing': '', 'docking': 0, 'berthing_cost': 0, 'bay_size': 0,
          'commercial': 0, 'residential': 0, 'shipyard_tons': 0},
}

READINESS_MODIFIERS = {
    'Complacent peace': 0.5,
    'Low threat level': 0.75,
    'Normal readiness': 1.0,
    'Heightened tensions': 1.2,
    'War or insurgency': 2.0,
    'Total war': 5.0,
}


def generate_starport_facilities(world: Any, system: Any = None) -> Dict[str, Any]:
    """Rolls the facilities present at a world's starport (WBH p.194)."""
    uwp = world.uwp
    port = uwp.starport if uwp.starport in STARPORT_FACILITIES else 'X'
    table = STARPORT_FACILITIES[port]
    pop = Utils.from_eHex(uwp.population)
    tl = Utils.from_eHex(uwp.tech_level)
    law = Utils.from_eHex(uwp.law_level)

    facilities: Dict[str, Any] = {
        'class': port,
        'fuel': table['fuel'] or 'None',
        'repair': table['repair'] or 'None',
        'shipyard_capability': table['shipyard'] or 'None',
    }

    # Highport
    highport_dm = 0
    if pop >= 9:
        highport_dm += 1
    if 9 <= tl <= 11:
        highport_dm += 1
    elif tl >= 12:
        highport_dm += 2
    facilities['highport'] = bool(
        table['highport'] and Utils.D6(2) + highport_dm >= table['highport'])

    # Bases
    bases: List[str] = []
    if table['naval'] and Utils.D6(2) >= table['naval']:
        bases.append('Naval')
    if table['scout'] and Utils.D6(2) >= table['scout']:
        # An Imperial scout base on an express route may be a waystation
        bases.append('Waystation' if Utils.D6() == 6 else 'Scout')
    if table['military'] and Utils.D6(2) >= table['military']:
        bases.append('Military')

    if table['corsair']:
        corsair_dm = 0
        if law == 0:
            corsair_dm += 2
        elif law >= 2:
            corsair_dm -= 2
        if Utils.D6(2) + corsair_dm >= table['corsair']:
            bases.append('Corsair')

    facilities['bases'] = bases

    # Capacities
    cap = STARPORT_CAPACITY[port]
    facilities['berthing_quality'] = cap['berthing']
    facilities['berthing_cost_cr'] = cap['berthing_cost'] * Utils.D6() if cap['berthing_cost'] else 0
    facilities['docking_capacity_tons'] = cap['docking']
    facilities['largest_bay_tons'] = cap['bay_size']
    facilities['commercial_zone_tons'] = cap['commercial']
    facilities['residential_zone_tons'] = cap['residential']

    # Shipyard: annual output is at best half the yard tonnage, and the
    # largest hull is about 10% of it (WBH p.196)
    yard = cap['shipyard_tons']
    facilities['shipyard_tons'] = yard
    facilities['shipyard_annual_output_tons'] = yard // 2
    facilities['largest_hull_tons'] = yard // 10

    # Traffic scales with importance and trade
    wtn = getattr(world, 'wtn', 0)
    importance = getattr(world, 'importance', 0)
    facilities['annual_traffic_ships'] = max(
        0, int((wtn ** 2) * (2 + max(0, importance)) * 1.5))

    return facilities


def _branch_effect(base: int, dms: int) -> int:
    """A branch's relative Effect, floored at 1 where the branch exists."""
    return max(1, base + dms)


def generate_military(world: Any, system: Any = None,
                      readiness: str = None) -> Dict[str, Any]:
    """Determines a world's military branches, their effect and its budget
    (WBH pp.200-207)."""
    uwp = world.uwp
    pop = Utils.from_eHex(uwp.population)
    gov = Utils.from_eHex(uwp.government)
    law = Utils.from_eHex(uwp.law_level)
    tl = Utils.from_eHex(uwp.tech_level)
    hyd = Utils.from_eHex(uwp.hydrographics)
    atm = Utils.from_eHex(uwp.atmosphere)
    port = uwp.starport
    pcr = getattr(world, 'pcr', 5)
    cp = getattr(world, 'cultural_profile', None)
    militancy = getattr(cp, 'militancy', 5) if cp else 5
    bases = getattr(system, 'bases', []) if system is not None else []

    branches: Dict[str, int] = {}

    if pop == 0:
        world.military_branches = {}
        world.military_budget_pct = 0.0
        world.military_budget = 0.0
        world.state_of_readiness = 'None'
        world.military_profile = "------:0.00%"
        return {}

    # Enforcement always exists: Effect = 3 + DMs
    dm = 0
    if gov == 0:
        dm -= 5
    elif gov == 11:
        dm += 2
    if law == 0:
        dm -= 4
    elif law == 1:
        dm -= 2
    elif law == 2:
        dm -= 1
    elif 9 <= law <= 11:
        dm += 2
    elif law >= 12:
        dm += 4
    if pcr <= 4:
        dm += 2
    branches['Enforcement'] = _branch_effect(3, dm)

    # Militia: low Law Level, dispersed and rural worlds
    if law <= 6 and Utils.D6(2) + (2 if law <= 3 else 0) >= 7:
        branches['Militia'] = _branch_effect(2, (1 if pcr <= 4 else 0)
                                             + max(0, militancy - 5))

    # Army: scales with population and militancy
    if pop >= 4 and Utils.D6(2) + max(0, militancy - 5) >= 7:
        branches['Army'] = _branch_effect(pop - 2, max(0, militancy - 5))

    # Wet Navy needs seas
    if hyd >= 2 and pop >= 5 and Utils.D6(2) >= 8:
        branches['Wet Navy'] = _branch_effect(max(1, hyd - 3),
                                              max(0, militancy - 5))

    # Air Force needs an atmosphere and the technology to use it
    if 2 <= atm <= 14 and tl >= 5 and pop >= 5 and Utils.D6(2) >= 7:
        branches['Air Force'] = _branch_effect(max(1, tl - 5),
                                               max(0, militancy - 5))

    # System Defence needs spaceflight
    if tl >= 8 and pop >= 5 and Utils.D6(2) + (2 if port in 'AB' else 0) >= 8:
        branches['System Defence'] = _branch_effect(max(1, tl - 7), 0)

    # Navy and Marines need jump capability and industry
    if tl >= 9 and pop >= 7 and port in 'ABC' and Utils.D6(2) >= 9:
        branches['Navy'] = _branch_effect(max(1, tl - 8),
                                          2 if 'Naval' in bases else 0)
        if Utils.D6(2) >= 8:
            branches['Marines'] = _branch_effect(max(1, tl - 9), 0)

    # Basic Military Budget% = 2% x (1 + Efficiency/10) x (1 + (2D-7+DMs)/10)
    efficiency = getattr(world, 'efficiency', 0)
    budget_dm = 0
    if gov in (0, 2, 4):
        budget_dm -= 2
    elif gov == 5:
        budget_dm += 1
    elif gov == 9:
        budget_dm -= 1
    elif gov in (10, 15):
        budget_dm += 3
    elif gov in (11, 12, 14):
        budget_dm += 2
    if law >= 12:
        budget_dm += 2
    if 'Military' in bases:
        budget_dm += 4
    if 'Naval' in bases:
        budget_dm += 2
    budget_dm += militancy - 5
    budget_dm += -4 + sum(branches.values()) // 10

    variance = max(-9, Utils.D6(2) - 7 + budget_dm)
    pct = 2.0 * (1 + efficiency / 10.0) * (1 + variance / 10.0)
    pct = max(0.0, pct)

    if readiness is None:
        roll = Utils.D6(2)
        if roll <= 3:
            readiness = 'Complacent peace'
        elif roll <= 5:
            readiness = 'Low threat level'
        elif roll <= 9:
            readiness = 'Normal readiness'
        elif roll <= 11:
            readiness = 'Heightened tensions'
        else:
            readiness = 'War or insurgency'

    modifier = READINESS_MODIFIERS.get(readiness, 1.0)
    gwp = getattr(world, 'gwp', 0.0) or 0.0

    world.military_branches = branches
    world.state_of_readiness = readiness
    world.military_budget_pct = round(pct * modifier, 3)
    world.military_budget = round(gwp * pct * modifier / 100.0, 2)

    # Military profile EMAWF-SNM:X.XX%
    def mark(name, letter):
        return letter if name in branches else '-'

    world.military_profile = (
        f"{mark('Enforcement', 'E')}{mark('Militia', 'M')}"
        f"{mark('Army', 'A')}{mark('Wet Navy', 'W')}{mark('Air Force', 'F')}"
        f"-{mark('System Defence', 'S')}{mark('Navy', 'N')}"
        f"{mark('Marines', 'M')}"
        f":{world.military_budget_pct:.2f}%")

    return branches


def detail_starport_and_military(world: Any, system: Any = None) -> None:
    """Records starport facilities and military forces on a world."""
    world.starport_facilities = generate_starport_facilities(world, system)
    generate_military(world, system)

    # A world's own starport rolls are the authoritative base list for its
    # system, since they use the full Starport Facilities table.
    if system is not None:
        system.bases = list(world.starport_facilities['bases'])
        if world.starport_facilities['highport']:
            system.has_highport = True
