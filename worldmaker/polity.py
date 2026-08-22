import random
from typing import List, Dict, Any, Tuple, Optional

from .classes import Polity, Sector, UWP, StellarSystem
from .utils import Utils

def define_foreven_polities(sector: Sector):
    """The canonical Foreven-flavoured layout: Zhodani Consulate coreward,
    Avalar Consulate rimward and the Third Imperium trailing. Kept for
    reproducing the SCG's worked example; generate_polities() is the
    procedural alternative used by default."""
    # 1. Zhodani Consulate (Coreward / Spinward)
    zhodani = Polity(
        name="Zhodani Consulate", 
        capital_hex="0101", 
        allegiance_code="Zh",
        polity_type="Major Race Polity",
        defense_index=9
    )
    # Define Zhodani territory (top-left quadrant)
    for col in range(1, 9): 
        for row in range(1, 5): 
            hex_coord = f"{col:02d}{row:02d}"
            zhodani.controlled_systems.append(hex_coord)
    
    # 2. Avalar Consulate (Rimward / Spinward - Pocket Empire)
    avalar = Polity(
        name="Avalar Consulate", 
        capital_hex="1636", 
        allegiance_code="Av",
        polity_type="Pocket Empire",
        defense_index=5
    )
    avalar_systems = ["1636", "1534", "1734", "1635", "1535", "1735", "1637"]
    avalar.controlled_systems.extend(avalar_systems)

    # 3. Third Imperium (Trailing / Rimward)
    imperium = Polity(
        name="Third Imperium", 
        capital_hex="3240", 
        allegiance_code="Im",
        polity_type="Major Race Polity",
        defense_index=10
    )
    # Define Imperial territory (bottom-right corner)
    for col in range(25, 33):
        for row in range(35, 41):
            hex_coord = f"{col:02d}{row:02d}"
            imperium.controlled_systems.append(hex_coord)

    polities = [zhodani, avalar, imperium]
    sector.polities = polities

    # Assign polities to the sector systems
    for polity in polities:
        for hex_coord in polity.controlled_systems:
            if hex_coord in sector.systems:
                sector.systems[hex_coord].allegiance = polity.allegiance_code

# Polity naming components, and the government-derived descriptor the SCG
# suggests deriving from the capital world (pp.42-43).
_POLITY_STEMS = ["Aslan", "Avalar", "Beryx", "Carrick", "Delphi", "Entaris",
                 "Foreven", "Gazulin", "Halcyon", "Iderati", "Jarrow",
                 "Kaltoth", "Lanth", "Marrakesh", "Nevermore", "Orlanth",
                 "Pyrrhus", "Quenlan", "Rhylanor", "Sindal", "Tanager",
                 "Ushant", "Vilis", "Wintar", "Xanthe", "Yggdras", "Zeda"]

_POLITY_FORMS = {
    'Confederation': ["Confederation", "League", "Compact", "Accord"],
    'Federation': ["Federation", "Union", "Commonwealth", "Alliance"],
    'Unitary': ["Imperium", "Consulate", "Hegemony", "Directorate", "Protectorate"],
}


def _jump_range_for_tech(tech_level: int) -> int:
    """Polity reach is bounded by its jump drive (SCG p.41): TL9-10 jump-1,
    TL11 jump-2, TL12-14 jump-3, TL15+ jump-4."""
    if tech_level >= 15:
        return 4
    if tech_level >= 12:
        return 3
    if tech_level >= 11:
        return 2
    if tech_level >= 9:
        return 1
    return 0


def _polity_type_for(tech_level: int, world_count: int, is_major_race: bool) -> str:
    if is_major_race:
        return "Major Race Polity"
    if world_count <= 1:
        return "Single-System State"
    if world_count <= 8:
        return "Pocket Empire"
    if tech_level >= 12 and world_count >= 30:
        return "Interstellar Empire"
    return "Interstellar State"


def _allegiance_code(name: str, used: set) -> str:
    """A two-character allegiance code, as used by .sec files and the maps."""
    letters = [c for c in name if c.isalpha()]
    candidates = []
    if len(letters) >= 2:
        candidates.append(letters[0].upper() + letters[1].lower())
        candidates.append(letters[0].upper() + letters[-1].lower())
    for extra in letters[2:]:
        candidates.append(letters[0].upper() + extra.lower())
    for code in candidates:
        if code not in used:
            used.add(code)
            return code
    # Fall back to a numbered code
    i = 1
    while f"X{i}" in used:
        i += 1
    used.add(f"X{i}")
    return f"X{i}"


def generate_polities(sector: Sector, max_polities: int = None,
                      reserved: set = None):
    """Generates polities procedurally (SCG pp.40-49).

    `reserved` names hexes a published source has already assigned; no
    procedural polity may claim them or plant a capital in them.

    Capitals are chosen from the sector's most capable worlds - high
    population, high Tech Level, good starport. Each polity then expands
    outward from its capital along jump links no longer than its drive
    technology allows, up to a size budget set by that technology and the
    capital's population. Government, culture and naming derive from the
    capital world, per the guidance that smaller and younger polities
    resemble their founding world."""
    from .sector import hex_distance, hex_neighbors, hex_to_coords

    systems = sector.systems
    reserved = set(reserved or ())
    if not systems:
        sector.polities = []
        return

    def score(hex_coord):
        mw = systems[hex_coord].mainworld
        if mw is None:
            return -1
        pop = Utils.from_eHex(mw.uwp.population)
        tl = Utils.from_eHex(mw.uwp.tech_level)
        port_bonus = {'A': 3, 'B': 2, 'C': 1}.get(mw.uwp.starport, 0)
        # A capital needs people, industry and a way off-world
        return pop * 2 + tl + port_bonus

    ranked = sorted((h for h in systems
                     if systems[h].mainworld is not None and h not in reserved),
                    key=score, reverse=True)
    if not ranked:
        sector.polities = []
        return

    # A sector typically holds a few significant states with substantial
    # independent space between them (the Spinward Marches has the Imperium,
    # the Zhodani, the Sword Worlds, Darrian and Vargr, plus many
    # unaligned worlds).
    if max_polities is None:
        max_polities = max(1, min(5, len(ranked) // 90 + 2))

    # Capitals must be far enough apart to have distinct spheres
    capitals = []
    min_separation = max(4, int((sector.width * sector.height / 40) ** 0.5))
    for hex_coord in ranked:
        mw = systems[hex_coord].mainworld
        if Utils.from_eHex(mw.uwp.tech_level) < 9:
            continue  # no jump drive, no interstellar polity
        if all(hex_distance(hex_coord, c) >= min_separation for c in capitals):
            capitals.append(hex_coord)
        if len(capitals) >= max_polities:
            break

    used_codes = set()
    used_names = set()
    polities = []
    # Every capital is reserved before any expansion begins: a polity must not
    # be able to absorb another state's seat of government. Territory a
    # published source has already assigned is off limits too.
    claimed = {c: None for c in capitals}
    claimed.update({h: 'canon' for h in reserved})

    for capital in capitals:
        cap_mw = systems[capital].mainworld
        cap_tl = Utils.from_eHex(cap_mw.uwp.tech_level)
        cap_pop = Utils.from_eHex(cap_mw.uwp.population)
        cap_gov = Utils.from_eHex(cap_mw.uwp.government)

        jump = _jump_range_for_tech(cap_tl)
        if jump == 0:
            continue

        # Size budget: reach and industry both matter, but ambition varies -
        # some states are expansive empires, others content pocket empires.
        ambition = Utils.D6() / 3.0          # 0.33 to 2.0
        budget = int((jump * 5 + cap_pop * 2 + max(0, cap_tl - 9)) * ambition)
        if sector.native_sophonts.get(capital):
            budget += 10  # a native major race expands from a deep base
        budget = max(1, budget)

        # Government structure follows the capital for smaller polities
        if cap_gov in (0, 1, 2, 4):
            centralisation = 'Confederation'
        elif cap_gov in (3, 5, 6, 8, 9):
            centralisation = 'Federation'
        else:
            centralisation = 'Unitary'

        stem = next((s for s in random.sample(_POLITY_STEMS, len(_POLITY_STEMS))
                     if s not in used_names), None)
        if stem is None:
            stem = f"Polity{len(polities) + 1}"
        used_names.add(stem)
        name = f"{stem} {random.choice(_POLITY_FORMS[centralisation])}"

        polity = Polity(
            name=name,
            capital_hex=capital,
            allegiance_code=_allegiance_code(stem, used_codes),
            polity_type="Interstellar State",
            defense_index=0,
        )

        # Breadth-first expansion along jump links within range
        frontier = [capital]
        polity.controlled_systems.append(capital)
        claimed[capital] = polity.allegiance_code

        while frontier and len(polity.controlled_systems) < budget:
            current = frontier.pop(0)
            c, r = hex_to_coords(current)
            # Candidate systems within jump range of this one
            reachable = [h for h in systems
                         if h not in claimed
                         and 0 < hex_distance(current, h) <= jump]
            reachable.sort(key=score, reverse=True)
            for target in reachable:
                if len(polity.controlled_systems) >= budget:
                    break
                mw = systems[target].mainworld
                if mw is None:
                    continue
                # Expansion is resisted by distance and by worlds with little
                # to offer or their own strong government
                pop = Utils.from_eHex(mw.uwp.population)
                gov = Utils.from_eHex(mw.uwp.government)
                dm = pop - hex_distance(capital, target)
                if gov >= 10:
                    dm -= 2
                if Utils.D6(2) + dm < 5:
                    continue
                polity.controlled_systems.append(target)
                claimed[target] = polity.allegiance_code
                frontier.append(target)

        polity.polity_type = _polity_type_for(
            cap_tl, len(polity.controlled_systems),
            is_major_race=bool(sector.native_sophonts.get(capital)))

        # Defence index scales with reach, industry and size: a jump-1 pocket
        # empire lands around 2-3, a jump-4 interstellar empire around 10-12.
        polity.defense_index = max(1, min(12,
            jump + max(0, cap_tl - 10) + len(polity.controlled_systems) // 25))

        polities.append(polity)

    sector.polities = polities

    for polity in polities:
        for hex_coord in polity.controlled_systems:
            if hex_coord in systems:
                systems[hex_coord].allegiance = polity.allegiance_code


def define_polities(sector: Sector, reserved: set = None):
    """Default polity generation: procedural (SCG pp.40-49)."""
    generate_polities(sector, reserved=reserved)


def generate_travel_zones(sector: Sector):
    """Assigns Amber/Red Travel Zones using the SCG p.27 rules of thumb:
    Exotic/Corrosive/Insidious atmospheres and worlds whose Government +
    Law Level total 20+ are Amber candidates, as are Balkanised worlds
    with ongoing conflicts. Red Zones are rare interdictions."""
    for hex_coord, system in sector.systems.items():
        mainworld = system.mainworld
        if not mainworld:
            continue

        uwp = mainworld.uwp
        atm = Utils.from_eHex(uwp.atmosphere)
        gov = Utils.from_eHex(uwp.government)
        law = Utils.from_eHex(uwp.law_level)
        pop = Utils.from_eHex(uwp.population)

        zone = ""
        if atm in (10, 11, 12) and Utils.D6(2) >= 9:  # Exotic/Corrosive/Insidious, hazardous cases
            zone = "A"
        elif gov + law >= 20:
            zone = "A"
        elif gov == 7 and Utils.D6(2) >= 10:  # Balkanised, ongoing conflict
            zone = "A"

        # Rare interdictions: hazardous Amber worlds and empty interdicted
        # worlds escalate to Red on boxcars.
        if zone == "A" and Utils.D6(2) == 12:
            zone = "R"
        elif pop == 0 and Utils.D6(2) == 12:
            zone = "R"

        system.travel_zone = zone

def generate_bases(sector: Sector):
    """Applies polity-specific adjustments to the bases each world's starport
    already rolled (WBH p.194).

    The Starport Facilities table is the authoritative source and is rolled
    during system generation; this pass only layers on the polity rules the
    SCG describes (p.28), where a restrictive state pairs every naval base
    with a military one and ignores scout base results."""
    for hex_coord, system in sector.systems.items():
        mainworld = system.mainworld
        if not mainworld:
            continue

        polity = next((p for p in sector.polities
                       if p.allegiance_code == system.allegiance), None)
        if polity is None:
            continue

        restrictive = (polity.defense_index >= 9
                       and polity.polity_type in ("Major Race Polity",
                                                  "Interstellar Empire"))
        if not restrictive:
            continue

        bases = [b for b in system.bases if b not in ("Scout", "Waystation")]
        if "Naval" in bases and "Military" not in bases:
            bases.append("Military")
        system.bases = bases
