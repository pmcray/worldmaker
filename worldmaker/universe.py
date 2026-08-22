"""Creating a Universe (SCG pp.3-8).

The Sector Construction Guide opens by asking the Referee to settle a
handful of high-level questions before rolling any dice: who inhabits this
universe, what themes run through it, how developed it is, how densely the
stars are packed, and whether any large-scale anomalies bend the standard
generation rules. This module turns those answers into the generation
parameters the rest of the package already understands, so a sector can be
built from a short description instead of a pile of arguments.

    universe = create_universe("Foreven Reach", theme="frontier",
                               density="standard", technology="imperial",
                               trajectory="expansion")
    universe.add_anomaly("barren", "The Quiet Zone", centre="1124", radius=2)
    sector = generate_universe_sector(universe, "Foreven")

Everything here is a starting sketch: the book is explicit that the outline
"may evolve and change, perhaps unrecognisably" once generation begins.
"""
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .classes import Sector
from .utils import Utils

# --------------------------------------------------------------- densities

# System density: the 1D target at or above which a hex holds a system
# (SCG p.9 - standard space is 4+, about half the hexes). The book notes
# jump-1 to jump-6 ships suit a 2-in-6 to 5-in-6 chance.
DENSITY_TARGETS = {
    'rift': 7,          # effectively empty: a gap between the stars
    'sparse': 6,        # 1 in 6
    'scattered': 5,     # 2 in 6
    'standard': 4,      # 3 in 6, the default
    'dense': 3,         # 4 in 6
    'cluster': 2,       # 5 in 6, a star cluster's heart
}

# Maximum generally available Tech Level (SCG p.3, "Background").
TECHNOLOGY_LEVELS = {
    'primitive': 5,     # pre-industrial holdouts, no starflight
    'early': 9,         # jump-1 just within reach
    'developing': 11,
    'imperial': 15,     # the Charted Space norm
    'advanced': 17,
}

# Trajectory of development, expressed as a universe-wide population DM.
TRAJECTORIES = {
    'expansion': 1,     # a time of growth and new colonies
    'stasis': 0,        # long-settled and unchanging
    'decline': -1,      # an empire past its prime
    'collapse': -2,     # scattered decaying outposts
    'recovery': -1,     # rebuilding after a fall
}

# How widespread native sophonts are (SCG p.4). Values are homeworlds per
# sixteen subsectors, scaled to the region actually generated.
SOPHONT_PREVALENCE = {
    'none': 0.0,
    'rare': 1.0,
    'standard': 8.0,
    'common': 20.0,
}

THEMES = {
    'frontier': "Expansion and conflict along a contested frontier",
    'decline': "The decline and fall of an old empire",
    'colonial': "Corporate, government and pioneer interests in competition",
    'contact': "Two major sophonts meeting where their colonies intersect",
    'isolation': "Scattered worlds separated by distance and danger",
    'recovery': "Rebuilding civilisation after a long dark age",
}


# --------------------------------------------------------------- anomalies

# Anomalies (SCG pp.4-5). Each bends generation in a bounded region.
ANOMALY_KINDS = {
    'rift': "An interstellar rift: few or no systems",
    'cluster': "A star cluster: systems packed tightly",
    'supernova': "A recent supernova sterilised these worlds",
    'barren': "Failed colonies and lost ships; the worlds stand empty",
    'ruins': "Ancient ruins from a long dead civilisation",
    'hazardous_jump': "Jump space is treacherous here",
    'plague': "A deadly disease keeps these worlds under interdiction",
    'tech_inhibitor': "Some effect suppresses technology",
    'warfare': "Endemic unrestricted warfare has wrecked the infrastructure",
}


@dataclass
class Anomaly:
    """A large-scale deviation from standard generation, covering a set of
    hexes (SCG pp.4-5)."""
    kind: str
    name: str = ""
    hexes: List[str] = field(default_factory=list)
    description: str = ""

    def __post_init__(self):
        if self.kind not in ANOMALY_KINDS:
            raise ValueError(
                f"unknown anomaly kind {self.kind!r}; "
                f"expected one of {sorted(ANOMALY_KINDS)}")
        if not self.description:
            self.description = ANOMALY_KINDS[self.kind]
        if not self.name:
            self.name = self.kind.replace('_', ' ').title()

    def covers(self, hex_coord: str) -> bool:
        return hex_coord in self.hexes


@dataclass
class TimelineEvent:
    """One entry in the universe's rough timeline (SCG p.5)."""
    year: int
    event: str

    def __str__(self) -> str:
        return f"{self.year:>7}  {self.event}"


@dataclass
class Universe:
    """The high-level sketch of a setting, and the generation parameters it
    implies (SCG pp.3-8)."""
    name: str = "Generated Universe"
    theme: str = 'frontier'
    density: str = 'standard'
    technology: str = 'imperial'
    trajectory: str = 'expansion'
    sophont_prevalence: str = 'standard'
    polity_count: int = 3
    current_year: int = 1105
    background: str = ""
    anomalies: List[Anomaly] = field(default_factory=list)
    timeline: List[TimelineEvent] = field(default_factory=list)

    # ------------------------------------------------------- derived values

    @property
    def density_target(self) -> int:
        """The baseline 1D system-presence target for this universe."""
        return DENSITY_TARGETS[self.density]

    @property
    def max_tech_level(self) -> int:
        """The maximum generally available Tech Level."""
        return TECHNOLOGY_LEVELS[self.technology]

    @property
    def population_dm(self) -> int:
        """The universe-wide population DM implied by its trajectory."""
        return TRAJECTORIES[self.trajectory]

    @property
    def theme_description(self) -> str:
        return THEMES.get(self.theme, self.theme)

    def density_target_for(self, hex_coord: str) -> int:
        """The system-presence target in one hex: the baseline, unless a rift
        or cluster anomaly covers it."""
        for anomaly in self.anomalies:
            if not anomaly.covers(hex_coord):
                continue
            if anomaly.kind == 'rift':
                return DENSITY_TARGETS['rift']
            if anomaly.kind == 'cluster':
                return DENSITY_TARGETS['cluster']
        return self.density_target

    def sophont_counts(self, sector: Sector) -> Tuple[int, int]:
        """(minor race homeworlds, major race homeworlds) for a sector of
        this size, from the prevalence setting."""
        per_sector = SOPHONT_PREVALENCE[self.sophont_prevalence]
        scale = (sector.width * sector.height) / 1280.0   # a full sector
        minor = int(round(per_sector * scale))
        if self.sophont_prevalence == 'none':
            return 0, 0
        major = 1 if self.sophont_prevalence in ('standard', 'common') else 0
        return max(0, minor), major

    def anomalies_at(self, hex_coord: str) -> List[Anomaly]:
        return [a for a in self.anomalies if a.covers(hex_coord)]

    # -------------------------------------------------------------- editing

    def add_anomaly(self, kind: str, name: str = "", hexes: List[str] = None,
                    centre: str = None, radius: int = 0,
                    description: str = "") -> Anomaly:
        """Adds an anomaly, either over an explicit hex list or over every
        hex within `radius` parsecs of `centre`."""
        from .sector import hex_distance, hex_to_coords

        covered = list(hexes or [])
        if centre is not None:
            col, row = hex_to_coords(centre)
            for c in range(max(1, col - radius - 1), col + radius + 2):
                for r in range(max(1, row - radius - 1), row + radius + 2):
                    candidate = f"{c:02d}{r:02d}"
                    if hex_distance(centre, candidate) <= radius:
                        covered.append(candidate)

        anomaly = Anomaly(kind=kind, name=name, hexes=sorted(set(covered)),
                          description=description)
        self.anomalies.append(anomaly)
        return anomaly

    def add_event(self, year: int, event: str) -> TimelineEvent:
        """Adds a timeline entry, keeping the timeline in date order."""
        entry = TimelineEvent(year=year, event=event)
        self.timeline.append(entry)
        self.timeline.sort(key=lambda e: e.year)
        return entry

    # ------------------------------------------------------------ reporting

    def describe(self) -> str:
        """The universe as a readable brief - the "broad sketch" the book
        asks for before generation begins."""
        lines = [f"# {self.name}", ""]
        lines.append(f"**Theme**: {self.theme_description}")
        lines.append(f"**Star density**: {self.density} "
                     f"(system on 1D {self.density_target}+)")
        lines.append(f"**Maximum Tech Level**: {self.max_tech_level} "
                     f"({self.technology})")
        lines.append(f"**Trajectory**: {self.trajectory} "
                     f"(population DM {self.population_dm:+d})")
        lines.append(f"**Native sophonts**: {self.sophont_prevalence}")
        lines.append(f"**Interstellar polities**: {self.polity_count}")
        lines.append(f"**Current year**: {self.current_year}")

        if self.background:
            lines += ["", "## Background", self.background]

        if self.anomalies:
            lines += ["", "## Anomalies"]
            for anomaly in self.anomalies:
                extent = (f"{len(anomaly.hexes)} hexes"
                          if anomaly.hexes else "sector-wide")
                lines.append(f"- **{anomaly.name}** ({extent}): "
                             f"{anomaly.description}")

        if self.timeline:
            lines += ["", "## Timeline"]
            for entry in self.timeline:
                lines.append(f"- {entry.year}: {entry.event}")

        return "\n".join(lines)

    # ----------------------------------------------------- applying effects

    def apply_anomalies(self, sector: Sector) -> None:
        """Applies every anomaly's effects to an already generated sector.

        Rift and cluster anomalies act during generation, through
        density_target_for, and so do nothing here."""
        for anomaly in self.anomalies:
            handler = _ANOMALY_HANDLERS.get(anomaly.kind)
            if handler is None:
                continue
            for hex_coord in anomaly.hexes:
                system = sector.systems.get(hex_coord)
                if system is not None:
                    handler(system, anomaly)


# ------------------------------------------------------- anomaly handlers

def _strip_population(mainworld) -> None:
    """Empties a world of people, and of everything that depends on them."""
    uwp = mainworld.uwp
    uwp.population = '0'
    uwp.government = '0'
    uwp.law_level = '0'
    uwp.tech_level = '0'
    uwp.starport = 'X'
    mainworld.population_digit = 0
    mainworld.total_population = 0
    mainworld.trade_codes = [c for c in mainworld.trade_codes
                             if c not in ('Hi', 'Ph', 'Ag', 'In', 'Ri', 'Na',
                                          'Pi', 'Pa', 'Px', 'Ph')]
    if 'Ba' not in mainworld.trade_codes:
        mainworld.trade_codes.append('Ba')


def _apply_barren(system, anomaly: Anomaly) -> None:
    """Failed colonies: the world is barren and the starport gone."""
    mainworld = system.mainworld
    if mainworld is None:
        return
    _strip_population(mainworld)
    system.bases = []
    system.allegiance = 'Na'
    mainworld.notes.append(f"{anomaly.name}: colony failed, world abandoned")


def _apply_supernova(system, anomaly: Anomaly) -> None:
    """A sterilising blast: no life, a stripped atmosphere and hydrographics,
    and a lasting radioactive taint."""
    mainworld = system.mainworld
    if mainworld is None:
        return
    _strip_population(mainworld)
    atmosphere = Utils.from_eHex(mainworld.uwp.atmosphere)
    hydrographics = Utils.from_eHex(mainworld.uwp.hydrographics)
    mainworld.uwp.atmosphere = Utils.eHex(max(0, atmosphere - Utils.D3()))
    mainworld.uwp.hydrographics = Utils.eHex(max(0, hydrographics - Utils.D3()))
    mainworld.atmosphere_code = mainworld.uwp.atmosphere
    mainworld.hydrographics_code = mainworld.uwp.hydrographics
    mainworld.biomass_rating = 0
    mainworld.biocomplexity_rating = 0
    mainworld.life_details = "Sterilised: no surviving native life"
    mainworld.atmosphere_taint = {'type': 'Radioactive Particulates',
                                  'severity': 'Extreme',
                                  'persistence': 'Planet-wide'}
    system.travel_zone = 'R'
    mainworld.notes.append(f"{anomaly.name}: sterilised by supernova")


def _apply_ruins(system, anomaly: Anomaly) -> None:
    """Ancient ruins: the world carries relics, and often an interdiction."""
    mainworld = system.mainworld
    if mainworld is None:
        return
    mainworld.notes.append(f"{anomaly.name}: ancient ruins on the surface")
    if 'An' not in mainworld.trade_codes:
        mainworld.trade_codes.append('An')
    if Utils.D6(2) >= 10:
        system.travel_zone = 'R'
        mainworld.notes.append("Interdicted: ruins under study")


def _apply_hazardous_jump(system, anomaly: Anomaly) -> None:
    """Treacherous jump space keeps traffic away."""
    mainworld = system.mainworld
    if mainworld is None:
        return
    if not system.travel_zone:
        system.travel_zone = 'A'
    mainworld.notes.append(f"{anomaly.name}: jump space unreliable; "
                           f"ships have been lost here")


def _apply_plague(system, anomaly: Anomaly) -> None:
    """Disease: an interdiction, and a population that never recovered."""
    mainworld = system.mainworld
    if mainworld is None:
        return
    system.travel_zone = 'R' if Utils.D6(2) >= 8 else 'A'
    population = Utils.from_eHex(mainworld.uwp.population)
    if population > 0:
        mainworld.uwp.population = Utils.eHex(max(0, population - Utils.D3()))
    mainworld.notes.append(f"{anomaly.name}: deadly disease present")


def _apply_tech_inhibitor(system, anomaly: Anomaly) -> None:
    """Technology fails here, stranding the world at a low Tech Level."""
    mainworld = system.mainworld
    if mainworld is None:
        return
    tech_level = Utils.from_eHex(mainworld.uwp.tech_level)
    capped = min(tech_level, Utils.D3() + 2)
    mainworld.uwp.tech_level = Utils.eHex(capped)
    if mainworld.uwp.starport in ('A', 'B', 'C'):
        mainworld.uwp.starport = 'E'
    mainworld.notes.append(f"{anomaly.name}: technology fails above TL{capped}")


def _apply_warfare(system, anomaly: Anomaly) -> None:
    """Unrestricted warfare: wrecked starports and a tainted atmosphere."""
    mainworld = system.mainworld
    if mainworld is None:
        return
    downgrade = {'A': 'C', 'B': 'C', 'C': 'D', 'D': 'E', 'E': 'X'}
    mainworld.uwp.starport = downgrade.get(mainworld.uwp.starport,
                                           mainworld.uwp.starport)
    population = Utils.from_eHex(mainworld.uwp.population)
    if population > 0:
        mainworld.uwp.population = Utils.eHex(max(0, population - 1))
    atmosphere = Utils.from_eHex(mainworld.uwp.atmosphere)
    if atmosphere in (6, 8):     # a clean atmosphere becomes tainted
        mainworld.uwp.atmosphere = Utils.eHex(atmosphere + 1)
        mainworld.atmosphere_code = mainworld.uwp.atmosphere
    mainworld.atmosphere_taint = {'type': 'Radioactive Particulates',
                                  'severity': 'Moderate',
                                  'persistence': 'Regional'}
    if not system.travel_zone:
        system.travel_zone = 'A'
    mainworld.notes.append(f"{anomaly.name}: infrastructure wrecked by war")


_ANOMALY_HANDLERS = {
    'barren': _apply_barren,
    'supernova': _apply_supernova,
    'ruins': _apply_ruins,
    'hazardous_jump': _apply_hazardous_jump,
    'plague': _apply_plague,
    'tech_inhibitor': _apply_tech_inhibitor,
    'warfare': _apply_warfare,
    # 'rift' and 'cluster' act during generation, via density_target_for
}


# --------------------------------------------------------------- presets

# Ready-made sketches, each a set of answers to the book's questions.
UNIVERSE_PRESETS = {
    'charted_space': dict(
        theme='frontier', density='standard', technology='imperial',
        trajectory='stasis', sophont_prevalence='standard', polity_count=3,
        background="A long-established interstellar order, with a great "
                   "empire's border running through the region and "
                   "independent worlds beyond it."),
    'frontier': dict(
        theme='frontier', density='scattered', technology='developing',
        trajectory='expansion', sophont_prevalence='standard', polity_count=2,
        background="Newly opened space. Settlement waves are still moving "
                   "outward and few worlds have been charted twice."),
    'pocket_empires': dict(
        theme='colonial', density='dense', technology='developing',
        trajectory='expansion', sophont_prevalence='rare', polity_count=5,
        background="No single power dominates. Several small states, each "
                   "a few parsecs across, compete for the same worlds."),
    'fallen_empire': dict(
        theme='decline', density='standard', technology='early',
        trajectory='collapse', sophont_prevalence='rare', polity_count=1,
        background="An empire has fallen. Its worlds have lost starflight "
                   "and its successor holds only a fraction of the old "
                   "territory."),
    'deep_rift': dict(
        theme='isolation', density='sparse', technology='imperial',
        trajectory='stasis', sophont_prevalence='rare', polity_count=1,
        background="A near-empty stretch of space. Crossing it takes "
                   "deep-space refuelling and careful astrogation."),
}


def create_universe(name: str = "Generated Universe", preset: str = None,
                    **overrides) -> Universe:
    """The guided entry point (SCG pp.3-8).

    Start from a preset or from the defaults, then override any of the
    high-level choices: theme, density, technology, trajectory,
    sophont_prevalence, polity_count, current_year and background."""
    settings = {}
    if preset is not None:
        if preset not in UNIVERSE_PRESETS:
            raise ValueError(f"unknown preset {preset!r}; "
                             f"expected one of {sorted(UNIVERSE_PRESETS)}")
        settings.update(UNIVERSE_PRESETS[preset])
    settings.update(overrides)

    for key, table in (('density', DENSITY_TARGETS),
                       ('technology', TECHNOLOGY_LEVELS),
                       ('trajectory', TRAJECTORIES),
                       ('sophont_prevalence', SOPHONT_PREVALENCE)):
        value = settings.get(key)
        if value is not None and value not in table:
            raise ValueError(f"unknown {key} {value!r}; "
                             f"expected one of {sorted(table)}")

    return Universe(name=name, **settings)


def build_default_timeline(universe: Universe) -> List[TimelineEvent]:
    """A rough timeline for the universe (SCG p.5), scaled to its
    trajectory: how long ago people arrived, when the current order was
    established, and what has happened lately."""
    now = universe.current_year
    universe.timeline = []

    if universe.sophont_prevalence != 'none':
        universe.add_event(now - 300000,
                           "Ancient civilisation active in the region; "
                           "sophonts transplanted between worlds")

    arrival = {'expansion': 800, 'stasis': 4000, 'decline': 3000,
               'collapse': 3000, 'recovery': 2500}[universe.trajectory]
    universe.add_event(now - arrival, "First interstellar arrivals in the region")
    universe.add_event(now - arrival // 2, "Widespread settlement begins")

    if universe.trajectory == 'expansion':
        universe.add_event(now - 200, "The current wave of expansion begins")
        universe.add_event(now - 40, "Frontier surveys reach the far side of the region")
    elif universe.trajectory == 'stasis':
        universe.add_event(now - 1000, "Borders stabilise where they still stand")
        universe.add_event(now - 100, "The last border war ends inconclusively")
    elif universe.trajectory == 'decline':
        universe.add_event(now - 400, "The high point of the old order")
        universe.add_event(now - 150, "Outer worlds begin losing contact")
    elif universe.trajectory == 'collapse':
        universe.add_event(now - 500, "The empire reaches its greatest extent")
        universe.add_event(now - 250, "Central authority fails; starflight is lost on many worlds")
    elif universe.trajectory == 'recovery':
        universe.add_event(now - 600, "The long night begins")
        universe.add_event(now - 120, "Jump drive is rediscovered and contact resumes")

    for anomaly in universe.anomalies:
        if anomaly.kind == 'supernova':
            universe.add_event(now - Utils.D6(2) * 100,
                               f"{anomaly.name}: the star goes supernova")
        elif anomaly.kind == 'barren':
            universe.add_event(now - Utils.D6() * 50,
                               f"{anomaly.name}: the last colony attempt fails")
        elif anomaly.kind == 'plague':
            universe.add_event(now - Utils.D6() * 30,
                               f"{anomaly.name}: the outbreak begins")

    return universe.timeline


def generate_universe_sector(universe: Universe, name: str = None,
                             width: int = 32, height: int = 40) -> Sector:
    """Generates a sector under a universe's settings, applying its density,
    Tech Level ceiling, sophont prevalence, polity count and anomalies."""
    from .sector import generate_full_sector

    return generate_full_sector(name=name or universe.name, width=width,
                                height=height,
                                density_target=universe.density_target,
                                universe=universe)
