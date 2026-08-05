"""Finding the worlds worth looking at.

A generated sector holds several hundred systems and several thousand
bodies, and almost all of them are unremarkable rock. This module reads a
sector and surfaces the places that would actually change what happens at
the table: a world with a native sophont species, a ruin left by an extinct
one, a pulsar sterilising everything in its system, a moon that is its
system's mainworld, a habitable world nobody has settled.

Each finding carries the reasons it was flagged, so a Referee sees *why*
something surfaced rather than a bare ranking.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .stellar import is_exotic, lum_class_of
from .utils import Utils

# Stellar objects that make a system worth a detour, and what they are worth.
EXOTIC_STARS = {
    'Black Hole': (10, "a black hole"),
    'Neutron Star': (9, "a neutron star"),
    'Pulsar': (9, "a pulsar, sterilising its system with radiation"),
    'Protostar': (8, "a protostar still forming"),
    'D': (6, "a white dwarf"),
    'D*': (6, "a white dwarf"),
    'BD': (5, "a brown dwarf"),
    'Nebula': (7, "an enveloping nebula"),
    'Star Cluster': (6, "a star cluster"),
}

GIANT_CLASSES = {
    'Ia': (6, "a supergiant primary"),
    'Ib': (6, "a supergiant primary"),
    'II': (5, "a bright giant primary"),
    'III': (4, "a giant primary"),
    'IV': (3, "a subgiant primary"),
    'VI': (3, "a subdwarf primary"),
}


@dataclass
class Notable:
    """One world or system worth a Referee's attention."""
    hex: str = ""
    system: Any = None
    body: Any = None
    kind: str = "mainworld"          # mainworld | secondary | system
    score: int = 0
    reasons: List[str] = field(default_factory=list)

    @property
    def name(self) -> str:
        return (getattr(self.body, 'name', '')
                or getattr(self.system, 'name', '') or "unnamed")

    @property
    def uwp(self) -> str:
        return str(getattr(self.body, 'uwp', '')) if self.body is not None else ""

    def summary(self) -> str:
        label = self.uwp or getattr(self.system, 'name', '')
        return (f"{self.hex}  {self.name:14s} {label:11s} "
                f"[{self.score:2d}] {self.kind:9s} {'; '.join(self.reasons)}")


# ------------------------------------------------------------- the checks

def _star_reasons(system: Any) -> List[Tuple[int, str]]:
    """What is unusual about a system's stars."""
    found = []
    for star in getattr(system, 'stars', []):
        if getattr(star, 'is_composite', False):
            continue
        spectral = star.spectral_type or ""
        if spectral in EXOTIC_STARS:
            found.append(EXOTIC_STARS[spectral])
            continue
        lum_class = lum_class_of(spectral)
        if lum_class in GIANT_CLASSES:
            found.append(GIANT_CLASSES[lum_class])

    ordinary = [s for s in getattr(system, 'stars', [])
                if not getattr(s, 'is_composite', False)]
    if len(ordinary) >= 4:
        found.append((3, f"{len(ordinary)} stars"))
    elif len(ordinary) == 3:
        found.append((2, "a triple star system"))

    age = getattr(system, 'age_gyr', 0.0) or 0.0
    if 0 < age < 0.01:
        found.append((7, "a protostar system, still forming"))
    elif 0 < age < 0.1:
        found.append((5, "a primordial system under 100 million years old"))
    return found


def _life_reasons(body: Any) -> List[Tuple[int, str]]:
    found = []
    if getattr(body, 'native_sophont', False):
        found.append((10, "a native sophont species"))
    if getattr(body, 'extinct_sophont', False):
        found.append((9, "the ruins of an extinct sophont species"))

    biomass = getattr(body, 'biomass_rating', 0) or 0
    complexity = getattr(body, 'biocomplexity_rating', 0) or 0
    if biomass >= 10 and complexity >= 8:
        found.append((4, "a rich and complex biosphere"))
    elif biomass >= 11:
        found.append((3, "a teeming biosphere"))
    return found


def _physical_reasons(body: Any) -> List[Tuple[int, str]]:
    found = []
    notes = " ".join(getattr(body, 'notes', []) or [])

    if 'Magma ocean' in notes:
        found.append((7, "an ocean of liquid magma"))
    if 'Tidally Locked' in notes:
        found.append((5, "tidally locked, with a permanent day and night side"))
    if 'Retrograde' in notes:
        found.append((4, "a retrograde orbit"))
    if 'Trojan' in notes:
        found.append((4, "a trojan orbit"))
    if 'Inclined Orbit' in notes:
        found.append((3, "a steeply inclined orbit"))

    stress = getattr(body, 'total_seismic_stress', 0.0) or 0.0
    if stress > 100:
        found.append((6, "constant volcanism and near-continuous earthquakes"))
    elif stress > 50:
        found.append((4, "frequent eruptions and major seismic activity"))

    atmosphere = Utils.from_eHex(getattr(body, 'atmosphere_code', 0) or 0)
    if atmosphere == 10:
        found.append((4, "an exotic atmosphere"))
    elif atmosphere == 11:
        found.append((5, "a corrosive atmosphere"))
    elif atmosphere == 12:
        found.append((6, "an insidious atmosphere"))

    taint = getattr(body, 'atmosphere_taint', None)
    if taint and 'Radioactive' in str(taint.get('type', '')):
        found.append((5, "a radioactive atmosphere"))

    if any(getattr(s, 'is_ring', False) for s in getattr(body, 'satellites', [])):
        found.append((2, "a ring system"))

    habitability = getattr(body, 'habitability_rating', 0) or 0
    population = Utils.from_eHex(getattr(getattr(body, 'uwp', None),
                                         'population', 0) or 0)
    if habitability >= 10 and population == 0:
        found.append((6, "highly habitable and completely unsettled"))
    elif habitability >= 11:
        found.append((3, "exceptionally habitable"))

    return found


def _social_reasons(body: Any, system: Any, sector: Any,
                    hex_coord: str) -> List[Tuple[int, str]]:
    found = []
    uwp = getattr(body, 'uwp', None)
    if uwp is None:
        return found

    population = Utils.from_eHex(uwp.population)
    tech_level = Utils.from_eHex(uwp.tech_level)
    government = Utils.from_eHex(uwp.government)

    if sector is not None and hex_coord in getattr(sector, 'native_sophonts', {}):
        sophont = sector.native_sophonts[hex_coord]
        found.append((9, f"the homeworld of the {sophont.name}"))

    nation_count = getattr(body, 'nation_count', 0) or 0
    if nation_count >= 50:
        found.append((5, f"balkanised into {nation_count} sovereign states"))
    elif nation_count >= 5:
        found.append((3, f"balkanised into {nation_count} states"))

    if population >= 9 and tech_level <= 5:
        found.append((7, "hugely populous and pre-industrial"))
    elif population >= 7 and tech_level <= 3:
        found.append((6, "populous and pre-industrial"))
    if tech_level >= 15:
        found.append((4, f"technology at TL{Utils.eHex(tech_level)}"))
    if population >= 10:
        found.append((3, "a population in the billions"))

    if getattr(body, 'proprietor', None):
        owner = body.proprietor.get('owner', 'a private holding')
        found.append((6, f"privately held by {owner}"))

    if government == 6:
        found.append((2, "under a captive government"))

    zone = getattr(system, 'travel_zone', '')
    if zone == 'R':
        found.append((6, "interdicted: a Red Zone"))
    elif zone == 'A':
        found.append((3, "an Amber Zone"))

    if getattr(body, 'is_secondary_world', False):
        if not getattr(body, 'affiliated', True):
            found.append((4, "an independent settlement away from the mainworld"))
        else:
            found.append((2, "a colony of the mainworld"))

    return found


def _role_reasons(body: Any, system: Any) -> List[Tuple[int, str]]:
    found = []
    if not getattr(body, 'is_mainworld', False):
        return found

    if getattr(body, 'parent_body', None) is not None:
        found.append((5, "a moon serving as its system's mainworld"))
    if getattr(body, 'body_type', '') == 'Planetoid Belt':
        found.append((4, "an asteroid belt serving as its system's mainworld"))
    return found


# --------------------------------------------------------------- scanning

def notability(body: Any, system: Any, sector: Any = None,
               hex_coord: str = "", include_stars: bool = True
               ) -> Tuple[int, List[str]]:
    """Scores one body, returning its total and the reasons behind it."""
    found: List[Tuple[int, str]] = []
    found += _life_reasons(body)
    found += _physical_reasons(body)
    found += _social_reasons(body, system, sector, hex_coord)
    found += _role_reasons(body, system)
    if include_stars:
        found += _star_reasons(system)

    if not found:
        return 0, []
    found = _dedupe(found)
    # Sum the weights, but let the strongest reason dominate the ordering so
    # a world with one extraordinary feature outranks one with five mild
    # ones.
    total = max(w for w, _ in found) * 2 + sum(w for w, _ in found)
    reasons = [text for _, text in sorted(found, key=lambda r: -r[0])]
    return total, reasons


def _dedupe(found: List[Tuple[int, str]]) -> List[Tuple[int, str]]:
    """Two stars of the same class are one reason, not two."""
    seen: Dict[str, int] = {}
    for weight, text in found:
        seen[text] = max(seen.get(text, 0), weight)
    return [(weight, text) for text, weight in seen.items()]


def find_notable(sector: Any, limit: int = 20, kind: str = None,
                 minimum_score: int = 1) -> List[Notable]:
    """The most interesting bodies in a sector, best first.

    `kind` filters to 'mainworld' or 'secondary'; omit it for both."""
    results: List[Notable] = []

    for hex_coord, system in getattr(sector, 'systems', {}).items():
        for body in system.all_bodies:
            if getattr(body, 'is_ring', False):
                continue
            if getattr(body, 'body_type', '') == 'Gas Giant':
                continue

            is_mainworld = bool(getattr(body, 'is_mainworld', False))
            is_secondary = bool(getattr(body, 'is_secondary_world', False))
            if not (is_mainworld or is_secondary):
                continue

            body_kind = 'mainworld' if is_mainworld else 'secondary'
            if kind and body_kind != kind:
                continue

            score, reasons = notability(
                body, system, sector, hex_coord,
                # A system's exotic star is a fact about the mainworld's
                # situation; a secondary world is already interesting for
                # its own reasons.
                include_stars=is_mainworld)
            if score < minimum_score:
                continue

            results.append(Notable(hex=hex_coord, system=system, body=body,
                                   kind=body_kind, score=score,
                                   reasons=reasons))

    results.sort(key=lambda n: (-n.score, n.hex))
    return results[:limit] if limit else results


def find_exotic_systems(sector: Any, limit: int = 20) -> List[Notable]:
    """Systems whose *stars* are the unusual thing - dead stars, protostars,
    giants and multiples - regardless of what orbits them."""
    results: List[Notable] = []
    for hex_coord, system in getattr(sector, 'systems', {}).items():
        found = _dedupe(_star_reasons(system))
        if not found:
            continue
        score = max(w for w, _ in found) * 2 + sum(w for w, _ in found)
        results.append(Notable(
            hex=hex_coord, system=system, body=system.mainworld,
            kind='system', score=score,
            reasons=[text for _, text in sorted(found, key=lambda r: -r[0])]))

    results.sort(key=lambda n: (-n.score, n.hex))
    return results[:limit] if limit else results


def describe_notable(entries: Sequence[Notable], title: str = "Notable worlds",
                     max_reasons: int = 3) -> str:
    """A readable rundown of what a scan turned up."""
    if not entries:
        return f"{title}: nothing stood out."
    lines = [title, ""]
    for entry in entries:
        reasons = entry.reasons[:max_reasons]
        extra = (f" (+{len(entry.reasons) - max_reasons} more)"
                 if len(entry.reasons) > max_reasons else "")
        lines.append(f"  {entry.hex}  {entry.name:14s} {entry.uwp:11s} "
                     f"{entry.kind:9s}")
        lines.append(f"        {'; '.join(reasons)}{extra}")
    return "\n".join(lines)
