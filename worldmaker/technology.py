"""The world technology profile (WBH pp.173-180).

The UWP's single Tech Level digit is the world's high common Tech Level. This
module derives the low common Tech Level and the subcategory levels the book
records as H-L-QQQQQ-TTTT-MM-N: quality of life (energy, electronics,
manufacturing, medical, environmental), transport (land, sea, air, space),
military (personal, heavy) and novelty.
"""
from typing import Any, Dict

from .utils import Utils

# Tech Level Modifier table (WBH p.176)
_TLM = {2: -3, 3: -2, 4: -1, 5: 0, 6: 0, 7: 0, 8: 0, 9: 0,
        10: 1, 11: 2, 12: 3}


def tlm() -> int:
    """A Tech Level Modifier: 2D on the TLM table."""
    return _TLM.get(Utils.D6(2), 0)


def _bounded(value: int, upper: int, lower: int) -> int:
    """Applies a subcategory's upper and lower bounds, rounding down. If the
    bounds are inverted, the upper bound wins."""
    upper = int(upper)
    lower = int(lower)
    if lower > upper:
        lower = upper
    return max(0, max(lower, min(upper, int(value))))


def generate_technology_profile(world: Any) -> Dict[str, int]:
    """Computes the full technology profile for a world.

    Returns the subcategory levels and records them on the world, along with
    the profile string H-L-QQQQQ-TTTT-MM-N."""
    uwp = world.uwp
    high = Utils.from_eHex(uwp.tech_level)
    pop = Utils.from_eHex(uwp.population)
    atm = Utils.from_eHex(uwp.atmosphere)
    hyd = Utils.from_eHex(uwp.hydrographics)
    law_weapons = getattr(world, 'law_weapons', Utils.from_eHex(uwp.law_level))

    starport_dm = {'A': 2, 'B': 1, 'C': 0, 'D': -1, 'E': -2, 'X': -3}.get(
        uwp.starport, 0)

    # An uninhabited world has no technology of its own
    if pop == 0:
        world.tech_high = high
        world.tech_low = 0
        for name in ('tech_energy', 'tech_electronics', 'tech_manufacturing',
                     'tech_medical', 'tech_environmental', 'tech_land',
                     'tech_sea', 'tech_air', 'tech_space', 'tech_personal',
                     'tech_heavy', 'tech_novelty'):
            setattr(world, name, 0)
        world.technology_profile = f"{Utils.eHex(high)}-0-00000-0000-00-0"
        return {}

    # Low common Tech Level: what is available to the general population
    low = _bounded(high + tlm() - 1, high, 0)

    # --- Quality of life -------------------------------------------------
    # Energy: the foundation, bounded by TL x 1.2 above and TL / 2 below
    energy = _bounded(high + tlm(), high * 1.2, high / 2)

    # Electronics: within one above energy and three below
    electronics = _bounded(high + tlm(), energy + 1, energy - 3)

    # Manufacturing: bounded by the greater of energy or electronics
    manufacturing = _bounded(high + tlm(), max(energy, electronics),
                             electronics - 2)

    # Medical: built on electronics, floored by the starport's access to
    # offworld medicine
    medical = _bounded(electronics + tlm(), electronics,
                       max(0, starport_dm))

    # Environmental: built on manufacturing, and a hostile world needs it
    env_dm = tlm()
    if atm in (0, 1, 10, 11, 12) or atm >= 15:
        env_dm += 2
    environmental = _bounded(manufacturing + env_dm, energy, energy - 5)

    # --- Transport -------------------------------------------------------
    land = _bounded(energy + tlm(), energy, electronics - 5)

    # No seas, no maritime technology
    sea_lower = 0 if hyd == 0 else electronics - 5
    sea_upper = 0 if hyd == 0 else energy
    sea = _bounded(energy + tlm(), sea_upper, sea_lower)

    air = _bounded(energy + tlm(), energy, electronics - 5)
    if atm == 0 and high <= 5:
        air = 0  # nothing to fly in, and no technology to fake it

    space = _bounded(manufacturing + tlm(),
                     min(energy, manufacturing),
                     min(energy - 3, manufacturing - 3))

    # --- Military --------------------------------------------------------
    personal_lower = manufacturing if law_weapons == 0 else 0
    personal = _bounded(manufacturing + tlm(), electronics, personal_lower)
    heavy = _bounded(manufacturing + tlm(), manufacturing, 0)

    # --- Novelty ---------------------------------------------------------
    # How far the world's cutting edge runs ahead of common availability
    novelty = _bounded(high + tlm() + (1 if pop >= 9 else 0), high + 2, high)

    world.tech_high = high
    world.tech_low = low
    world.tech_energy = energy
    world.tech_electronics = electronics
    world.tech_manufacturing = manufacturing
    world.tech_medical = medical
    world.tech_environmental = environmental
    world.tech_land = land
    world.tech_sea = sea
    world.tech_air = air
    world.tech_space = space
    world.tech_personal = personal
    world.tech_heavy = heavy
    world.tech_novelty = novelty

    e = Utils.eHex
    world.technology_profile = (
        f"{e(high)}-{e(low)}-"
        f"{e(energy)}{e(electronics)}{e(manufacturing)}{e(medical)}{e(environmental)}-"
        f"{e(land)}{e(sea)}{e(air)}{e(space)}-"
        f"{e(personal)}{e(heavy)}-{e(novelty)}"
    )

    return {
        'high': high, 'low': low, 'energy': energy,
        'electronics': electronics, 'manufacturing': manufacturing,
        'medical': medical, 'environmental': environmental,
        'land': land, 'sea': sea, 'air': air, 'space': space,
        'personal': personal, 'heavy': heavy, 'novelty': novelty,
    }
