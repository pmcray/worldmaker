"""Traveller5 Second Survey sector data output.

Implements both formats travellermap.com defines for T5SS sector data: the
column-delimited format (human readable, self-describing widths) and the
tab-delimited format (recommended for interchange).

The column format is a header line, a separator line of dash runs that
defines each field's width, and one data line per world. Fields are left
aligned, padded with spaces and separated by a single space. The canonical
example from the format specification is::

    Hex  Name        UWP       Remarks          {Ix}  (Ex)    [Cx]   N     B Z PBG W  A  Stellar
    ---- ----------- --------- ---------------- ----- ------- ------ ----- - - --- -- -- -------
    0133 Emape       B564500-B Ag Ni Pr Da      { 2 } (A46+2) [1716] BcC   N A 503 6  Im M0 V

Field order follows the T5SS standard: Hex, Name, UWP, Remarks, Ix, Ex, Cx,
N, B, Z, PBG, W, A, Stellar.
"""
from typing import Any, Dict, List, Optional, Tuple

from .classes import Sector, StellarSystem
from .utils import Utils

# Field name and the minimum width each takes in the specification's example.
# Actual widths grow to fit the data, which is what the separator line
# records for the parser.
T5_FIELDS: List[Tuple[str, int]] = [
    ('Hex', 4),
    ('Name', 11),
    ('UWP', 9),
    ('Remarks', 16),
    ('{Ix}', 5),
    ('(Ex)', 7),
    ('[Cx]', 6),
    ('N', 5),
    ('B', 1),
    ('Z', 1),
    ('PBG', 3),
    ('W', 2),
    ('A', 2),
    ('Stellar', 7),
]

# Base letters used in the Bases field (T5SS uses one letter per base).
BASE_CODES = {
    'Naval': 'N',
    'Zhodani Naval': 'N',
    'Scout': 'S',
    'Military': 'M',
    'Waystation': 'W',
    'Way Station': 'W',
    'Corsair': 'C',
    'Depot': 'D',
    'Embassy': 'E',
    'Exploration': 'V',
}

# Noble ranks, least to most senior (T5). The assignment below is this
# project's own reading of "more important worlds carry more titles"; the
# Traveller5 rulebook's exact table is not reproduced here.
NOBLE_RANKS = ['B', 'c', 'C', 'D', 'e', 'E', 'f', 'F', 'G', 'H']


def _mainworld(system: StellarSystem):
    return system.mainworld


def t5_hex(hex_coord: str) -> str:
    return hex_coord


def t5_name(system: StellarSystem) -> str:
    """The mainworld's name. A world with no name at all takes the '.'
    placeholder the format defines."""
    mainworld = _mainworld(system)
    name = (getattr(mainworld, 'name', '') or system.name or '').strip()
    return name or '.'


def t5_uwp(system: StellarSystem) -> str:
    mainworld = _mainworld(system)
    if mainworld is None or not mainworld.uwp.starport:
        return 'X000000-0'
    return str(mainworld.uwp)


def t5_remarks(system: StellarSystem, sector: Sector = None,
               hex_coord: str = None) -> str:
    """Trade classifications, plus the native sophont code where the sector
    records a homeworld in this hex."""
    mainworld = _mainworld(system)
    codes = list(getattr(mainworld, 'trade_codes', []) or [])

    if sector is not None and hex_coord is not None:
        sophont = sector.native_sophonts.get(hex_coord)
        if sophont is not None:
            # T5SS writes a sophont homeworld as a parenthesised name
            codes.append(f"({sophont.name})")

    return " ".join(codes)


def t5_importance(system: StellarSystem) -> str:
    """Importance extension, written as '{ 2 }'."""
    mainworld = _mainworld(system)
    importance = int(getattr(mainworld, 'importance', 0) or 0)
    return f"{{ {importance} }}"


def t5_economic(system: StellarSystem) -> str:
    """Economic extension, '(A46+2)': resources, labour and infrastructure in
    eHex, then signed efficiency."""
    mainworld = _mainworld(system)
    extension = getattr(mainworld, 'economic_extension', '') or ''
    if extension:
        return extension
    return '(000+0)'


def t5_cultural(system: StellarSystem) -> str:
    """Cultural extension, '[1716]'.

    T5's four digits are Homogeneity, Acceptance, Strangeness and Symbols.
    The generator produces the World Builder's Handbook's eight cultural
    traits instead, so the four are read off the WBH traits covering the
    same ground: cohesion, xenophilia, uniqueness and symbology."""
    mainworld = _mainworld(system)
    profile = getattr(mainworld, 'cultural_profile', None)
    if profile is None:
        return '[0000]'

    def digit(value):
        return Utils.eHex(max(0, min(33, int(value or 0))))

    return (f"[{digit(profile.cohesion)}{digit(profile.xenophilia)}"
            f"{digit(profile.uniqueness)}{digit(profile.symbology)}]")


def t5_nobility(system: StellarSystem) -> str:
    """Imperial noble ranks assigned to the world.

    Approximated from the world's Importance: a populated world carries a
    knight, and each further point of Importance adds the next rank."""
    mainworld = _mainworld(system)
    if mainworld is None:
        return ''
    population = Utils.from_eHex(mainworld.uwp.population)
    if population <= 0:
        return ''
    importance = int(getattr(mainworld, 'importance', 0) or 0)
    count = max(1, min(len(NOBLE_RANKS), importance + 1))
    return "".join(NOBLE_RANKS[:count])


def t5_bases(system: StellarSystem) -> str:
    """Base letters, one per base present, in a stable order."""
    letters = []
    for base in system.bases:
        letter = BASE_CODES.get(base)
        if letter and letter not in letters:
            letters.append(letter)
    return "".join(sorted(letters))


def t5_zone(system: StellarSystem) -> str:
    """Travel zone: A for Amber, R for Red, blank for Green."""
    return system.travel_zone if system.travel_zone in ('A', 'R') else ''


def t5_pbg(system: StellarSystem) -> str:
    """Population multiplier, planetoid belts and gas giants.

    The multiplier is the mainworld's population significant digit, and is
    zero on an unpopulated world."""
    mainworld = _mainworld(system)
    population = Utils.from_eHex(mainworld.uwp.population) if mainworld else 0
    if population <= 0:
        multiplier = 0
    else:
        multiplier = int(getattr(mainworld, 'population_digit', 0) or 1)
        multiplier = max(1, min(9, multiplier))
    belts = min(9, system.planetoid_belt_count)
    giants = min(9, system.gas_giant_count)
    return f"{multiplier}{Utils.eHex(belts)}{Utils.eHex(giants)}"


def t5_worlds(system: StellarSystem) -> str:
    """Number of worlds in the system: every placed body plus its
    significant moons."""
    count = 0
    for world in system.all_worlds:
        count += 1
        count += sum(1 for s in world.satellites
                     if not s.is_ring and s.size_code not in ('', 'R'))
    return str(count)


def t5_allegiance(system: StellarSystem) -> str:
    """Allegiance code; '--' marks space claimed by nobody."""
    allegiance = (system.allegiance or '').strip()
    if not allegiance or allegiance == 'Na':
        return 'Na'
    return allegiance


def t5_stellar(system: StellarSystem) -> str:
    """Morgan-Keenan classifications of every star, space separated."""
    types = [s.spectral_type for s in system.stars
             if not s.is_composite and s.spectral_type]
    return " ".join(types)


def t5_row(hex_coord: str, system: StellarSystem,
           sector: Sector = None) -> Optional[Dict[str, str]]:
    """The T5SS field values for one system, or None when the system has no
    mainworld to describe."""
    if _mainworld(system) is None:
        return None
    return {
        'Hex': t5_hex(hex_coord),
        'Name': t5_name(system),
        'UWP': t5_uwp(system),
        'Remarks': t5_remarks(system, sector, hex_coord),
        '{Ix}': t5_importance(system),
        '(Ex)': t5_economic(system),
        '[Cx]': t5_cultural(system),
        'N': t5_nobility(system),
        'B': t5_bases(system),
        'Z': t5_zone(system),
        'PBG': t5_pbg(system),
        'W': t5_worlds(system),
        'A': t5_allegiance(system),
        'Stellar': t5_stellar(system),
    }


def _sorted_rows(sector: Sector) -> List[Dict[str, str]]:
    """Every describable system, in hex order (the convention for T5SS
    files: down each column, then across)."""
    rows = []
    for hex_coord in sorted(sector.systems):
        row = t5_row(hex_coord, sector.systems[hex_coord], sector)
        if row is not None:
            rows.append(row)
    return rows


def _column_widths(rows: List[Dict[str, str]]) -> List[Tuple[str, int]]:
    """Each field's width: wide enough for its header, its specification
    minimum and its widest value."""
    widths = []
    for name, minimum in T5_FIELDS:
        width = max(minimum, len(name),
                    max((len(row[name]) for row in rows), default=0))
        widths.append((name, width))
    return widths


def _header_lines(sector: Sector, widths: List[Tuple[str, int]]) -> List[str]:
    """The comment block, header line and separator line."""
    lines = [
        f"# {sector.name}",
        "# Traveller5 Second Survey, column delimited",
    ]
    if sector.subsector_names:
        for letter in sorted(sector.subsector_names):
            lines.append(f"# Subsector {letter}: {sector.subsector_names[letter]}")
    lines.append("#")
    lines.append(" ".join(name.ljust(width) for name, width in widths).rstrip())
    lines.append(" ".join("-" * width for _, width in widths))
    return lines


def export_sector_t5_column(sector: Sector) -> str:
    """Column-delimited T5 Second Survey data for a sector."""
    rows = _sorted_rows(sector)
    widths = _column_widths(rows)
    lines = _header_lines(sector, widths)
    for row in rows:
        lines.append(" ".join(row[name].ljust(width)
                              for name, width in widths).rstrip())
    return "\n".join(lines) + "\n"


def export_sector_t5_tab(sector: Sector) -> str:
    """Tab-delimited T5 Second Survey data, the format travellermap.com
    recommends for interchange."""
    rows = _sorted_rows(sector)
    names = [name for name, _ in T5_FIELDS]
    lines = ["\t".join(names)]
    for row in rows:
        lines.append("\t".join(row[name] for name in names))
    return "\n".join(lines) + "\n"


def parse_t5_column(text: str) -> List[Dict[str, str]]:
    """Reads column-delimited T5 data back into field dictionaries.

    Widths come from the separator line and names from the header line, as
    the specification requires - the round trip is what proves the output
    columns line up."""
    lines = [line for line in text.splitlines()
             if line.strip() and not line.startswith('#')]
    if len(lines) < 2:
        return []

    header, separator = lines[0], lines[1]

    # Field spans come from the runs of dashes on the separator line
    spans = []
    start = None
    for index, char in enumerate(separator):
        if char == '-' and start is None:
            start = index
        elif char != '-' and start is not None:
            spans.append((start, index))
            start = None
        elif char not in ('-', ' '):
            raise ValueError(f"bad separator character {char!r} at {index}")
    if start is not None:
        spans.append((start, len(separator)))

    names = [header[a:b].strip() for a, b in spans]

    rows = []
    for line in lines[2:]:
        padded = line.ljust(spans[-1][1])
        # Anything between fields must be blank, or the columns do not align
        for (_, end), (next_start, _) in zip(spans, spans[1:]):
            if padded[end:next_start].strip():
                raise ValueError(f"data between fields in line: {line!r}")
        rows.append({name: padded[a:b].strip()
                     for name, (a, b) in zip(names, spans)})
    return rows
