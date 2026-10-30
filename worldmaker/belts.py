"""Planetoid belt characteristics (WBH pp.72-75).

A belt is more than a Size 0 marker: it has a span in Orbit#s, a composition
split between metallic, stony and carbonaceous bodies, a bulk factor, a
resource rating and a count of significant bodies.
"""
import math
import random
from typing import Any, Dict, List

from .utils import Utils

# Belt Composition Percentages table (WBH p.74). Each entry returns
# (m-type%, s-type%, c-type%) for its 2D+DM row.
_COMPOSITION = {
    0:  lambda: (60 + Utils.D6() * 5, Utils.D6() * 5, 0),
    1:  lambda: (50 + Utils.D6() * 5, 5 + Utils.D6() * 5, Utils.D3()),
    2:  lambda: (40 + Utils.D6() * 5, 15 + Utils.D6() * 5, Utils.D6()),
    3:  lambda: (25 + Utils.D6() * 5, 30 + Utils.D6() * 5, Utils.D6()),
    4:  lambda: (15 + Utils.D6() * 5, 35 + Utils.D6() * 5, 5 + Utils.D6()),
    5:  lambda: (5 + Utils.D6() * 5, 40 + Utils.D6() * 5, 5 + Utils.D6() * 2),
    6:  lambda: (Utils.D6() * 5, 40 + Utils.D6() * 5, Utils.D6() * 5),
    7:  lambda: (5 + Utils.D6() * 2, 35 + Utils.D6() * 5, 10 + Utils.D6() * 5),
    8:  lambda: (5 + Utils.D6(), 30 + Utils.D6() * 5, 20 + Utils.D6() * 5),
    9:  lambda: (Utils.D6(), 15 + Utils.D6() * 5, 40 + Utils.D6() * 5),
    10: lambda: (Utils.D6(), 5 + Utils.D6() * 5, 50 + Utils.D6() * 5),
    11: lambda: (Utils.D3(), 5 + Utils.D6() * 2, 60 + Utils.D6() * 5),
    12: lambda: (0, Utils.D6(), 70 + Utils.D6() * 5),
}


def calculate_belt_span(belt: Any, system: Any, inner_is_gas_giant: bool = False,
                        outer_is_gas_giant: bool = False,
                        is_outermost: bool = False) -> float:
    """Belt Span = Spread x (2D - 2) / 10 Orbit#s, with DMs for neighbouring
    gas giants and for occupying the outermost slot (WBH p.72)."""
    spread = getattr(system, 'spread', 0.0) or (Utils.D6(2) * 0.1)

    dm = 0
    if inner_is_gas_giant or outer_is_gas_giant:
        dm -= 1
    if is_outermost:
        dm += 3

    roll = max(0, Utils.D6(2) - 2 + dm)
    return round(max(0.01, spread * roll / 10.0), 4)


def calculate_belt_composition(belt: Any, hzco: float) -> Dict[str, int]:
    """Belt Composition Percentages (WBH p.74).

    Belts inside the habitable zone are metal-rich; those well beyond it are
    dominated by ices and carbonaceous bodies."""
    dm = 0
    orbit = getattr(belt, 'orbit_num', 0.0) or 0.0
    if hzco and orbit < hzco:
        dm -= 4
    elif hzco and orbit > hzco + 2:
        dm += 4

    row = min(12, max(0, Utils.D6(2) + dm))
    m_type, s_type, c_type = _COMPOSITION[row]()

    # Excess over 100% comes off m-type first, then s-type (WBH p.74)
    total = m_type + s_type + c_type
    if total > 100:
        excess = total - 100
        take = min(excess, m_type)
        m_type -= take
        excess -= take
        if excess:
            s_type = max(0, s_type - excess)

    other = max(0, 100 - (m_type + s_type + c_type))
    return {'m_type': int(m_type), 's_type': int(s_type),
            'c_type': int(c_type), 'other': int(other)}


def calculate_belt_bulk(composition: Dict[str, int], system_age_gyr: float) -> int:
    """Belt Bulk = 2D2 + DMs, minimum 1 (WBH p.74).

    Older belts are thinner; carbonaceous belts are bulkier."""
    base = random.randint(1, 2) + random.randint(1, 2)
    dm = -math.floor(max(0.0, system_age_gyr) / 2.0)
    dm += math.floor(composition['c_type'] / 10.0)
    return max(1, base + dm)


def calculate_belt_resource_rating(composition: Dict[str, int], bulk: int,
                                   industrial_tl8: bool = False) -> int:
    """Resource Rating = 2D - 7 + bulk + composition DMs (WBH p.74).

    Metal content helps, carbonaceous content hurts, and an industrialised
    system will already have worked the belt over."""
    dm = bulk
    dm += math.floor(composition['m_type'] / 10.0)
    dm -= math.ceil(composition['c_type'] / 10.0)

    rating = Utils.D6(2) - 7 + dm
    if industrial_tl8:
        rating -= Utils.D6()
    return max(1, rating)


def calculate_significant_bodies(bulk: int, span: float) -> Dict[str, int]:
    """The count of Size 1 and Size S bodies large enough to matter
    (WBH p.75)."""
    size_1 = max(0, Utils.D6(2) - 10 + bulk // 2)
    size_s = max(0, Utils.D6(2) - 4 + bulk)
    return {'size_1_bodies': size_1, 'size_s_bodies': size_s}


def detail_belt(belt: Any, system: Any, hzco: float = 0.0,
                inner_is_gas_giant: bool = False,
                outer_is_gas_giant: bool = False,
                is_outermost: bool = False) -> None:
    """Fills in the full belt profile for a planetoid belt."""
    belt.belt_span = calculate_belt_span(
        belt, system, inner_is_gas_giant, outer_is_gas_giant, is_outermost)
    belt.belt_composition = calculate_belt_composition(belt, hzco)
    belt.belt_bulk = calculate_belt_bulk(
        belt.belt_composition, getattr(system, 'age_gyr', 0.0))
    belt.resource_rating = calculate_belt_resource_rating(
        belt.belt_composition, belt.belt_bulk)

    bodies = calculate_significant_bodies(belt.belt_bulk, belt.belt_span)
    belt.size_1_bodies = bodies['size_1_bodies']
    belt.size_s_bodies = bodies['size_s_bodies']

    comp = belt.belt_composition
    # Belt profile: [span]-[composition%s]-[bulk]-[resource]-[#Size1]-[#Size0]
    belt.belt_profile = (
        f"{belt.belt_span:.3f}-"
        f"m{comp['m_type']}/s{comp['s_type']}/c{comp['c_type']}-"
        f"{belt.belt_bulk}-{Utils.eHex(min(33, belt.resource_rating))}-"
        f"{belt.size_1_bodies}-{belt.size_s_bodies}"
    )

    belt.notes.append(
        f"Belt span {belt.belt_span:.3f} Orbit#s; "
        f"{comp['m_type']}% metallic, {comp['s_type']}% stony, "
        f"{comp['c_type']}% carbonaceous; bulk {belt.belt_bulk}")


def detail_system_belts(system: Any) -> None:
    """Details every planetoid belt in a system, taking neighbouring bodies
    into account."""
    primary = getattr(system, 'primary_star', None)
    hzco = primary.hzco if primary else 0.0

    for star in system.stars:
        if star.is_composite:
            continue
        bodies = sorted(star.orbiting_bodies, key=lambda b: b.orbit_num)
        for i, body in enumerate(bodies):
            if body.body_type != 'Planetoid Belt':
                continue
            inner = bodies[i - 1] if i > 0 else None
            outer = bodies[i + 1] if i + 1 < len(bodies) else None
            detail_belt(
                body, system, hzco,
                inner_is_gas_giant=bool(inner and inner.body_type == 'Gas Giant'),
                outer_is_gas_giant=bool(outer and outer.body_type == 'Gas Giant'),
                is_outermost=(outer is None),
            )
