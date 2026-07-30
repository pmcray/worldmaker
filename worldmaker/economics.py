"""World economic characteristics (WBH pp.185-199).

Implements the economic extension: importance (Ix), the resources / labour /
infrastructure / efficiency factors (Ex), resource units, gross world product,
world trade number, inequality and tariffs.
"""
import random
from typing import Any

from .utils import Utils

# WTN Starport Modifier table (WBH p.191), keyed by base WTN band
_WTN_PORT_MOD = [
    # (max_base_wtn, {port: modifier})
    (1,  {'A': 3, 'B': 2, 'C': 2, 'D': 1, 'E': 1, 'X': 0}),
    (3,  {'A': 2, 'B': 2, 'C': 1, 'D': 1, 'E': 0, 'X': 0}),
    (5,  {'A': 2, 'B': 1, 'C': 1, 'D': 0, 'E': 0, 'X': -5}),
    (7,  {'A': 1, 'B': 1, 'C': 0, 'D': 0, 'E': -1, 'X': -6}),
    (9,  {'A': 1, 'B': 0, 'C': 0, 'D': -1, 'E': -2, 'X': -7}),
    (11, {'A': 0, 'B': 0, 'C': -1, 'D': -2, 'E': -3, 'X': -8}),
    (13, {'A': 0, 'B': -1, 'C': -2, 'D': -3, 'E': -4, 'X': -9}),
    (99, {'A': 0, 'B': -2, 'C': -3, 'D': -4, 'E': -5, 'X': -10}),
]

# GWP per capita modifiers (WBH p.190)
_PORT_GWP_MOD = {'A': 1.2, 'B': 1.1, 'C': 1.0, 'D': 0.9, 'E': 0.8, 'X': 0.7}
_GOV_GWP_MOD = {0: 0.9, 1: 1.1, 2: 1.0, 3: 0.9, 4: 1.1, 5: 1.1, 6: 1.0,
                7: 0.8, 8: 1.0, 9: 0.9, 10: 0.9, 11: 0.8, 12: 0.8,
                13: 0.7, 14: 0.7, 15: 0.9}
_TRADE_GWP_MOD = {'Ri': 1.4, 'In': 1.2, 'Ht': 1.2, 'Ag': 1.1,
                  'Po': 0.7, 'Lt': 0.8, 'Ni': 0.9, 'Na': 0.9, 'Ba': 0.0}


def calculate_importance(world: Any, system: Any = None) -> int:
    """Importance (Ix), roughly -3 to +5 (WBH p.187)."""
    uwp = world.uwp
    pop = Utils.from_eHex(uwp.population)
    tl = Utils.from_eHex(uwp.tech_level)
    codes = world.trade_codes or []

    ix = 0
    if uwp.starport in ('A', 'B'):
        ix += 1
    elif uwp.starport in ('D', 'E', 'X'):
        ix -= 1

    if pop <= 6:
        ix -= 1
    elif pop >= 9:
        ix += 1

    if tl <= 8:
        ix -= 1
    elif tl <= 15:
        ix += 1
    else:
        ix += 2

    if 'Ag' in codes:
        ix += 1
    if 'In' in codes:
        ix += 1
    if 'Ri' in codes:
        ix += 1

    bases = getattr(system, 'bases', []) if system is not None else []
    if len(bases) >= 2:
        ix += 1
    if any('Xboat' in str(b) or 'Waystation' in str(b) for b in bases):
        ix += 1

    return ix


def calculate_resource_factor(world: Any, system: Any = None) -> int:
    """Resource Factor = Resource Rating + DMs (WBH p.188)."""
    base = world.resource_rating or Utils.D6(2)
    codes = world.trade_codes or []
    tl = Utils.from_eHex(world.uwp.tech_level)

    belts_and_giants = 0
    if system is not None:
        belts_and_giants = (getattr(system, 'gas_giant_count', 0)
                            + getattr(system, 'planetoid_belt_count', 0))

    factor = base
    # Space-based resources open up at TL8
    if tl >= 8:
        factor += belts_and_giants

    # Industrial and agricultural worlds deplete their endowment
    if 'In' in codes:
        factor -= (Utils.D6() - 1)
    if 'Ag' in codes:
        factor -= (Utils.D6() - 1)

    if factor < 2:
        factor = 2 + belts_and_giants
    return factor


def calculate_labour_factor(world: Any) -> int:
    """Labour Factor = Population code - 1 (WBH p.188)."""
    pop = Utils.from_eHex(world.uwp.population)
    return max(0, pop - 1)


def calculate_infrastructure(world: Any, importance: int) -> int:
    """Infrastructure Factor = Importance + DMs (WBH p.188)."""
    pop = Utils.from_eHex(world.uwp.population)
    if pop == 0:
        return 0
    infra = importance
    if 4 <= pop <= 6:
        infra += Utils.D6()
    elif pop >= 7:
        infra += Utils.D6(2)
    return max(0, infra)


def calculate_efficiency(world: Any) -> int:
    """Efficiency Factor, -5 to +5 (WBH p.188). A rolled 0 counts as +1."""
    pop = Utils.from_eHex(world.uwp.population)
    gov = Utils.from_eHex(world.uwp.government)
    law = Utils.from_eHex(world.uwp.law_level)

    if pop == 0:
        return -5

    dm = 0
    if gov in (0, 3, 6, 9, 11, 12, 15):
        dm -= 1
    elif gov in (1, 2, 4, 5, 8):
        dm += 1
    if law <= 4:
        dm += 1
    if law >= 10:
        dm -= 1

    if pop <= 6:
        eff = Utils.D6(2) - 7 + dm
    else:
        eff = (Utils.D3() + Utils.D3()) - 4 + dm

    if eff == 0:
        eff = 1
    return max(-5, min(5, eff))


def calculate_wtn(world: Any) -> int:
    """World Trade Number = Base WTN + starport modifier (WBH p.191)."""
    uwp = world.uwp
    pop = Utils.from_eHex(uwp.population)
    tl = Utils.from_eHex(uwp.tech_level)

    base = pop
    if tl <= 1:
        base -= 1
    elif tl <= 4:
        pass
    elif tl <= 8:
        base += 1
    elif tl <= 14:
        base += 2
    else:
        base += 3
    base = max(0, base)

    port = uwp.starport if uwp.starport in 'ABCDEX' else 'X'
    for ceiling, mods in _WTN_PORT_MOD:
        if base <= ceiling:
            return max(0, base + mods[port])
    return max(0, base)


def total_population(world: Any) -> int:
    """Total inhabitants from the Population code and its significant digit."""
    pop = Utils.from_eHex(world.uwp.population)
    if pop == 0:
        return 0
    p_value = getattr(world, 'population_digit', 0) or Utils.D6() + 3
    return int(p_value * (10 ** pop))


def calculate_gwp_per_capita(world: Any, infrastructure: int, resources: int,
                             efficiency: int) -> float:
    """GWP per capita in Credits (WBH p.190)."""
    uwp = world.uwp
    tl = Utils.from_eHex(uwp.tech_level)
    gov = Utils.from_eHex(uwp.government)
    codes = world.trade_codes or []

    if infrastructure <= 0:
        return 0.0

    base_value = max(2, min(resources + infrastructure, 2 * infrastructure))

    modifier = max(0.05, tl / 10.0)
    modifier *= _PORT_GWP_MOD.get(uwp.starport, 0.8)
    modifier *= _GOV_GWP_MOD.get(gov, 1.0)
    for code in codes:
        if code in _TRADE_GWP_MOD:
            modifier *= _TRADE_GWP_MOD[code]

    if efficiency >= 1:
        per_capita = 1000.0 * base_value * modifier * efficiency
    else:
        per_capita = 1000.0 * base_value * modifier / abs(efficiency - 1)
    return round(per_capita, 2)


def generate_economics(world: Any, system: Any = None) -> None:
    """Computes and records the full economic extension for a world."""
    if not world.uwp.starport:
        return

    pop = Utils.from_eHex(world.uwp.population)
    if not getattr(world, 'population_digit', 0) and pop > 0:
        world.population_digit = Utils.D6() + 3  # significant digit, 4-9

    world.importance = calculate_importance(world, system)
    world.resources = calculate_resource_factor(world, system)
    world.labour = calculate_labour_factor(world)
    world.infrastructure = calculate_infrastructure(world, world.importance)
    world.efficiency = calculate_efficiency(world)

    # Resource Units = Resources x Labour x Infrastructure x Efficiency
    world.resource_units = int(world.resources * max(1, world.labour)
                               * max(1, world.infrastructure) * world.efficiency)

    world.wtn = calculate_wtn(world)
    world.total_population = total_population(world)
    world.gwp_per_capita = calculate_gwp_per_capita(
        world, world.infrastructure, world.resources, world.efficiency)
    world.gwp = round(world.gwp_per_capita * world.total_population, 2)

    # Inequality Rating = 50 - Efficiency x 5 + (2D-7) x 2 + DMs
    inequality = 50 - world.efficiency * 5 + (Utils.D6(2) - 7) * 2
    gov = Utils.from_eHex(world.uwp.government)
    if gov in (2, 4, 5):
        inequality -= 5
    if gov in (10, 11, 12, 13, 14):
        inequality += 5
    world.inequality_rating = max(5, min(95, inequality))

    # Development score, a rough composite of wealth, tech and equality
    tl = Utils.from_eHex(world.uwp.tech_level)
    world.development_score = round(
        (tl / 15.0) * 40
        + (1 - world.inequality_rating / 100.0) * 30
        + min(30.0, world.gwp_per_capita / 2000.0), 1)

    # Tariff rate, driven by government and law level (WBH p.199)
    law = Utils.from_eHex(world.uwp.law_level)
    world.tariff_rate = round(min(0.35, max(0.0, 0.005 * law
                                            + (0.05 if gov in (7, 10, 11, 12, 13, 14) else 0.0)
                                            + random.randint(0, 4) / 100.0)), 3)

    # Economic extension string, T5 style: (resources labour infra efficiency)
    world.economic_extension = (
        f"({Utils.eHex(min(33, max(0, world.resources)))}"
        f"{Utils.eHex(min(33, max(0, world.labour)))}"
        f"{Utils.eHex(min(33, max(0, world.infrastructure)))}"
        f"{world.efficiency:+d})"
    )
