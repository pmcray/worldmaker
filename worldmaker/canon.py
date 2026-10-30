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
package ships loaders rather than a copy of it.

Two tiers of the *Sector Construction Guide* sit on top of it, each entry
carrying its citation:

`scg_foreven()`
    The seven worlds the reserve documentation itself establishes (SCG p.6).
`scg_foreven_full()`
    The whole sector the Guide works up around them over sixty pages - the
    Avalar Consulate, the Tlesho Union, the sophont homeworlds and Ancients
    sites, the barren zone of subsector J, the Zhodani route waypoints, the
    Imperial cage and both Consulates' Tech Level ceilings. The Guide is
    explicit that none of this is canon; it is offered as a published
    alternative to inventing a reserve sector from nothing.
"""
import os
import random
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
    'TlU': "Tlesho Union",
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

    # Facts a survey file has no column for, but a sector guide states in
    # prose: who lives there, what the world physically is, and what a
    # Referee's decision has already fixed about it.
    sophont: str = ""            # species native to or settled on the world
    # True where the species did not evolve here: an Ancients transplant, a
    # lost colony, an occupied world. They still count as natives for
    # Population (SCG p.26 treats them as "old enough"), but the hex is not
    # their homeworld.
    sophont_transplanted: bool = False
    physical_profile: str = ""   # Size/Atmosphere/Hydrographics, e.g. "998"
    climate: str = ""            # "Hot", "Temperate" or "Cold"
    barren: bool = False         # Population 0: nobody lives here
    ruins: bool = False          # an Ancients site
    starport: str = ""           # a starport class fixed by fiat
    starport_floor: str = ""     # a starport class the world is raised to
    gas_giant: str = ""          # 'G' at least one, 'X' none, '' unstated
    max_tech_level: int = 0      # a Tech Level ceiling, 0 for none
    # An entry that annotates a system established elsewhere - "put a naval
    # base here" - rather than surveying one. It never places a star, so if
    # the hex turns out to be empty the annotation simply has no effect.
    annotation_only: bool = False

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

    @property
    def has_sophont(self) -> bool:
        return bool((self.sophont or '').strip())


@dataclass
class CanonicalSector:
    """A published sector's established facts."""
    name: str = ""
    worlds: Dict[str, CanonicalWorld] = field(default_factory=dict)
    source: str = ""
    width: int = 32
    height: int = 40
    # Tech Level ceilings a source imposes on a whole polity, by allegiance
    # code. The SCG holds the Zhodani Consulate to TL14 and the Avalar
    # Consulate to TL12 (SCG p.27).
    tech_level_ceilings: Dict[str, int] = field(default_factory=dict)

    @property
    def hexes(self) -> Set[str]:
        """Every hex canon places a system in.

        Annotation-only entries are excluded: "this system has a naval base"
        presumes a system, it does not survey one."""
        return {h for h, w in self.worlds.items() if not w.annotation_only}

    def max_tech_level_for(self, hex_coord: str) -> Optional[int]:
        """The Tech Level ceiling over a hex: the world's own, or the one its
        polity imposes, whichever is lower."""
        world = self.worlds.get(hex_coord)
        if world is None:
            return None
        limits = [world.max_tech_level] if world.max_tech_level else []
        polity_limit = self.tech_level_ceilings.get(
            (world.allegiance or '').strip())
        if polity_limit:
            limits.append(polity_limit)
        return min(limits) if limits else None

    def sophont_worlds(self) -> List[CanonicalWorld]:
        """Worlds a source names a species for."""
        return [w for w in self.worlds.values() if w.has_sophont]

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


# --------------------------------------------- the guide's full example

# Everything above is the handful of worlds the reserve documentation itself
# establishes. The Sector Construction Guide goes much further: over sixty
# pages it works Foreven up into a playable sector, and the worlds it settles
# on are printed in full. They are explicitly *not* canon - the guide says so
# twice - but they are a coherent, published treatment of the reserve, and a
# Referee who wants the Guide's Foreven rather than their own should be able
# to have it. That is what this tier is.

_AVALAR = "SCG p.46 - Avalar Consulate world table"

# The 27 systems of the Avalar Consulate (SCG p.46). 'Lun' is a moon, 'Pres'
# a presidio - a fortress system of the Consular Armada.
SCG_AVALAR: List[CanonicalWorld] = [
    CanonicalWorld(hex="1234", name="Amanecer", uwp="C212347-9",
                   remarks="Ic Lo", gas_giant="G"),
    CanonicalWorld(hex="1335", name="Ardiente", uwp="B461885-B",
                   remarks="Ri", gas_giant="G"),
    CanonicalWorld(hex="1432", name="Rocaroja", uwp="B100798-A", bases="N",
                   remarks="Na Va", gas_giant="G"),
    CanonicalWorld(hex="1534", name="Acerbo", uwp="E877100-7",
                   remarks="Lo", gas_giant="X"),
    CanonicalWorld(hex="1536", name="Lun Varga", uwp="C336412-9",
                   remarks="Ni", gas_giant="G"),
    CanonicalWorld(hex="1539", name="Horizonte", uwp="D87A653-6",
                   remarks="Ni Wa", gas_giant="G"),
    CanonicalWorld(hex="1630", name="Lun Escarpa", uwp="B400310-C", bases="N",
                   remarks="Ht Lo Va", gas_giant="G"),
    CanonicalWorld(hex="1631", name="Buergeria", uwp="C542635-6",
                   remarks="Ni Po", gas_giant="G"),
    CanonicalWorld(hex="1632", name="Escandi", uwp="E746321-3",
                   remarks="Lo Lt", gas_giant="G"),
    CanonicalWorld(hex="1634", name="Hortali", uwp="A9B8787-C",
                   remarks="Fl Ht", gas_giant="X"),
    CanonicalWorld(hex="1636", name="Avalar", uwp="A75599C-C", bases="N",
                   remarks="Ga Hi Ht", gas_giant="G", sophont="Solomani",
                   sophont_transplanted=True,
                   source="SCG pp.6, 26 and 46 - capital of the Avalar "
                          "Consulate, a Solomani lost colony"),
    CanonicalWorld(hex="1637", name="Tranquilidad", uwp="C669638-8",
                   remarks="Ni Ri", gas_giant="X",
                   source="SCG pp.45-46 - Avalar's first colony, settled 18"),
    CanonicalWorld(hex="1639", name="Lun Estrad", uwp="B4346A8-A",
                   remarks="Ni", gas_giant="G"),
    CanonicalWorld(hex="1640", name="Orilla", uwp="B400233-C", bases="N",
                   remarks="Ht Lo Va", gas_giant="X"),
    CanonicalWorld(hex="1734", name="Pres Tinto", uwp="B452464-C", bases="ZM",
                   remarks="Ht Ni Po", gas_giant="X",
                   source="SCG pp.46-47 - a Consular Armada fortress system, "
                          "entirely under Armada rule"),
    CanonicalWorld(hex="1738", name="Pres Alfa", uwp="B443454-C", bases="ZM",
                   remarks="Ht Ni Po", gas_giant="G",
                   source="SCG pp.46-47 - a Consular Armada fortress system"),
    CanonicalWorld(hex="1739", name="Lun Rico", uwp="D442221-7",
                   remarks="Lo Po", gas_giant="G"),
    CanonicalWorld(hex="1833", name="Salacia", uwp="C98A154-C",
                   remarks="Ht Lo Wa", gas_giant="G"),
    CanonicalWorld(hex="1834", name="Cloacina", uwp="C510647-8",
                   remarks="Na Ni", gas_giant="G"),
    CanonicalWorld(hex="1840", name="Atun", uwp="C66A336-A",
                   remarks="Lo Wa", gas_giant="G"),
    CanonicalWorld(hex="1936", name="Tresca", uwp="D76A340-6",
                   remarks="Lo Wa", gas_giant="G"),
    CanonicalWorld(hex="1938", name="Zuekgoz", uwp="C657864-6", bases="M",
                   remarks="Ga", zone="A", gas_giant="G", sophont="Vargr",
                   sophont_transplanted=True,
                   source="SCG pp.25-26, 45-46 - a Vargr world under Avalar "
                          "military occupation; the polity chapter spells it "
                          "Zuekgov"),
    CanonicalWorld(hex="2135", name="Fragos", uwp="A000641-C", bases="N",
                   remarks="As Ht Na Ni Va", gas_giant="G"),
    CanonicalWorld(hex="2136", name="Ninfa", uwp="B567757-B",
                   remarks="Ag Ri", gas_giant="G"),
    CanonicalWorld(hex="2137", name="Drevas", uwp="D410444-9",
                   remarks="Ni", gas_giant="G"),
    CanonicalWorld(hex="2236", name="Larissa", uwp="C659841-7",
                   gas_giant="G"),
    CanonicalWorld(hex="2237", name="Lun Orcus", uwp="B100341-C", bases="N",
                   remarks="Ht Lo Va", gas_giant="G"),
]

# Every world in that table is Avalar's by definition - the guide draws the
# border first and then counts 27 systems inside it - and the rows that carry
# no note of their own are established by the table itself.
for _world in SCG_AVALAR:
    _world.allegiance = _world.allegiance or "Av"
    _world.source = _world.source or _AVALAR
del _world

_TLESHO = ("SCG pp.24-25 and 55-61 - the Tlesho Union of the Tlinzha, an "
           "armed neutrality that fires on unauthorised visitors")

# The four systems of the Tlesho Union (SCG p.61 map, pp.24-25 narrative).
# Tlesho's table entry reads B998844-A; the narrative upgrades it to Class A
# to support a starfaring minor race, and the sophont chapter prints the
# upgraded profile, so that is what is used here.
SCG_TLESHO_UNION: List[CanonicalWorld] = [
    CanonicalWorld(hex="0720", name="Tlesho", uwp="A998844-A",
                   physical_profile="998", climate="Temperate",
                   bases="M", zone="A", allegiance="TlU", sophont="Tlinzha",
                   stars="F5 V M3 V",
                   source=_TLESHO + "; their homeworld, a heavy world of a "
                                    "flare-prone red dwarf orbiting an F5"),
    CanonicalWorld(hex="0819", name="Zhdikevli", uwp="B226586-A", bases="M",
                   zone="A", allegiance="TlU", sophont="Tlinzha",
                   sophont_transplanted=True,
                   source=_TLESHO + "; a buffer colony"),
    CanonicalWorld(hex="0820", name="Chtenchee", uwp="C24A694-A", bases="M",
                   zone="A", allegiance="TlU", sophont="Tlinzha",
                   sophont_transplanted=True,
                   source=_TLESHO + "; floating habitats on a waterworld, "
                                    "settled sublight in -1833"),
    CanonicalWorld(hex="0919", name="Zdefr", uwp="D000340-A", bases="M",
                   zone="A", allegiance="TlU", sophont="Tlinzha",
                   sophont_transplanted=True,
                   source=_TLESHO + "; asteroid-belt buffer colonies"),
]

_NATIVES = "SCG p.24 - native sophont homeworlds and Ancients ruins"

# Foreven's native sophonts and the Ancients sites among them (SCG p.24).
# The physical profile is the guide's own column; where it disagrees with the
# printed UWP, as at 2328, the UWP is used and the discrepancy noted.
SCG_NATIVE_SOPHONTS: List[CanonicalWorld] = [
    CanonicalWorld(hex="0103", uwp="E5589BD-3", physical_profile="558",
                   climate="Temperate", zone="R", allegiance="ZhIN",
                   sophont="Native",
                   source=_NATIVES + "; Zhodani Forbidden zone, protective "
                                     "interdiction"),
    CanonicalWorld(hex="0214", uwp="E5209EF-6", physical_profile="520",
                   climate="Hot", zone="R", allegiance="ZhIN",
                   sophont="Native",
                   source=_NATIVES + "; Zhodani Forbidden zone, xenophobic "
                                     "natives"),
    CanonicalWorld(hex="0825", uwp="X677776-4", physical_profile="677",
                   climate="Temperate", sophont="Native",
                   source=_NATIVES + "; isolated, with unsanctioned trading"),
    CanonicalWorld(hex="1628", uwp="C6A688A-9", physical_profile="6A6",
                   climate="Temperate", sophont="Native",
                   source=_NATIVES + "; exotic atmosphere, spacefaring"),
    CanonicalWorld(hex="1725", uwp="E223686-3", physical_profile="223",
                   climate="Cold", sophont="Native",
                   source=_NATIVES + "; mostly subterranean, possibly a gas "
                                     "giant moon"),
    CanonicalWorld(hex="1927", uwp="E666988-7", physical_profile="666",
                   climate="Temperate", sophont="Native",
                   source=_NATIVES + "; contact with the Darrians?"),
    CanonicalWorld(hex="2328", uwp="D87A653-5", physical_profile="87A",
                   climate="Temperate", sophont="Native",
                   source=_NATIVES + "; contact with the Darrians? The "
                                     "guide's physical column reads 755, its "
                                     "printed UWP 87A"),
    # The four Ancients sites: profiled physically, socially undetermined.
    CanonicalWorld(hex="1726", physical_profile="300", climate="Temperate",
                   ruins=True, barren=True, source=_NATIVES + "; Ancients ruins"),
    CanonicalWorld(hex="2615", physical_profile="300", climate="Temperate",
                   ruins=True, barren=True, source=_NATIVES + "; Ancients ruins"),
    CanonicalWorld(hex="2740", physical_profile="000", climate="Hot",
                   ruins=True, barren=True, source=_NATIVES + "; Ancients ruins"),
    CanonicalWorld(hex="3006", physical_profile="100", climate="Temperate",
                   ruins=True, barren=True, zone="R", allegiance="ZhIN",
                   source=_NATIVES + "; Ancients ruins under Zhodani military "
                                     "interdiction"),
]

_SCATTERED = "SCG pp.25-26 - scattered settlements"

# Populations that arrived long before the current settlement wave: Ancients
# transplants, lost colonies of the First and Second Imperiums, Aslan
# deviants and wandering Vargr (SCG pp.25-26). Avalar (1636) and Parthinia
# (3018) belong to this table too and are carried by their own entries.
SCG_SCATTERED_SETTLEMENTS: List[CanonicalWorld] = [
    CanonicalWorld(hex="0104", uwp="B35A515-E", physical_profile="35A",
                   climate="Temperate", allegiance="ZhIN", sophont="Chirper",
                   source=_SCATTERED + "; a Zhodani science 'corp' holds 80% "
                                       "of the system"),
    CanonicalWorld(hex="0131", uwp="A654956-E", physical_profile="654",
                   climate="Temperate", zone="R", sophont="Aslan",
                   source=_SCATTERED + "; Aslan deviants fleeing the Cultural "
                                       "Purge, now interdicted xenophobic "
                                       "cyborgs"),
    CanonicalWorld(hex="0408", uwp="D997648-1", physical_profile="997",
                   climate="Temperate", zone="R", allegiance="ZhIN",
                   sophont="Minor Human",
                   source=_SCATTERED + "; Zhodani Forbidden zone, protective "
                                       "interdiction"),
    CanonicalWorld(hex="0708", uwp="B66A767-C", physical_profile="66A",
                   climate="Temperate", zone="A", allegiance="ZhIN",
                   sophont="Solomani",
                   source=_SCATTERED + "; an Unabsorbed world under Zhodani "
                                       "military rule"),
    CanonicalWorld(hex="0935", uwp="C57488D-9", physical_profile="574",
                   climate="Temperate", sophont="Droyne",
                   source=_SCATTERED + "; an isolationist Droyne coyn"),
    CanonicalWorld(hex="1216", uwp="B767837-9", physical_profile="767",
                   climate="Temperate", allegiance="ZhIN", sophont="Droyne",
                   source=_SCATTERED + "; Droyne, full members of the "
                                       "Consulate"),
    CanonicalWorld(hex="1303", uwp="X76737B-0", physical_profile="767",
                   climate="Hot", zone="R", allegiance="ZhIN",
                   sophont="Chirper",
                   source=_SCATTERED + "; Zhodani Forbidden zone, protective "
                                       "interdiction"),
    CanonicalWorld(hex="2823", uwp="C699876-8", physical_profile="699",
                   climate="Temperate", sophont="Vargr",
                   source=_SCATTERED + "; warring Vargr states on the "
                                       "Spinward Main, 80% of the system"),
    CanonicalWorld(hex="2835", uwp="C577757-7", physical_profile="577",
                   climate="Temperate", sophont="Minor Human",
                   source=_SCATTERED + "; open for trade"),
    CanonicalWorld(hex="3018", name="Parthinia", uwp="C694655-C",
                   remarks="Ag Ht Ni", pbg="006", allegiance="Na",
                   sophont="Minor Human",
                   source=_SCATTERED + "; the Issugur, held to remote "
                                       "reservations (Classic Traveller "
                                       "Alien Realms)"),
]

# By definition none of these species evolved where they now live: they were
# moved by the Ancients, stranded by a fallen empire, or wandered here.
for _world in SCG_SCATTERED_SETTLEMENTS:
    _world.sophont_transplanted = True
del _world

_BARREN = ("SCG p.8 Decision #5 - the 'Bermuda Triangle' of subsector J, "
           "where colonies fail and ships sometimes disappear")

# The barren clusters (SCG p.8), given Class X starports except the two
# garden worlds, which keep a cleared landing area (SCG p.27).
SCG_BARREN: List[CanonicalWorld] = [
    CanonicalWorld(hex="1124", barren=True, starport="X", source=_BARREN),
    CanonicalWorld(hex="1224", barren=True, starport="E",
                   source=_BARREN + "; a garden world, its safe landing areas "
                                    "mapped by an earlier survey"),
    CanonicalWorld(hex="1325", barren=True, starport="E",
                   source=_BARREN + "; a garden world, its safe landing areas "
                                    "mapped by an earlier survey"),
    CanonicalWorld(hex="1422", barren=True, starport="X", source=_BARREN),
    CanonicalWorld(hex="1423", barren=True, starport="X", gas_giant="X",
                   source=_BARREN + "; the only jump-2 link between the two "
                                    "clusters, and with no gas giant it "
                                    "forces an ocean refuelling"),
    CanonicalWorld(hex="1523", barren=True, starport="X", source=_BARREN),
    CanonicalWorld(hex="1622", barren=True, starport="X", source=_BARREN),
    CanonicalWorld(hex="0822", barren=True, starport="X",
                   source=_BARREN + "; on the periphery of the zone"),
    CanonicalWorld(hex="1218", barren=True, starport="X",
                   source=_BARREN + "; on the periphery of the zone"),
    CanonicalWorld(hex="1319", barren=True, starport="X",
                   source=_BARREN + "; on the periphery of the zone"),
    CanonicalWorld(hex="1419", barren=True, starport="X",
                   source=_BARREN + "; on the periphery of the zone"),
    CanonicalWorld(hex="2209", barren=True, starport="X", allegiance="ZhIN",
                   source=_BARREN + "; barren inside the Zhodani Consulate, "
                                    "which may or may not be the same anomaly"),
    CanonicalWorld(hex="2309", barren=True, starport="X", allegiance="ZhIN",
                   source=_BARREN + "; barren inside the Zhodani Consulate, "
                                    "which may or may not be the same anomaly"),
    CanonicalWorld(hex="2310", barren=True, starport="X", allegiance="ZhIN",
                   source=_BARREN + "; barren inside the Zhodani Consulate, "
                                    "which may or may not be the same anomaly"),
]

_WAYPOINT = ("Zhodani route waypoint: travellermap.com runs route lines from "
             "the Ziafrplians sector to this hex, so it carries naval and "
             "military bases and a starport of at least Class B")

# The guide names these twice and disagrees with itself: p.27 lists 2602,
# p.63 lists 2802. Both are carried, because both are annotations rather than
# survey results - and that settles it on its own. The guide's whole reason
# for the list is that travellermap.com draws route lines to these hexes, and
# travellermap.com has no star at 2802, so 2802 quietly does nothing while
# 2602 takes effect.
SCG_ZHODANI_WAYPOINTS: List[CanonicalWorld] = [
    CanonicalWorld(hex="1102", source=f"SCG pp.27, 63 - {_WAYPOINT}"),
    CanonicalWorld(hex="1701", source=f"SCG pp.27, 63 - {_WAYPOINT}"),
    CanonicalWorld(hex="3201", source=f"SCG pp.27, 63 - {_WAYPOINT}"),
    CanonicalWorld(hex="2602",
                   source=f"SCG p.27 - {_WAYPOINT}. p.63 gives 2802 instead"),
    CanonicalWorld(hex="2802",
                   source=f"SCG p.63 - {_WAYPOINT}. p.27 gives 2602 instead, "
                          f"and the surveyed map has no star at 2802"),
]

_CAGE = ("SCG p.64 - a naval base completing the Imperial Navy's three-parsec "
         "'cage' around the Droyne systems of Andor and Candory in the Five "
         "Sisters subsector; the guide makes these worlds Imperial client "
         "states with at least a Class B starport")

SCG_IMPERIAL_CAGE: List[CanonicalWorld] = [
    CanonicalWorld(hex="3135", source=_CAGE),
    CanonicalWorld(hex="3228",
                   source=_CAGE + ". The surveyed map has no star at 3228; "
                                  "the nearest are 3232 and 3238"),
]

for _world in SCG_ZHODANI_WAYPOINTS:
    _world.annotation_only = True
    _world.starport_floor = "B"
    _world.bases = "KM"           # Zhodani naval, and so military too
    _world.allegiance = "ZhIN"
for _world in SCG_IMPERIAL_CAGE:
    _world.annotation_only = True
    _world.starport_floor = "B"
    _world.bases = "N"
    _world.allegiance = "CsIm"
del _world

# Tech Level ceilings the guide imposes polity-wide (SCG p.27).
SCG_FOREVEN_TECH_CEILINGS = {'ZhIN': 14, 'Av': 12}

SCG_FOREVEN_FULL: List[CanonicalWorld] = (
    SCG_AVALAR + SCG_TLESHO_UNION + SCG_NATIVE_SOPHONTS
    + SCG_SCATTERED_SETTLEMENTS + SCG_BARREN + SCG_ZHODANI_WAYPOINTS
    + SCG_IMPERIAL_CAGE
)


def scg_foreven_full() -> CanonicalSector:
    """The Sector Construction Guide's whole worked Foreven as an overlay.

    Where `scg_foreven()` carries only the seven worlds the reserve
    documentation itself establishes, this adds the sector the Guide builds
    on top of them: the Avalar Consulate's 27 systems, the Tlesho Union of
    the Tlinzha, eleven native sophont homeworlds and Ancients sites, ten
    scattered settlements, the fourteen barren worlds of the subsector J
    anomaly, the Zhodani route waypoints, the Imperial cage around Andor and
    Candory, and the Tech Level ceilings of both Consulates.

    None of it is canon and the Guide says so; it is one published, coherent
    treatment of a Referee's reserve, offered as an alternative to inventing
    the whole thing."""
    canon = merge_canon(
        scg_foreven(),
        _overlay_from(SCG_FOREVEN_FULL,
                      "Mongoose Traveller Sector Construction Guide, the "
                      "worked Foreven example (pp.8, 24-27, 46, 61, 63-64)"))
    canon.tech_level_ceilings.update(SCG_FOREVEN_TECH_CEILINGS)
    return canon


def _overlay_world(existing: CanonicalWorld, world: CanonicalWorld) -> None:
    """Layers one entry's stated facts over another's. Non-blank wins."""
    for attribute, value in vars(world).items():
        if attribute in ('hex', 'annotation_only'):
            continue
        if value and not _is_placeholder(str(value)):
            setattr(existing, attribute, value)
    # A hex stays annotation-only only while every source for it is: one
    # source surveying a star there is enough to establish the system.
    existing.annotation_only = existing.annotation_only and world.annotation_only


def _overlay_from(worlds: List[CanonicalWorld], source: str) -> CanonicalSector:
    """Builds a CanonicalSector from a list, merging repeated hexes rather
    than letting a later entry silently replace an earlier one."""
    canon = CanonicalSector(name="Foreven", source=source)
    for world in worlds:
        existing = canon.worlds.get(world.hex)
        if existing is None:
            canon.worlds[world.hex] = CanonicalWorld(**vars(world))
        else:
            _overlay_world(existing, world)
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
    merged.tech_level_ceilings = dict(base.tech_level_ceilings)
    merged.tech_level_ceilings.update(overlay.tech_level_ceilings)

    for hex_coord, world in overlay.worlds.items():
        existing = merged.worlds.get(hex_coord)
        if existing is None:
            merged.worlds[hex_coord] = CanonicalWorld(**vars(world))
        else:
            _overlay_world(existing, world)
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

    # The physical profile comes first: a source may state what a world
    # physically is without ever settling what society lives on it.
    if world.physical_profile and len(world.physical_profile.strip()) == 3:
        size, atmosphere, hydrographics = world.physical_profile.strip()
        mainworld.size_code = size
        mainworld.atmosphere_code = atmosphere
        mainworld.hydrographics_code = hydrographics
        mainworld.uwp.size = size
        mainworld.uwp.atmosphere = atmosphere
        mainworld.uwp.hydrographics = hydrographics

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

    if world.gas_giant == 'G' and system.gas_giant_count == 0:
        system.gas_giant_count = 1
    elif world.gas_giant == 'X':
        system.gas_giant_count = 0

    if world.has_stars:
        _apply_canonical_stars(system, world.stars)

    # A barren world is a statement about the whole society, so it is applied
    # after the UWP: a source can give a physical profile and still say
    # nobody lives there.
    if world.barren:
        _make_barren(system, mainworld)
        if not world.has_name:
            system.name = mainworld.name = _survey_designation(mainworld)

    if world.starport:
        mainworld.uwp.starport = world.starport.strip()[0]
    elif world.starport_floor:
        _raise_starport(mainworld, world.starport_floor.strip()[0])

    if world.max_tech_level and not world.has_uwp:
        current = Utils.from_eHex(mainworld.uwp.tech_level)
        if current > world.max_tech_level:
            mainworld.uwp.tech_level = Utils.eHex(world.max_tech_level)

    if world.climate:
        mainworld.notes.append(f"Canonical climate: {world.climate}")
    if world.ruins:
        mainworld.extinct_sophont = True
        mainworld.notes.append("Ancients site")
    if world.source:
        mainworld.notes.append(f"Canonical world: {world.source}")


# Starport classes, best first. X is not on the scale: it means there is no
# starport at all, so nothing is ever "raised" to it or held back by it.
_STARPORT_ORDER = 'ABCDE'


def _raise_starport(mainworld, floor: str) -> None:
    """Raises a world's starport to at least `floor`, as a source that says
    'Class B if randomly generated to be of a lower class' requires."""
    current = mainworld.uwp.starport
    if floor not in _STARPORT_ORDER:
        return
    if (current not in _STARPORT_ORDER
            or _STARPORT_ORDER.index(current) > _STARPORT_ORDER.index(floor)):
        mainworld.uwp.starport = floor


def _make_barren(system, mainworld) -> None:
    """Empties a world a source declares barren.

    Population 0 takes the whole society with it - a world nobody lives on
    has no government, no law and no technology base - so the social half of
    the UWP goes to zero rather than keeping numbers nobody is left to
    justify."""
    mainworld.uwp.population = '0'
    mainworld.uwp.government = '0'
    mainworld.uwp.law_level = '0'
    mainworld.uwp.tech_level = '0'
    mainworld.uwp.starport = 'X'
    mainworld.total_population = 0
    mainworld.population_digit = 0
    mainworld.nations = []
    system.bases = []
    for body in system.all_bodies:
        if body is not mainworld:
            body.is_secondary_world = False
    # Ba, Va, De and the rest describe the world it is now, not the one that
    # was generated before canon emptied it.
    from .society import generate_trade_codes
    generate_trade_codes(mainworld)
    mainworld.notes.append("Barren: no population")


def _survey_designation(mainworld) -> str:
    """The Scout Service's name for a world nobody named.

    "Barren systems may not have names but just numeric designations. A
    convention used by the Imperial Interstellar Scout Service is of the
    format XXX-YYY where XXX corresponds to the mainworld's physical
    characteristics and YYY is a unique sequence number" (SCG p.63)."""
    profile = (f"{mainworld.uwp.size}{mainworld.uwp.atmosphere}"
               f"{mainworld.uwp.hydrographics}")
    return f"{profile}-{random.randint(100, 999)}"


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


def place_canonical_sophonts(sector: Sector, canon: CanonicalSector) -> int:
    """Registers the species a source names, and returns how many were placed.

    This has to run *before* systems are generated: a sophont homeworld
    carries a +6 Population DM (SCG p.22), so who lives on a world changes
    how many of them there are. A generated homeworld already in the hex is
    replaced - canon says which species evolved there."""
    from .sophont import generate_minor_race, get_catalogued_race

    placed = 0
    for world in canon.sophont_worlds():
        name = world.sophont.strip()
        if name.lower() == 'native':
            # A source can establish that a world evolved its own sophonts
            # without ever naming them - the guide names only the Tlinzha and
            # leaves the rest as "Native". The species is fact; the name is
            # the Referee's, so it is rolled.
            sophont = generate_minor_race(world.hex)
        else:
            sophont = get_catalogued_race(name, world.hex)
        if world.sophont_transplanted:
            sophont.history_summary += (
                f" They did not evolve at {world.hex}: this is a settlement, "
                f"not their homeworld.")
        sector.native_sophonts[world.hex] = sophont
        placed += 1
    return placed


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
    # A world a source declares barren is nobody's. Letting a procedural
    # empire sweep up the hexes of a zone where colonies fail would erase the
    # very thing the source established.
    reserved |= {h for h, w in canon.worlds.items()
                 if w.barren and h in sector.systems}
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
