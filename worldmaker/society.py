import random
from typing import List, Dict, Any, Tuple, Optional

from .classes import UWP, PlanetaryBody, CulturalProfile
from .utils import Utils
from .data import DATA

def generate_population(dm: int = 0) -> int:
    """Generates population code with an optional DM."""
    return max(0, Utils.D6(2) - 2 + dm)

def generate_government(population: int) -> int:
    """Generates government code."""
    if population == 0:
        return 0
    return max(0, Utils.D6(2) - 7 + population)

def generate_law_level(government: int) -> int:
    """Generates law level code."""
    if government == 0:
        return 0
    return max(0, Utils.D6(2) - 7 + government)

def generate_starport(population: int) -> str:
    """Generates starport code."""
    roll = Utils.D6(2)
    # Test the tighter bounds first, or the Pop<=2 case never fires.
    if population >= 10:
        roll += 2
    elif population >= 8:
        roll += 1
    elif population <= 2:
        roll -= 2
    elif population <= 4:
        roll -= 1

    if roll <= 2:
        return 'X'
    elif roll <= 4:
        return 'E'
    elif roll <= 6:
        return 'D'
    elif roll <= 8:
        return 'C'
    elif roll <= 10:
        return 'B'
    else:
        return 'A'

def generate_tech_level(starport: str, size: int, atmosphere: int, hydrographics: int,
                        population: int, government: int = 0) -> int:
    """Generates base tech level code."""
    roll = Utils.D6(1)
    dm = 0
    if starport == 'A':
        dm += 6
    elif starport == 'B':
        dm += 4
    elif starport == 'C':
        dm += 2
    elif starport == 'X':
        dm -= 4
    
    if size <= 1:
        dm += 2
    elif size <= 4:
        dm += 1
        
    if atmosphere <= 3 or atmosphere >= 10:
        dm += 1
        
    if hydrographics == 0 or hydrographics == 9:
        dm += 1
    elif hydrographics == 10:
        dm += 2
        
    if 1 <= population <= 5 or population == 8:
        dm += 1
    elif population == 9:
        dm += 2
    elif population >= 10:
        dm += 4

    # Government DMs (Mongoose core Tech Level table)
    if government in (0, 5):
        dm += 1
    elif government == 7:
        dm += 2
    elif government in (13, 14):
        dm -= 2

    return max(0, roll + dm)

def generate_expanded_tech_matrix(uwp: UWP, world: PlanetaryBody):
    """Calculates a 6-field technological matrix: Spaceflight, Energy,
    Transport, Medical, Environment and Personal Gear.

    Note: this is this project's own construct, not a WBH procedure. The
    handbook's equivalent is the technology profile on p.173
    (H-L-QQQQQ-TTTT-MM-N), which is not implemented."""
    base_tl = Utils.from_eHex(uwp.tech_level)
    atm = Utils.from_eHex(uwp.atmosphere)
    pop = Utils.from_eHex(uwp.population)
    # A mainworld may be a planet or a significant moon; both carry a size code
    # while only planets carry a body_type.
    is_solid = getattr(world, 'body_type', 'Terrestrial') in ('Terrestrial', '')
    size = Utils.from_eHex(world.size_code) if is_solid else 0

    # 1. Spaceflight (correlates with Starport infrastructure)
    sf_dm = 0
    if uwp.starport == 'A': sf_dm += 1
    elif uwp.starport in ['D', 'E']: sf_dm -= 1
    elif uwp.starport == 'X': sf_dm -= 3
    uwp.tl_spaceflight = max(0, base_tl + sf_dm)

    # 2. Energy (correlates with atmospheric survivability / energy needs)
    eg_dm = 0
    if atm in [0, 1, 10, 11, 12]: eg_dm += 1 # Harsh environment requires high power isolation
    uwp.tl_energy = max(0, base_tl + eg_dm)

    # 3. Transport (correlates with world size/gravity density)
    tr_dm = 0
    if size >= 10: tr_dm += 1 # Larger worlds require more robust vehicles
    if Utils.from_eHex(uwp.hydrographics) >= 8: tr_dm += 1 # Liquid water requires maritime transport tech
    uwp.tl_transport = max(0, base_tl + tr_dm)

    # 4. Medical (correlates with population concentrations and biosphere complexities)
    md_dm = 0
    if pop >= 9: md_dm += 1
    if pop <= 3: md_dm -= 1
    uwp.tl_medical = max(0, base_tl + md_dm)

    # 5. Environment (correlates directly with hostile atmospheres)
    ev_dm = 0
    if atm in [2, 3, 13, 14, 15]: ev_dm += 2 # Highly toxic / hostile atmospheres require closed environmental tech
    uwp.tl_environment = max(0, base_tl + ev_dm)

    # 6. Personal Gear (personal protection and small weaponry - correlates with law levels)
    pg_dm = 0
    gov = Utils.from_eHex(uwp.government)
    if gov in [2, 7]: pg_dm -= 1 # Strict centralized states restrict personal gear tech advancement
    uwp.tl_personal = max(0, base_tl + pg_dm)

def generate_mainworld_uwp(population_dm: int = 0, size: int = None,
                           atmosphere: int = None, hydrographics: int = None) -> UWP:
    """Generates a full UWP for a mainworld.

    Pass size/atmosphere/hydrographics to derive the UWP from a world that has
    already been generated physically (the normal path - WBH's continuation of
    the physical characteristics into the social ones). Omit them to roll a
    standalone world."""
    uwp = UWP()

    from .geophysics import generate_atmosphere, generate_hydrographics

    if size is None:
        size_roll = Utils.D6(2) - 2
    else:
        size_roll = size
    uwp.size = Utils.eHex(size_roll)

    atmosphere_val = generate_atmosphere(size_roll) if atmosphere is None else atmosphere
    uwp.atmosphere = Utils.eHex(atmosphere_val)

    hydrographics_val = (generate_hydrographics(size_roll, atmosphere_val)
                         if hydrographics is None else hydrographics)
    uwp.hydrographics = Utils.eHex(hydrographics_val)

    population_val = generate_population(population_dm)
    uwp.population = Utils.eHex(population_val)
    
    government_val = generate_government(population_val)
    uwp.government = Utils.eHex(government_val)
    
    law_level_val = generate_law_level(government_val)
    uwp.law_level = Utils.eHex(law_level_val)
    
    starport_val = generate_starport(population_val)
    uwp.starport = starport_val
    
    tech_level_val = generate_tech_level(starport_val, size_roll, atmosphere_val,
                                         hydrographics_val, population_val, government_val)
    uwp.tech_level = Utils.eHex(tech_level_val)
    
    return uwp

def generate_trade_codes(world: PlanetaryBody):
    """Determines trade codes for a world based on its UWP."""
    if not world.is_mainworld and not world.uwp.starport:
        return 

    uwp = world.uwp
    size = Utils.from_eHex(uwp.size)
    atm = Utils.from_eHex(uwp.atmosphere)
    hyd = Utils.from_eHex(uwp.hydrographics)
    pop = Utils.from_eHex(uwp.population)
    gov = Utils.from_eHex(uwp.government)
    law = Utils.from_eHex(uwp.law_level)
    tl = Utils.from_eHex(uwp.tech_level)

    world.trade_codes = []
    for tc in DATA['trade_codes']:
        match = True
        if tc['size'] is not None and size not in tc['size']: match = False
        if tc['atm'] is not None and atm not in tc['atm']: match = False
        if tc['hyd'] is not None and hyd not in tc['hyd']: match = False
        if tc['pop'] is not None and pop not in tc['pop']: match = False
        if tc['gov'] is not None and gov not in tc['gov']: match = False
        if tc['law'] is not None and law not in tc['law']: match = False
        if tc['tl'] is not None and tl not in tc['tl']: match = False
        
        if match:
            world.trade_codes.append(tc['code'])

def generate_cultural_profile(uwp: UWP) -> CulturalProfile:
    """Generates the eight cultural traits (WBH pp.182-185). Every trait is
    2D + DMs, with a minimum of 1 for an inhabited world."""
    pop = Utils.from_eHex(uwp.population)
    gov = Utils.from_eHex(uwp.government)
    law = Utils.from_eHex(uwp.law_level)
    tl = Utils.from_eHex(uwp.tech_level)
    port = uwp.starport

    if pop == 0:
        return CulturalProfile()

    def trait(*dms: int) -> int:
        return max(1, Utils.D6(2) + sum(dms))

    # Diversity
    d_dm = 0
    if 1 <= pop <= 5: d_dm -= 2
    if pop >= 9: d_dm += 2
    if gov <= 2: d_dm += 1
    if gov == 7: d_dm += 4
    if gov >= 13: d_dm -= 4
    if law <= 4: d_dm += 1
    if law >= 10: d_dm -= 1

    # Xenophilia
    x_dm = 0
    if 1 <= pop <= 5: x_dm -= 1
    if pop >= 9: x_dm += 2
    if gov in (13, 14): x_dm -= 2
    if law >= 10: x_dm -= 2
    if port == 'A': x_dm += 2
    elif port == 'B': x_dm += 1

    # Uniqueness - isolation breeds distinctiveness
    u_dm = 0
    if port in ('A', 'B'): u_dm -= 2
    elif port in ('X', 'E'): u_dm += 2
    if pop <= 4: u_dm += 1

    # Symbology
    s_dm = 0
    if gov in (6, 7): s_dm += 1
    if tl <= 5: s_dm += 1
    if tl >= 12: s_dm -= 1

    # Cohesion - the inverse pressures to diversity
    c_dm = 0
    if gov == 7: c_dm -= 4
    if gov >= 10: c_dm += 2
    if law >= 9: c_dm += 1
    if pop >= 9: c_dm -= 1

    # Progressiveness
    p_dm = 0
    if tl >= 12: p_dm += 2
    if tl <= 5: p_dm -= 2
    if gov in (13, 14): p_dm -= 2
    if law >= 10: p_dm -= 1

    # Expansionism
    e_dm = 0
    if port == 'A': e_dm += 2
    elif port == 'B': e_dm += 1
    if pop >= 9: e_dm += 1
    if pop <= 3: e_dm -= 2
    if tl >= 10: e_dm += 1

    # Militancy
    m_dm = 0
    if law >= 9: m_dm += 1
    if law <= 2: m_dm -= 1
    if gov in (10, 11, 12, 13, 14): m_dm += 2
    if gov == 7: m_dm += 1

    return CulturalProfile(
        diversity=trait(d_dm),
        xenophilia=trait(x_dm),
        uniqueness=trait(u_dm),
        symbology=trait(s_dm),
        cohesion=trait(c_dm),
        progressiveness=trait(p_dm),
        expansionism=trait(e_dm),
        militancy=trait(m_dm),
    )

def generate_social_details(world: PlanetaryBody):
    """Generates WBH detailed social customs, cultural profiles, and factions."""
    if not world.is_mainworld or Utils.from_eHex(world.uwp.population) == 0:
        return

    world.cultural_profile = generate_cultural_profile(world.uwp)

    # Customs and Taboos
    customs = [
        "Ritualized greeting protocols using hand gestures.",
        "Strict dietary customs forbidding certain synthetic proteins.",
        "Public isolation during religious or lunar alignments.",
        "Corporate branding integrated directly into social status.",
        "Highly decentralized cybernetic-linked group negotiations.",
        "Technological tools are treated as sacred relics.",
        "Linguistic honorifics dictated by familial profession."
    ]
    taboos = [
        "Speaking of off-world politics in public squares.",
        "Wasting potable water or artificial atmospheric gases.",
        "Utilizing unregistered artificial intelligence tools.",
        "Disrespecting naval or scout representatives."
    ]
    world.notes.append(f"Cultural Custom: {random.choice(customs)}")
    world.notes.append(f"Cultural Taboo: {random.choice(taboos)}")

    # Factions (WBH p. 192)
    num_factions = max(1, Utils.D3())
    ideologies = ["Democratic Reformists", "Corporate Hegemony", "Religious Zealots", "Anarchist Separatists", "Military Junta", "Technological Technocrats"]
    sizes = ["Tiny", "Minor", "Major"]
    influences = ["Low", "High"]
    for i in range(num_factions):
        fid = random.choice(ideologies)
        fsz = random.choice(sizes)
        finf = random.choice(influences)
        world.notes.append(f"Faction {i+1}: {fid} (Size: {fsz}, Influence: {finf})")
