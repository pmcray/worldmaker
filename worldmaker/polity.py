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
                      reserved: set = None, universe: Any = None):
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

    # Shape borders through the sequence of wars, treaties and neutral zones
    # implied by the sector's history (SCG pp. 20, 26, 42, 47).
    evolve_borders_from_history(sector, universe=universe, reserved=reserved)


def _stays_contiguous(capital_hex: str, systems_set: set, jump: int) -> bool:
    """Checks that every system in `systems_set` remains reachable from
    `capital_hex` via hops of at most `jump` parsecs."""
    from .sector import hex_distance

    if not systems_set:
        return True
    if capital_hex not in systems_set:
        return False
    if len(systems_set) == 1:
        return True
    if jump <= 0:
        return len(systems_set) <= 1

    visited = {capital_hex}
    queue = [capital_hex]
    while queue:
        curr = queue.pop(0)
        for other in systems_set:
            if other not in visited and 0 < hex_distance(curr, other) <= jump:
                visited.add(other)
                queue.append(other)
    return len(visited) == len(systems_set)


def _recompute_polity_stats(polity: Polity, sector: Sector) -> None:
    """Refreshes `polity_type` and `defense_index` after border shifts."""
    cap_sys = sector.systems.get(polity.capital_hex)
    cap_mw = cap_sys.mainworld if cap_sys else None
    cap_tl = Utils.from_eHex(cap_mw.uwp.tech_level) if cap_mw else 10
    jump = _jump_range_for_tech(cap_tl)
    polity.polity_type = _polity_type_for(
        cap_tl, len(polity.controlled_systems),
        is_major_race=bool(sector.native_sophonts.get(polity.capital_hex))
    )
    polity.defense_index = max(
        1, min(12, jump + max(0, cap_tl - 10) + len(polity.controlled_systems) // 25)
    )


def evolve_borders_from_history(sector: Sector, universe: Any = None,
                                reserved: Optional[set] = None,
                                current_year: int = 1105) -> List[Dict[str, Any]]:
    """Evolves polity borders from a sequence of historical expansions, frontier
    wars, annexations, secessions, and peace treaties (SCG pp. 20, 26, 42, 47).

    Records the resulting historical narrative in `sector.border_history`,
    `sector.neutral_zones`, `polity.history`, `polity.border_treaties`,
    `system.historical_notes`, and (when `universe` is supplied)
    `universe.timeline`."""
    from .sector import hex_distance

    reserved = set(reserved or ())
    systems = sector.systems
    if universe is not None and getattr(universe, 'current_year', None) is not None:
        current_year = universe.current_year

    # Only evolve procedural polities whose territory is not canon-locked
    active_polities = [
        p for p in sector.polities
        if p.capital_hex in systems and p.capital_hex not in reserved
    ]
    if not active_polities:
        return sector.border_history

    trajectory = getattr(universe, 'trajectory', 'expansion') if universe is not None else 'expansion'
    events: List[Dict[str, Any]] = []

    # 1. Founding & Initial Expansion Epoch
    founding_base = current_year - ({
        'expansion': 350, 'stasis': 900, 'decline': 700,
        'collapse': 800, 'recovery': 450,
    }.get(trajectory, 400))

    for idx, polity in enumerate(active_polities):
        found_year = founding_base + idx * 25
        cap_sys = systems.get(polity.capital_hex)
        cap_name = cap_sys.mainworld.name if (cap_sys and cap_sys.mainworld) else polity.capital_hex
        ev = {
            'year': found_year,
            'type': 'founding',
            'polity': polity.name,
            'allegiance': polity.allegiance_code,
            'capital_hex': polity.capital_hex,
            'systems_count': len(polity.controlled_systems),
            'description': (
                f"{polity.name} ({polity.allegiance_code}) established at {cap_name} "
                f"({polity.capital_hex}), expanding across {len(polity.controlled_systems)} systems."
            ),
        }
        polity.history.append(ev)
        events.append(ev)
        if cap_sys:
            note = f"Founded {polity.name} ({found_year})."
            if note not in cap_sys.historical_notes:
                cap_sys.historical_notes.append(note)

    # 2. Frontier Contact, Border Wars & Treaty Buffers between neighbouring polities
    for i in range(len(active_polities)):
        for j in range(i + 1, len(active_polities)):
            pa, pb = active_polities[i], active_polities[j]
            cap_a = systems[pa.capital_hex].mainworld
            cap_b = systems[pb.capital_hex].mainworld
            jump_a = _jump_range_for_tech(Utils.from_eHex(cap_a.uwp.tech_level)) if cap_a else 1
            jump_b = _jump_range_for_tech(Utils.from_eHex(cap_b.uwp.tech_level)) if cap_b else 1
            contact_range = max(2, jump_a, jump_b) + 1

            # Find closest border approach between pa and pb
            border_pairs: List[Tuple[int, str, str]] = []
            for ha in pa.controlled_systems:
                for hb in pb.controlled_systems:
                    d = hex_distance(ha, hb)
                    if d <= contact_range:
                        border_pairs.append((d, ha, hb))

            if not border_pairs:
                continue

            border_pairs.sort()
            war_year = current_year - random.randint(60, 220)
            treaty_year = war_year + random.randint(4, 15)

            # Determine aggressor/victor weighted by defense_index and ambition
            roll_a = Utils.D6(2) + pa.defense_index
            roll_b = Utils.D6(2) + pb.defense_index
            if roll_a >= roll_b:
                victor, loser = pa, pb
                v_jump, l_jump = jump_a, jump_b
            else:
                victor, loser = pb, pa
                v_jump, l_jump = jump_b, jump_a

            # Candidate border hexes of `loser` that `victor` can reach within
            # `v_jump` while keeping `loser` contiguous within `l_jump`.
            conquered: List[str] = []
            max_transfers = min(2, max(0, len(loser.controlled_systems) - 2))
            loser_candidates = sorted(
                [h for h in loser.controlled_systems
                 if h != loser.capital_hex and h not in reserved],
                key=lambda h: min(hex_distance(h, vh) for vh in victor.controlled_systems)
            )
            for cand in loser_candidates:
                if len(conquered) >= max_transfers:
                    break
                if not any(0 < hex_distance(cand, vh) <= v_jump for vh in victor.controlled_systems):
                    continue
                remaining_loser = set(loser.controlled_systems) - {cand}
                if not _stays_contiguous(loser.capital_hex, remaining_loser, l_jump):
                    continue
                loser.controlled_systems.remove(cand)
                victor.controlled_systems.append(cand)
                systems[cand].allegiance = victor.allegiance_code
                conquered.append(cand)
                if cand not in victor.contested_hexes:
                    victor.contested_hexes.append(cand)
                if cand not in loser.contested_hexes:
                    loser.contested_hexes.append(cand)
                sys_obj = systems[cand]
                w_name = sys_obj.mainworld.name if sys_obj.mainworld else cand
                sys_obj.historical_notes.append(
                    f"Annexed by {victor.name} from {loser.name} in the "
                    f"{victor.name}-{loser.name} Frontier War ({war_year})."
                )
                if sys_obj.mainworld:
                    sys_obj.mainworld.notes.append(
                        f"Former {loser.name} border world conquered in {war_year}"
                    )

            # Fortify a border bastion on the victor's front line (SCG p. 47)
            front_hex = border_pairs[0][1] if victor is pa else border_pairs[0][2]
            if front_hex in systems:
                front_sys = systems[front_hex]
                if "Military" not in front_sys.bases:
                    front_sys.bases.append("Military")
                front_sys.historical_notes.append(
                    f"Fortified as a frontier bastion during the {war_year} border war."
                )

            war_desc = (
                f"{victor.name}–{loser.name} Frontier War ({war_year}–{treaty_year}): "
                + (f"{victor.name} seized {', '.join(conquered)} along the contested march."
                   if conquered else
                   f"fought to a standstill along the {front_hex} frontier.")
            )
            war_ev = {
                'year': war_year,
                'type': 'frontier_war',
                'victor': victor.name,
                'defender': loser.name,
                'hexes_transferred': list(conquered),
                'description': war_desc,
            }
            victor.history.append(war_ev)
            loser.history.append(war_ev)
            events.append(war_ev)
            if universe is not None:
                universe.add_event(war_year, war_desc)

            # 3. Peace Treaty & Neutral / Demilitarised Buffer Zone (SCG p. 20)
            buffer_hexes = [
                h for h, s in systems.items()
                if s.allegiance == 'Na' and h not in reserved
                and min((hex_distance(h, vh) for vh in pa.controlled_systems), default=99) <= 2
                and min((hex_distance(h, lh) for lh in pb.controlled_systems), default=99) <= 2
            ]
            treaty_world_hex = buffer_hexes[0] if buffer_hexes else front_hex
            treaty_sys = systems.get(treaty_world_hex)
            treaty_world_name = (
                treaty_sys.mainworld.name
                if (treaty_sys and treaty_sys.mainworld)
                else treaty_world_hex
            )
            treaty_name = f"Treaty of {treaty_world_name}"
            treaty_desc = (
                f"{treaty_name} ({treaty_year}) delineates the border between "
                f"{pa.name} and {pb.name}"
                + (f", establishing a neutral buffer across {', '.join(buffer_hexes[:4])}."
                   if buffer_hexes else ".")
            )
            treaty_record = {
                'year': treaty_year,
                'type': 'treaty',
                'name': treaty_name,
                'signatories': [pa.name, pb.name],
                'buffer_hexes': buffer_hexes[:6],
                'description': treaty_desc,
            }
            pa.border_treaties.append(treaty_record)
            pb.border_treaties.append(treaty_record)
            pa.history.append(treaty_record)
            pb.history.append(treaty_record)
            events.append(treaty_record)
            if buffer_hexes:
                sector.neutral_zones.append({
                    'name': f"{treaty_world_name} Neutral Buffer",
                    'treaty': treaty_name,
                    'year': treaty_year,
                    'signatories': [pa.name, pb.name],
                    'hexes': buffer_hexes[:6],
                })
                for bh in buffer_hexes[:6]:
                    systems[bh].historical_notes.append(
                        f"Designated neutral buffer under the {treaty_name} ({treaty_year})."
                    )
            if universe is not None:
                universe.add_event(treaty_year, treaty_desc)

    # 4. Trajectory-driven border contraction for 'decline' / 'collapse' settings
    if trajectory in ('decline', 'collapse'):
        secession_year = current_year - random.randint(30, 120)
        for polity in active_polities:
            if len(polity.controlled_systems) <= 3:
                continue
            cap_mw = systems[polity.capital_hex].mainworld
            jump = _jump_range_for_tech(Utils.from_eHex(cap_mw.uwp.tech_level)) if cap_mw else 1
            # Outermost world furthest from capital
            by_dist = sorted(
                [h for h in polity.controlled_systems
                 if h != polity.capital_hex and h not in reserved],
                key=lambda h: hex_distance(polity.capital_hex, h),
                reverse=True
            )
            lost: List[str] = []
            target_loss = 2 if trajectory == 'collapse' else 1
            for cand in by_dist:
                if len(lost) >= target_loss or len(polity.controlled_systems) <= 2:
                    break
                rem = set(polity.controlled_systems) - {cand}
                if _stays_contiguous(polity.capital_hex, rem, jump):
                    polity.controlled_systems.remove(cand)
                    systems[cand].allegiance = 'Na'
                    systems[cand].historical_notes.append(
                        f"Seceded / lost contact with {polity.name} ({secession_year})."
                    )
                    lost.append(cand)
            if lost:
                sec_desc = (
                    f"{polity.name} border contraction ({secession_year}): "
                    f"outer rim {', '.join(lost)} reverted to independent status."
                )
                sec_ev = {
                    'year': secession_year,
                    'type': 'contraction',
                    'polity': polity.name,
                    'hexes_lost': lost,
                    'description': sec_desc,
                }
                polity.history.append(sec_ev)
                events.append(sec_ev)
                if universe is not None:
                    universe.add_event(secession_year, sec_desc)

    for polity in active_polities:
        _recompute_polity_stats(polity, sector)

    events.sort(key=lambda e: e['year'])
    sector.border_history.extend(events)
    sector.border_history.sort(key=lambda e: e['year'])
    return sector.border_history


def apply_foreven_timeline_borders(sector: Sector) -> List[Dict[str, Any]]:
    """Applies the SCG Foreven & Avalar historical timeline (SCG pp. 26, 47) to
    explain and annotate the sector's borders, conquests, treaty lines, and
    neutral buffer corridors."""
    timeline_events = [
        {
            'year': -4000,
            'type': 'settlement_wave',
            'polity': 'Zhodani Consulate',
            'subsectors': ['A', 'B', 'C'],
            'description': (
                "Zhodani scouts and settlers from Ziafrplians establish the "
                "coreward Consular heartland across Subsectors A, B and C, "
                "with provincial capital at Zdovesil (1212)."
            ),
        },
        {
            'year': -1850,
            'type': 'founding',
            'polity': 'Avalar',
            'hexes': ['1636'],
            'description': (
                "Solomani manufactory starship Avalar settles Avalar (1636); "
                "first contact with Zhodani explorers follows in -1635."
            ),
        },
        {
            'year': 18,
            'type': 'expansion',
            'polity': 'Avalar',
            'hexes': ['1636', '1637', '1536', '1734'],
            'description': (
                "Having reached TL9 (-21), Avalar settles Tranquilidad (1637) "
                "and expands across its local 1-parsec cluster."
            ),
        },
        {
            'year': 550,
            'type': 'settlement_wave',
            'polity': 'Third Imperium',
            'subsectors': ['D', 'H', 'L', 'P'],
            'description': (
                "Pre-war Imperial thin settlement wave crosses from the "
                "Spinward Marches into trailing Subsectors Massina (D), "
                "Fessor (H), Reidain (L) and Urnian (P)."
            ),
        },
        {
            'year': 604,
            'type': 'frontier_war',
            'polity': 'Zhodani Consulate',
            'subsectors': ['D'],
            'description': (
                "First Frontier War (589–604): Zhodani Consulate conquers "
                "Massina (Subsector D) from the Imperial frontier and begins "
                "client-state technical assistance to Avalar."
            ),
        },
        {
            'year': 620,
            'type': 'treaty',
            'name': 'Zhodani-Avalar Defence Treaty of 620',
            'signatories': ['Zhodani Consulate', 'Avalar Consulate'],
            'description': (
                "Second Frontier War ends (620): Avalar signs a mutual defence "
                "treaty with the Zhodani Consulate; Zhodani thin settlement "
                "wave expands into Subsectors E, F and G (600–700), fixing the "
                "142-hex Consular border."
            ),
        },
        {
            'year': 628,
            'type': 'treaty',
            'name': 'Charter of the Avalar Consulate (628)',
            'signatories': ['Avalar Consulate', 'Zhodani Consulate'],
            'hexes': ['1636', '1634', '1637', '1734'],
            'description': (
                "Ardiente (1634) settled; the Avalar Consulate (or neutral "
                "Confederation of Worlds / Die Weltbund) is formally "
                "established and recognised."
            ),
        },
        {
            'year': 855,
            'type': 'expansion',
            'polity': 'Avalar Consulate',
            'subsectors': ['N', 'O'],
            'hexes': ['2136', '2236', '2135'],
            'description': (
                "Avalar expands one Jump-2 link by 800 and two Jump-2 links by "
                "900 (Ninfa 2136 settled 704, Larissa 2236 joins 744, Fragos "
                "2135 naval base 855), creating the Subsector N/O border and "
                "isolating the Subsector I/M shadow frontier."
            ),
        },
        {
            'year': 983,
            'type': 'fortification',
            'polity': 'Avalar Consulate',
            'hexes': ['1734', '1738', '1637'],
            'description': (
                "Third Frontier War (980–986): Naval bases and fortresses "
                "established at Pres Tinto (1734) and Pres Alfa (1738) in 983; "
                "Imperial strike devastates Tranquilidad (1637) in 985; "
                "Vengador strike force raids Urnian in 986."
            ),
        },
        {
            'year': 1045,
            'type': 'annexation',
            'polity': 'Avalar Consulate',
            'hexes': ['1938'],
            'description': (
                "Avalar Consulate occupies Vargr world Zuekgoz (1938) in a "
                "piracy suppression campaign, extending the eastern border."
            ),
        },
        {
            'year': 1084,
            'type': 'frontier_war',
            'polity': 'Avalar Consulate',
            'hexes': ['2236', '2237'],
            'description': (
                "Fourth Frontier War (1082–1084): Avalar raids Urnian "
                "installations; Imperial frontier cruisers out of Urnian raid "
                "Larissa (2236) and Lun Orcus (2237) before the 1084 armistice "
                "freezes the current borders."
            ),
        },
    ]

    sector.border_history = list(timeline_events)

    # Annotate affected systems and polities with their border history
    hex_notes = {
        '1212': "Zhodani Iakr Sector provincial capital established during coreward wave (-4000 to -1000).",
        '1636': "Settled -1850 by Tvastar-class starship Avalar; capital of the 628 Consulate charter.",
        '1637': "Settled Year 18 from Avalar; devastated by Imperial strike in 985 (Third Frontier War).",
        '1634': "Settled 628 at the formal recognition of the Avalar Consulate.",
        '1734': "Fortified with naval/military base in 983 during the Third Frontier War.",
        '1738': "Fortified with naval/military base in 983 during the Third Frontier War.",
        '2135': "Consular naval base established in 855 upon reaching TL12.",
        '2136': "Settled 704 from Avalar during the Jump-2 expansion ripple.",
        '2236': "Voluntarily joined the Consulate in 744; raided by Urnian cruisers in 1084.",
        '2237': "Eastern border naval bastion; raided by Urnian frontier cruisers in 1084.",
        '1938': "Vargr world occupied by Avalar in 1045 piracy suppression campaign.",
    }
    for h, note in hex_notes.items():
        if h in sector.systems and note not in sector.systems[h].historical_notes:
            sector.systems[h].historical_notes.append(note)

    # Massina (Subsector D) conquest note (First Frontier War, 589-604)
    for h, sys in sector.systems.items():
        col, row = int(h[:2]), int(h[2:])
        if 25 <= col <= 32 and 1 <= row <= 10 and (sys.allegiance or '').startswith('Zh'):
            note = "Conquered by the Zhodani Consulate from the early Imperial frontier in the First Frontier War (589–604)."
            if note not in sys.historical_notes:
                sys.historical_notes.append(note)

    for polity in sector.polities:
        for ev in timeline_events:
            if (ev.get('polity') in (polity.name, 'Avalar') and polity.allegiance_code in ('Av', 'Wb')) or (
                ev.get('polity') == 'Zhodani Consulate' and polity.allegiance_code.startswith('Zh')
            ):
                if ev not in polity.history:
                    polity.history.append(ev)

    return sector.border_history


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
