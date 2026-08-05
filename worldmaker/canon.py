"""Canonical sector data overlays.

Published Traveller sectors carry facts a generator must not overwrite: where
the stars actually are, which polity claims them, and the profiles of worlds
established in print. This module loads that data and applies it to a
generated sector.

For a Referee's reserve like Foreven the split is stark. Of its 358 systems,
every *position* is canon and 142 hexes carry a canonical Zhodani allegiance,
but only six worlds are named and five have real UWPs - everything else is
`???????-?`, deliberately left for the Referee. The overlay honours the hard
canon and generates the rest.

Three modes, from most faithful to least:

``pin``
    Everything canon states is forced: positions, allegiances, and the name,
    UWP, bases, travel zone, PBG and stars of every established world.
``seed``
    Positions and allegiances are canon; world details are generated fresh.
    This is the "make the reserve your own" mode.
``positions``
    Only the star positions are canon. Allegiance and everything else is
    generated.

Data sources
------------
`fetch_canonical_sector()` reads the T5 Second Survey data published by
travellermap.com and caches it locally. The cache is not committed: the
underlying data is Traveller canon owned by Far Future Enterprises, so this
package ships loaders rather than a copy of it. `SCG_FOREVEN` is the small
table of worlds the *Sector Construction Guide* prints in its own worked
example (pp.6, 63-64), each entry carrying its citation.
"""
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .classes import Polity, Sector
from .utils import Utils

TRAVELLERMAP_URL = "https://travellermap.com/data/{sector}/tab"

# T5SS allegiance codes seen in the sectors this package targets. Unknown
# codes fall back to the code itself, so an unmapped allegiance still yields
# a usable polity.
ALLEGIANCE_NAMES = {
    'ZhIN': "Zhodani Consulate",
    'ZhCo': "Zhodani Consulate",
    'ZhCa': "Zhodani Consulate",
    'ZhMe': "Zhodani Consulate",
    'ZhAx': "Zhodani Consulate",
    'Zh': "Zhodani Consulate",
    'ImDd': "Third Imperium",
    'Im': "Third Imperium",
    'CsIm': "Imperial Client State",
    'CsZh': "Zhodani Client State",
    'SwCf': "Sword Worlds Confederation",
    'DaCf': "Darrian Confederation",
    'AsT': "Aslan Tlaukhu",
    'VaEx': "Vargr Extents",
    'NaHu': "Non-Aligned, Human",
    'NaXX': "Non-Aligned",
    'Na': "Non-Aligned",
    'Av': "Avalar Consulate",
}

# Codes that mean "nobody has established this yet", not a real polity.
UNCLAIMED_CODES = {'XXXX', '----', '--', '', '?', '???'}

# Codes that establish a world as independent. The hex is spoken for - no
# procedural polity may absorb it - but "non-aligned" is not itself a state,
# so these never become a Polity.
NON_ALIGNED_CODES = {'Na', 'NaHu', 'NaXX', 'NaAs', 'NaVa', 'NaDr'}

# A UWP the source leaves undetermined.
PLACEHOLDER_UWP = {'???????-?', '???????-?', ''}


def _is_placeholder(value: str) -> bool:
    value = (value or '').strip()
    return not value or set(value) <= {'?', '-'}


@dataclass
class CanonicalWorld:
    """One world as a published source establishes it.

    Any field may be blank: a reserve sector typically fixes only the hex and
    the allegiance."""
    hex: str
    name: str = ""
    uwp: str = ""
    bases: str = ""
    remarks: str = ""
    zone: str = ""
    pbg: str = ""
    allegiance: str = ""
    stars: str = ""
    source: str = ""

    @property
    def has_uwp(self) -> bool:
        return not _is_placeholder(self.uwp)

    @property
    def has_allegiance(self) -> bool:
        return (self.allegiance or '').strip() not in UNCLAIMED_CODES

    @property
    def has_name(self) -> bool:
        return bool((self.name or '').strip()) and self.name.strip() != '.'

    @property
    def has_pbg(self) -> bool:
        return not _is_placeholder(self.pbg) and len(self.pbg.strip()) == 3

    @property
    def has_stars(self) -> bool:
        return bool((self.stars or '').strip())

    @property
    def trade_codes(self) -> List[str]:
        return [c for c in (self.remarks or '').split() if c]

    @property
    def gas_giants(self) -> int:
        return Utils.from_eHex(self.pbg.strip()[2]) if self.has_pbg else 0

    @property
    def planetoid_belts(self) -> int:
        return Utils.from_eHex(self.pbg.strip()[1]) if self.has_pbg else 0

    @property
    def population_digit(self) -> int:
        return Utils.from_eHex(self.pbg.strip()[0]) if self.has_pbg else 0


@dataclass
class CanonicalSector:
    """A published sector's established facts."""
    name: str = ""
    worlds: Dict[str, CanonicalWorld] = field(default_factory=dict)
    source: str = ""
    width: int = 32
    height: int = 40

    @property
    def hexes(self) -> Set[str]:
        """Every hex canon places a system in."""
        return set(self.worlds)

    def allegiance_groups(self) -> Dict[str, List[str]]:
        """Hexes grouped by canonical allegiance, unclaimed codes omitted."""
        groups: Dict[str, List[str]] = {}
        for hex_coord, world in self.worlds.items():
            if world.has_allegiance:
                groups.setdefault(world.allegiance.strip(), []).append(hex_coord)
        return {code: sorted(hexes) for code, hexes in groups.items()}

    def named_worlds(self) -> List[CanonicalWorld]:
        return [w for w in self.worlds.values() if w.has_name]

    def established_worlds(self) -> List[CanonicalWorld]:
        """Worlds canon gives a real UWP."""
        return [w for w in self.worlds.values() if w.has_uwp]

    def summary(self) -> str:
        groups = self.allegiance_groups()
        lines = [f"{self.name}: {len(self.worlds)} canonical systems"]
        if self.source:
            lines.append(f"  source: {self.source}")
        lines.append(f"  named worlds: {len(self.named_worlds())}")
        lines.append(f"  worlds with a UWP: {len(self.established_worlds())}")
        for code, hexes in sorted(groups.items(),
                                  key=lambda kv: -len(kv[1])):
            lines.append(f"  {code:6s} {ALLEGIANCE_NAMES.get(code, code):32s} "
                         f"{len(hexes):4d} hexes")
        return "\n".join(lines)


# ------------------------------------------------------------- parsing

def parse_travellermap_tab(text: str, name: str = "",
                           source: str = "") -> CanonicalSector:
    """Parses travellermap.com's tab-delimited T5 Second Survey data.

    The header names the columns and their order is not fixed, so the field
    index is built from the header line, exactly as the format requires."""
    lines = [line for line in text.splitlines()
             if line.strip() and not line.startswith('#')]
    if not lines:
        return CanonicalSector(name=name, source=source)

    header = [h.strip() for h in lines[0].split('\t')]
    index = {field_name: i for i, field_name in enumerate(header)}
    if 'Hex' not in index:
        raise ValueError("no Hex column in the data: not T5 tab format")

    def cell(parts: List[str], field_name: str) -> str:
        i = index.get(field_name)
        if i is None or i >= len(parts):
            return ""
        return parts[i].strip()

    canon = CanonicalSector(name=name, source=source)
    for line in lines[1:]:
        parts = line.split('\t')
        hex_coord = cell(parts, 'Hex')
        if not hex_coord:
            continue
        canon.worlds[hex_coord] = CanonicalWorld(
            hex=hex_coord,
            name=cell(parts, 'Name'),
            uwp=cell(parts, 'UWP'),
            bases=cell(parts, 'Bases'),
            remarks=cell(parts, 'Remarks'),
            zone=cell(parts, 'Zone'),
            pbg=cell(parts, 'PBG'),
            allegiance=cell(parts, 'Allegiance'),
            stars=cell(parts, 'Stars'),
            source=source,
        )
        if not canon.name:
            canon.name = cell(parts, 'Sector') or name
    return canon


# ------------------------------------------------------------- fetching

def cache_dir() -> Path:
    """Where fetched canon is cached. Override with WORLDMAKER_CANON_CACHE."""
    override = os.environ.get('WORLDMAKER_CANON_CACHE')
    if override:
        return Path(override)
    return Path(__file__).resolve().parent.parent / 'canon_cache'


def fetch_canonical_sector(sector_name: str, refresh: bool = False,
                           timeout: int = 60) -> CanonicalSector:
    """Loads a sector's canonical data, fetching it from travellermap.com the
    first time and caching it locally afterwards.

    The cache is deliberately not committed to the repository: the data is
    Traveller canon owned by Far Future Enterprises, so this package ships
    the loader rather than a copy."""
    directory = cache_dir()
    path = directory / f"{sector_name.replace(' ', '_')}.tab"

    if path.exists() and not refresh:
        return parse_travellermap_tab(
            path.read_text(encoding='utf-8'), name=sector_name,
            source=f"travellermap.com (cached at {path})")

    url = TRAVELLERMAP_URL.format(sector=urllib.parse.quote(sector_name))
    with urllib.request.urlopen(url, timeout=timeout) as response:
        text = response.read().decode('utf-8')

    directory.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return parse_travellermap_tab(text, name=sector_name,
                                  source=f"travellermap.com ({url})")


def load_canonical_sector(sector_name: str) -> CanonicalSector:
    """Loads cached canon without touching the network."""
    path = cache_dir() / f"{sector_name.replace(' ', '_')}.tab"
    if not path.exists():
        raise FileNotFoundError(
            f"no cached canon for {sector_name!r} at {path}. "
            f"Run worldmaker.fetch_canonical_sector({sector_name!r}) once to "
            f"download it.")
    return parse_travellermap_tab(path.read_text(encoding='utf-8'),
                                  name=sector_name,
                                  source=f"travellermap.com (cached at {path})")


# -------------------------------------------------- the guide's own tier

# The worlds the Sector Construction Guide establishes for Foreven in its
# worked example (pp.6, 63-64), with the publications each comes from.
# travellermap carries most of these; the Guide adds trade codes and the
# Parthinia placement that the survey data does not.
SCG_FOREVEN: List[CanonicalWorld] = [
    CanonicalWorld(hex="1212", name="Zdovesil", uwp="A65588A-9", bases="ZM",
                   remarks="Ga", allegiance="ZhIN", pbg="103",
                   source="SCG p.6 - Zhodani provincial capital for Iakr"),
    CanonicalWorld(hex="1618", name="Tlebria", allegiance="ZhIN",
                   source="SCG p.6 - Zhodani shipping company base, "
                          "Classic Traveller Book 7: Merchant Prince"),
    CanonicalWorld(hex="2523", name="Hollis", uwp="A370642-C", bases="NS",
                   remarks="De Ht Ni", allegiance="CsIm",
                   source="SCG p.6 - Imperial client state"),
    CanonicalWorld(hex="3229", name="Alenzar", uwp="C000414-9",
                   remarks="As Ni Va", allegiance="CsIm",
                   source="SCG p.6 - Imperial client state, Classic Traveller "
                          "Double Adventure 5: Chamax Plague/Horde"),
    CanonicalWorld(hex="3230", name="Raschev", uwp="C8697C4-6", remarks="Ri",
                   allegiance="CsIm",
                   source="SCG p.6 - Imperial client state, Classic Traveller "
                          "Double Adventure 5: Chamax Plague/Horde"),
    CanonicalWorld(hex="1636", name="Avalar", uwp="A75599C-C", bases="N",
                   remarks="Ga Hi Ht", allegiance="Av",
                   source="SCG p.6 - capital of the Avalar Consulate"),
    CanonicalWorld(hex="3018", name="Parthinia", uwp="C694655-C",
                   remarks="Ag Ht Ni", pbg="006", allegiance="Na",
                   source="SCG p.6 - Classic Traveller Alien Realms; an "
                          "independent world, and the hex is the Guide's "
                          "unofficial placement"),
]


def scg_foreven() -> CanonicalSector:
    """The Sector Construction Guide's own Foreven worlds as an overlay."""
    canon = CanonicalSector(
        name="Foreven",
        source="Mongoose Traveller Sector Construction Guide, pp.6 and 63-64")
    for world in SCG_FOREVEN:
        canon.worlds[world.hex] = world
    return canon


def merge_canon(base: CanonicalSector, overlay: CanonicalSector,
                name: str = None) -> CanonicalSector:
    """Layers one canon set over another. Non-blank overlay fields win, so a
    curated tier can add detail the survey data leaves out without
    discarding the survey's positions."""
    merged = CanonicalSector(
        name=name or base.name or overlay.name,
        source="; ".join(s for s in (base.source, overlay.source) if s),
        width=base.width, height=base.height)
    merged.worlds = {h: CanonicalWorld(**vars(w)) for h, w in base.worlds.items()}

    for hex_coord, world in overlay.worlds.items():
        existing = merged.worlds.get(hex_coord)
        if existing is None:
            merged.worlds[hex_coord] = CanonicalWorld(**vars(world))
            continue
        for attribute, value in vars(world).items():
            if attribute == 'hex':
                continue
            if value and not _is_placeholder(str(value)):
                setattr(existing, attribute, value)
    return merged


# ------------------------------------------------------------- applying

MODES = ('pin', 'seed', 'positions')


def canonical_polities(canon: CanonicalSector,
                       sector: Sector = None) -> List[Polity]:
    """Builds a Polity for each canonical allegiance.

    This is how a published border reaches the generator: the Zhodani
    Consulate's extent in Foreven is 142 hexes of ZhIN allegiance, not
    something to be rolled for."""
    polities = []
    for code, hexes in canon.allegiance_groups().items():
        if code in NON_ALIGNED_CODES:
            continue      # independent worlds, not a state
        if sector is not None:
            hexes = [h for h in hexes if h in sector.systems]
        if not hexes:
            continue
        name = ALLEGIANCE_NAMES.get(code, code)
        # A client-state code marks worlds aligned to a power, not a state
        # in its own right, so it is not given a capital.
        is_client = code.startswith('Cs')
        polity = Polity(
            name=name,
            allegiance_code=code,
            controlled_systems=sorted(hexes),
            polity_type="Client States" if is_client else "Major Race Polity",
            capital_hex="" if is_client else _pick_capital(canon, hexes),
            defense_index=0 if is_client else 9,
        )
        polities.append(polity)
    return polities


def _pick_capital(canon: CanonicalSector, hexes: List[str]) -> str:
    """A canonical capital: a named world carrying the Cp trade code if there
    is one, else the highest-population established world."""
    named = [canon.worlds[h] for h in hexes if canon.worlds[h].has_name]
    for world in named:
        if 'Cp' in world.trade_codes or 'Cx' in world.trade_codes:
            return world.hex
    established = [w for w in named if w.has_uwp]
    if established:
        return max(established,
                   key=lambda w: Utils.from_eHex(w.uwp[4])).hex
    return hexes[0] if hexes else ""


def apply_canonical_world(system, world: CanonicalWorld) -> None:
    """Forces a generated system to match an established world."""
    mainworld = system.mainworld
    if mainworld is None:
        return

    if world.has_name:
        system.name = world.name
        mainworld.name = world.name

    if world.has_uwp:
        uwp = world.uwp.strip()
        mainworld.uwp.starport = uwp[0]
        mainworld.uwp.size = uwp[1]
        mainworld.uwp.atmosphere = uwp[2]
        mainworld.uwp.hydrographics = uwp[3]
        mainworld.uwp.population = uwp[4]
        mainworld.uwp.government = uwp[5]
        mainworld.uwp.law_level = uwp[6]
        mainworld.uwp.tech_level = uwp[8] if len(uwp) > 8 else '0'
        # Keep the physical body consistent with the profile it now carries
        mainworld.size_code = uwp[1]
        mainworld.atmosphere_code = uwp[2]
        mainworld.hydrographics_code = uwp[3]

    if world.trade_codes:
        mainworld.trade_codes = list(world.trade_codes)

    if world.zone in ('A', 'R'):
        system.travel_zone = world.zone
    elif world.zone in ('G', ''):
        pass  # Green or unstated: leave whatever was generated

    if world.bases:
        system.bases = _bases_from_codes(world.bases)
    elif world.has_uwp:
        # A world the source profiles in full, with the Bases column empty,
        # has no bases - that is a statement, not a gap.
        system.bases = []

    if world.has_allegiance:
        system.allegiance = world.allegiance.strip()

    if world.has_pbg:
        system.planetoid_belt_count = world.planetoid_belts
        system.gas_giant_count = world.gas_giants
        if world.population_digit:
            mainworld.population_digit = world.population_digit

    if world.has_stars:
        _apply_canonical_stars(system, world.stars)

    if world.source:
        mainworld.notes.append(f"Canonical world: {world.source}")


# Base letters, back to the names the generator uses internally.
_BASE_NAMES = {
    'N': 'Naval', 'S': 'Scout', 'M': 'Military', 'W': 'Waystation',
    'C': 'Corsair', 'D': 'Depot', 'E': 'Embassy', 'V': 'Exploration',
    'K': 'Naval', 'Z': 'Naval',       # Zhodani naval / military codes
    'A': 'Naval',                      # legacy: naval and scout
    'R': 'Clan Base', 'T': 'Tlaukhu Base',
}


def _bases_from_codes(codes: str) -> List[str]:
    bases = []
    for letter in codes.strip():
        name = _BASE_NAMES.get(letter.upper())
        if name and name not in bases:
            bases.append(name)
        if letter.upper() == 'A' and 'Scout' not in bases:
            bases.append('Scout')       # legacy A = naval + scout
        if letter.upper() == 'K' and 'Military' not in bases:
            bases.append('Military')    # Zhodani naval implies military
    return bases


def _apply_canonical_stars(system, stars: str) -> None:
    """Rebuilds the system's stars from a canonical Morgan-Keenan string."""
    from .stellar import build_star_from_type

    tokens = _split_stellar(stars)
    if not tokens:
        return

    designations = ['A', 'B', 'C', 'D']
    rebuilt = []
    for i, token in enumerate(tokens[:4]):
        star = build_star_from_type(designations[i], token)
        if star is None:
            continue
        if i > 0:
            star.parent = rebuilt[0] if rebuilt else None
            star.orbit_class = ['', 'Close', 'Near', 'Far'][min(i, 3)]
        rebuilt.append(star)

    if not rebuilt:
        return

    # Move the generated worlds onto the canonical primary
    worlds = list(system.all_worlds)
    for star in system.stars:
        star.orbiting_bodies = []
    rebuilt[0].orbiting_bodies = worlds
    for world in worlds:
        world.parent_star_group = rebuilt[0].designation
    system.stars = rebuilt


def _split_stellar(stars: str) -> List[str]:
    """Splits 'M1 V M3 V' into ['M1 V', 'M3 V']."""
    parts = stars.split()
    tokens: List[str] = []
    for part in parts:
        if part and part[0].isalpha() and len(part) >= 2 and part[1].isdigit():
            tokens.append(part)            # a new type, e.g. 'M1'
        elif tokens:
            tokens[-1] = f"{tokens[-1]} {part}"   # a luminosity class
        else:
            tokens.append(part)            # bare 'D', 'BD', ...
    return tokens


def expand_polity_from_capital(sector: Sector, polity: Polity,
                               jump: int = 2, budget: int = 12) -> Polity:
    """Grows a canonical polity outward from its capital into unclaimed space.

    Canon often fixes only a capital - the Sector Construction Guide names
    Avalar and says the Consulate lies "mostly within the N and O
    subsectors" without listing a hex. This fills in an extent of the right
    shape while leaving every other polity's territory untouched."""
    from .sector import hex_distance

    if not polity.capital_hex or polity.capital_hex not in sector.systems:
        return polity

    claimed = {h for p in sector.polities if p is not polity
               for h in p.controlled_systems}
    held = set(polity.controlled_systems) or {polity.capital_hex}
    frontier = [polity.capital_hex]

    while frontier and len(held) < budget:
        current = frontier.pop(0)
        reachable = sorted(
            (h for h in sector.systems
             if h not in claimed and h not in held
             and 0 < hex_distance(current, h) <= jump),
            key=lambda h: hex_distance(polity.capital_hex, h))
        for target in reachable:
            if len(held) >= budget:
                break
            held.add(target)
            frontier.append(target)

    polity.controlled_systems = sorted(held)
    for hex_coord in held:
        sector.systems[hex_coord].allegiance = polity.allegiance_code
    return polity


def establish_canon_polities(sector: Sector, canon: CanonicalSector,
                             expand: Dict[str, int] = None
                             ) -> Tuple[List[Polity], Set[str]]:
    """Creates the canonical polities and returns them with the hexes they
    and any canonically independent worlds occupy.

    This runs *before* procedural polity generation, so a published border
    is laid down first and the procedural states fill in around it. `expand`
    maps an allegiance code to a target world count, for polities canon
    gives a capital but no extent."""
    polities = canonical_polities(canon, sector)
    sector.polities = polities

    for polity in polities:
        target = (expand or {}).get(polity.allegiance_code)
        if target and len(polity.controlled_systems) < target:
            expand_polity_from_capital(sector, polity, budget=target)

    reserved = {h for p in polities for h in p.controlled_systems}
    # Worlds canon marks independent are spoken for too, even though
    # non-alignment is not a state that can be given territory.
    reserved |= {h for h, w in canon.worlds.items()
                 if w.has_allegiance and h in sector.systems}
    return polities, reserved


def apply_canon(sector: Sector, canon: CanonicalSector, mode: str = 'pin',
                polities: List[Polity] = None) -> Sector:
    """Applies canonical data to an already generated sector.

    Positions are handled during generation; this pass sets allegiances,
    forces established worlds and installs the canonical polities. Pass
    `polities` from establish_canon_polities() to keep an extent that was
    settled before the procedural states ran."""
    if mode not in MODES:
        raise ValueError(f"unknown mode {mode!r}; expected one of {MODES}")

    if mode != 'positions':
        canonical = (polities if polities is not None
                     else canonical_polities(canon, sector))
        if canonical:
            claimed = {h for p in canonical for h in p.controlled_systems}
            # Procedural polities keep only the space canon leaves open
            remaining = []
            for polity in sector.polities:
                if any(polity is c for c in canonical):
                    continue
                kept = [h for h in polity.controlled_systems if h not in claimed]
                if kept:
                    polity.controlled_systems = kept
                    remaining.append(polity)
            sector.polities = canonical + remaining
            for polity in canonical:
                for hex_coord in polity.controlled_systems:
                    if hex_coord in sector.systems:
                        sector.systems[hex_coord].allegiance = polity.allegiance_code

        # Canonical world facts win over anything generated or expanded
        for hex_coord, world in canon.worlds.items():
            system = sector.systems.get(hex_coord)
            if system is None:
                continue
            if world.has_allegiance:
                system.allegiance = world.allegiance.strip()
            if mode == 'pin':
                apply_canonical_world(system, world)

    return sector
