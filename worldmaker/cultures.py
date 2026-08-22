"""Cultural character for nations and worlds.

Two ways to give a society a character, and the default is deliberately the
plain one.

**Procedural** (the default). The *World Builder's Handbook*'s eight cultural
traits, rolled from the society's own government, law, technology and
population. Nothing is imported from Earth: what comes out is a set of
numbers a Referee reads and interprets. This is the honest default, because
a galactic society spanning thousands of worlds and tens of thousands of
years is not well served by being sorted into terrestrial pigeonholes.

**Templates** (opt-in). A palette of ready-made cultural characters for when
a Referee wants a society that already reads as a place. The palette leans
deliberately away from Earth: terrestrial historical periods are one family
among several, alongside the social forms that only a starfaring or wholly
alien setting produces - hive collectives, distributed minds, nomad fleets,
clade lineages, worlds where the dead remain legal persons.

Templates set the eight traits, and suggest the government codes, Law Levels
and Tech Levels that suit them; the values are centres, jittered per nation,
so two states on the same template are still different places.
"""
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .classes import CulturalProfile
from .utils import Utils

# The handbook's eight cultural traits, in profile order.
TRAIT_KEYS = ('diversity', 'xenophilia', 'uniqueness', 'symbology',
              'cohesion', 'progressiveness', 'expansionism', 'militancy')

TRAIT_LABELS = {
    'diversity': "how varied the population is",
    'xenophilia': "openness to outsiders",
    'uniqueness': "how unlike its neighbours the culture is",
    'symbology': "weight given to symbol and ritual",
    'cohesion': "social unity",
    'progressiveness': "appetite for change",
    'expansionism': "outward drive",
    'militancy': "readiness to use force",
}

# Template families. 'terrestrial' is one option among many by design.
FAMILIES = {
    'terrestrial': "Analogues of Earth's own historical periods",
    'starfaring': "Societies shaped by interstellar settlement",
    'exotic': "Social forms with no terrestrial parallel",
}


@dataclass
class CultureTemplate:
    """A ready-made cultural character."""
    key: str
    name: str
    family: str
    description: str
    traits: Dict[str, int] = field(default_factory=dict)
    tech_level: Tuple[int, int] = (0, 15)
    law_level: Tuple[int, int] = (0, 15)
    governments: Tuple[int, ...] = ()

    def suits(self, tech_level: int) -> bool:
        low, high = self.tech_level
        return low <= tech_level <= high


def _t(div, xen, uni, sym, coh, pro, exp, mil) -> Dict[str, int]:
    """Shorthand for the eight traits, in profile order."""
    return dict(zip(TRAIT_KEYS, (div, xen, uni, sym, coh, pro, exp, mil)))


# --------------------------------------------------------------- the palette

_TEMPLATES: List[CultureTemplate] = [

    # ---------------------------------------------------- terrestrial
    CultureTemplate(
        'neolithic', "Neolithic Villages", 'terrestrial',
        "Settled farming hamlets, kin-reckoned, the year measured by "
        "planting and harvest.",
        _t(3, 5, 9, 9, 10, 3, 3, 4), (0, 1), (0, 3), (0,)),
    CultureTemplate(
        'bronze_age', "Bronze Age Palace States", 'terrestrial',
        "Temple granaries, scribes, god-kings and the first standing "
        "armies.",
        _t(4, 4, 9, 12, 9, 3, 7, 8), (1, 2), (3, 8), (10, 14)),
    CultureTemplate(
        'classical', "Classical City-States", 'terrestrial',
        "Rival cities, civic religion, philosophy argued in public and "
        "an economy resting on the unfree.",
        _t(6, 6, 8, 10, 6, 6, 8, 8), (1, 3), (2, 7), (2, 4, 7)),
    CultureTemplate(
        'dark_age', "Early Medieval Kingdoms", 'terrestrial',
        "Petty kings, monastery libraries and a scholarship kept alive by "
        "a handful of hands.",
        _t(4, 3, 9, 12, 6, 3, 5, 9), (1, 2), (2, 7), (5, 14)),
    CultureTemplate(
        'norse', "Seafaring Raiders", 'terrestrial',
        "Longships, assemblies of free men, feud and far-ranging trade in "
        "the same hulls.",
        _t(4, 5, 11, 10, 8, 5, 11, 11), (1, 2), (1, 5), (0, 4, 14)),
    CultureTemplate(
        'celtic', "Clan Hill-Peoples", 'terrestrial',
        "Cattle-wealth, fostering and oral law recited by trained "
        "memories.",
        _t(5, 4, 11, 11, 9, 3, 5, 9), (0, 2), (1, 5), (0, 4)),
    CultureTemplate(
        'medieval', "Feudal Kingdoms", 'terrestrial',
        "Sworn obligation from field to throne, a universal church and "
        "chartered towns beginning to buy their freedom.",
        _t(5, 4, 8, 12, 7, 4, 7, 9), (2, 3), (4, 9), (5, 14)),
    CultureTemplate(
        'renaissance', "Merchant Princes", 'terrestrial',
        "Banking houses, patronage, gunpowder and a sudden appetite for "
        "the antique.",
        _t(7, 7, 8, 10, 5, 9, 9, 8), (3, 4), (3, 8), (1, 3, 4)),
    CultureTemplate(
        'age_of_sail', "Maritime Empires", 'terrestrial',
        "Chartered companies, naval discipline and colonies administered "
        "at six months' remove.",
        _t(7, 6, 7, 9, 6, 8, 12, 10), (3, 5), (4, 9), (1, 6, 14)),
    CultureTemplate(
        'georgian', "Enlightenment Society", 'terrestrial',
        "Coffee houses, correspondence, subscription libraries and a "
        "confident faith in improvement.",
        _t(6, 7, 7, 8, 6, 10, 8, 6), (3, 5), (2, 6), (2, 4, 14)),
    CultureTemplate(
        'regency', "Landed Gentry", 'terrestrial',
        "Estates and entail, the season, propriety as an instrument of "
        "power, and a great deal turning on an income.",
        _t(4, 5, 8, 11, 8, 5, 5, 5), (3, 5), (3, 7), (4, 14)),
    CultureTemplate(
        'victorian', "Industrial Imperium", 'terrestrial',
        "Mills and railways, reform societies and an empire administered "
        "by examination.",
        _t(7, 5, 7, 10, 7, 10, 12, 9), (4, 6), (4, 9), (4, 8, 14)),
    CultureTemplate(
        'belle_epoque', "Late Industrial Cities", 'terrestrial',
        "Trams and gaslight, newspapers and nationalism, a literature of "
        "ordinary days in a city that knows itself.",
        _t(8, 7, 8, 9, 5, 10, 8, 8), (5, 6), (2, 6), (2, 4, 7)),
    CultureTemplate(
        'interwar', "Ideological Decades", 'terrestrial',
        "Radio and cinema, mass parties, and a peace nobody quite "
        "believes in.",
        _t(8, 5, 7, 10, 4, 9, 9, 11), (5, 7), (3, 9), (7, 10, 12)),
    CultureTemplate(
        'atomic_age', "Superpower Era", 'terrestrial',
        "Mass media, suburbs, a space programme and a rivalry conducted "
        "everywhere but directly.",
        _t(8, 6, 6, 8, 5, 11, 11, 10), (7, 8), (3, 8), (2, 8, 12)),
    CultureTemplate(
        'information_age', "Networked Society", 'terrestrial',
        "Global supply chains, ambient connection, and identity "
        "negotiated in public.",
        _t(11, 8, 5, 6, 3, 12, 7, 6), (8, 9), (2, 6), (2, 8, 9)),

    # ----------------------------------------------------- starfaring
    CultureTemplate(
        'frontier_colony', "Frontier Colony", 'starfaring',
        "Thin population, long distances, and a self-reliance that has "
        "hardened into a virtue.",
        _t(5, 6, 8, 6, 8, 7, 9, 8), (5, 11), (1, 5), (0, 2, 4)),
    CultureTemplate(
        'belter', "Belter Communities", 'starfaring',
        "Claims, water rights and salvage law; everything is owed to "
        "somebody and nothing is wasted.",
        _t(6, 6, 10, 5, 7, 8, 7, 7), (8, 13), (1, 5), (0, 2, 4)),
    CultureTemplate(
        'corporate_state', "Company World", 'starfaring',
        "Employment is citizenship, the contract is the constitution, and "
        "the quarterly figures are read like scripture.",
        _t(6, 5, 6, 7, 9, 9, 9, 6), (8, 15), (5, 11), (1,)),
    CultureTemplate(
        'imperial_client', "Client Aristocracy", 'starfaring',
        "Titles confirmed by a throne many parsecs away, and a local "
        "nobility that takes them very seriously indeed.",
        _t(6, 6, 6, 11, 8, 5, 7, 8), (7, 14), (4, 9), (6, 14)),
    CultureTemplate(
        'free_trader', "Port Culture", 'starfaring',
        "Everyone is from somewhere else, credit is character, and the "
        "docks never quite close.",
        _t(12, 11, 6, 5, 3, 9, 8, 5), (7, 14), (1, 5), (2, 4, 7)),
    CultureTemplate(
        'naval_garrison', "Service World", 'starfaring',
        "Rank, watch-bills and a civilian life organised around the base "
        "gate.",
        _t(5, 5, 6, 10, 11, 6, 8, 12), (9, 15), (6, 12), (11, 12, 13)),
    CultureTemplate(
        'terraform_project', "Terraforming Generations", 'starfaring',
        "A society organised around a task no living member will see "
        "finished.",
        _t(5, 5, 9, 9, 12, 8, 4, 4), (9, 15), (4, 9), (8, 9)),
    CultureTemplate(
        'lost_colony', "Lost Colony", 'starfaring',
        "Cut off long enough that the founding is myth and the machines "
        "in the old hall are relics.",
        _t(4, 3, 13, 12, 9, 3, 3, 7), (0, 6), (2, 8), (0, 5, 10, 14)),
    CultureTemplate(
        'generation_ship', "Shipborn Landfall", 'starfaring',
        "Descendants of a slower-than-light crossing, keeping watches and "
        "rationing habits a planet no longer requires.",
        _t(4, 4, 12, 11, 12, 5, 4, 5), (7, 13), (5, 11), (8, 9, 13)),
    CultureTemplate(
        'penal_colony', "Transported Descent", 'starfaring',
        "Founded as a punishment, grown into a country, and touchy about "
        "both.",
        _t(7, 4, 9, 8, 6, 6, 6, 10), (5, 12), (6, 13), (3, 6, 11)),
    CultureTemplate(
        'refugee_landfall', "Refugee Landfall", 'starfaring',
        "A people who arrived with what they could carry, and who keep "
        "the memory deliberately.",
        _t(6, 4, 11, 13, 11, 5, 4, 8), (5, 12), (3, 9), (4, 8, 13)),

    # --------------------------------------------------------- exotic
    CultureTemplate(
        'hive_collective', "Hive Collective", 'exotic',
        "Individual preference is not suppressed so much as unintelligible; "
        "the colony is the person.",
        _t(2, 2, 15, 8, 15, 4, 9, 9), (3, 15), (7, 15), (9, 13)),
    CultureTemplate(
        'distributed_mind', "Distributed Minds", 'exotic',
        "One consciousness across many bodies, and conversation between "
        "two people is an internal matter.",
        _t(3, 5, 15, 7, 14, 8, 6, 5), (11, 17), (4, 10), (8, 9, 13)),
    CultureTemplate(
        'machine_symbiosis', "Symbiotic Polity", 'exotic',
        "Sophonts and their machines are a single political body, and "
        "asking which governs is thought a rude question.",
        _t(7, 6, 14, 6, 11, 12, 6, 5), (12, 17), (3, 9), (8, 9)),
    CultureTemplate(
        'uplift_society', "Newly Uplifted", 'exotic',
        "A species given sapience within living memory, still deciding "
        "what it wants to be and resenting being asked.",
        _t(8, 5, 13, 9, 6, 11, 7, 9), (7, 14), (4, 10), (3, 6, 7)),
    CultureTemplate(
        'psionic_theocracy', "Psionic Hierarchy", 'exotic',
        "Those who read minds hold office by right, and privacy is a "
        "concept requiring translation.",
        _t(4, 4, 13, 13, 13, 6, 9, 7), (9, 16), (7, 14), (5, 13)),
    CultureTemplate(
        'gerontocracy_of_ages', "Gerontocracy of Ages", 'exotic',
        "Lifespans measured in centuries, politics conducted at the pace "
        "of geology, and the young are four hundred.",
        _t(4, 4, 12, 11, 12, 2, 3, 4), (12, 17), (5, 11), (3, 5, 8)),
    CultureTemplate(
        'seasonal_polymorphs', "Seasonal Polymorphs", 'exotic',
        "The population changes physical form with the year, and the "
        "constitution changes with it.",
        _t(9, 5, 15, 12, 8, 6, 5, 6), (2, 13), (2, 9), (0, 4, 7)),
    CultureTemplate(
        'tidal_twilight', "Twilight Band", 'exotic',
        "Everything lives in the narrow ring between a burning day side "
        "and a frozen night, and everything is long and thin.",
        _t(6, 5, 13, 9, 10, 7, 4, 7), (6, 15), (4, 10), (4, 8, 13)),
    CultureTemplate(
        'aquatic_shoal', "Shoal Society", 'exotic',
        "Group identity is fluid and literal; a crowd becomes a decision "
        "without anyone proposing one.",
        _t(6, 6, 14, 8, 12, 6, 5, 6), (3, 13), (2, 8), (2, 4, 7)),
    CultureTemplate(
        'low_gravity_arboreal', "Canopy Dwellers", 'exotic',
        "Settlement in three dimensions, where 'down' is a direction "
        "rather than a place.",
        _t(7, 7, 12, 8, 7, 8, 6, 5), (2, 13), (1, 6), (0, 2, 4)),
    CultureTemplate(
        'high_gravity_stoic', "Deep-Weight Peoples", 'exotic',
        "A world that punishes haste, and a people who have made "
        "deliberation a moral quality.",
        _t(4, 4, 11, 10, 12, 4, 4, 8), (4, 14), (5, 11), (5, 8, 14)),
    CultureTemplate(
        'clade_lineage', "Clade Lineages", 'exotic',
        "Genetic lines are the political units; citizenship is ancestry "
        "and marriage is treaty.",
        _t(5, 3, 13, 12, 10, 5, 7, 9), (8, 16), (6, 12), (0, 5, 14)),
    CultureTemplate(
        'memory_guild', "Rememberers", 'exotic',
        "Writing is distrusted; the past is held by trained specialists "
        "and recited, and to alter a record you must persuade a person.",
        _t(5, 4, 14, 14, 11, 3, 4, 6), (1, 10), (4, 10), (4, 5, 13)),
    CultureTemplate(
        'ritual_exchange', "Obligation Economies", 'exotic',
        "Status comes from what you have given away, and debt is the "
        "fabric holding society together.",
        _t(7, 8, 13, 13, 9, 5, 6, 5), (1, 12), (2, 7), (0, 2, 4)),
    CultureTemplate(
        'nomad_fleet', "Nomad Fleet", 'exotic',
        "No homeworld; the fleet is the nation, and a planet is a place "
        "you visit for water.",
        _t(7, 6, 13, 11, 12, 7, 10, 9), (10, 16), (5, 11), (4, 8, 14)),
    CultureTemplate(
        'arcology_stacks', "Stack Society", 'exotic',
        "A vertical city where the level you were born on is the single "
        "most important fact about you.",
        _t(10, 5, 9, 8, 5, 8, 4, 8), (9, 16), (6, 13), (9, 10, 12)),
    CultureTemplate(
        'contemplative_order', "Contemplative Orders", 'exotic',
        "A world given over to withdrawal, scholarship and long silence, "
        "which receives visitors politely and briefly.",
        _t(3, 5, 13, 14, 12, 4, 2, 2), (3, 15), (3, 9), (5, 13)),
    CultureTemplate(
        'warrior_honour', "Honour Cultures", 'exotic',
        "Standing is held against all comers, insults are technical "
        "matters, and land changes hands by challenge.",
        _t(5, 4, 12, 13, 9, 4, 11, 13), (5, 15), (4, 10), (10, 14)),
    CultureTemplate(
        'dietary_absolutist', "Dietary Absolutists", 'exotic',
        "What may be eaten is the foundation of law, cosmology and "
        "foreign policy, in that order.",
        _t(3, 2, 14, 14, 13, 3, 10, 12), (5, 15), (8, 15), (5, 13)),
    CultureTemplate(
        'pack_charisma', "Charismatic Packs", 'exotic',
        "Authority is personal and provisional; a leader holds a following "
        "exactly as long as the following is impressed.",
        _t(9, 7, 12, 8, 4, 9, 11, 10), (7, 15), (1, 6), (0, 3, 7)),
    CultureTemplate(
        'manipulator_consensus', "Indirect Governance", 'exotic',
        "Nobody appears to be in charge, decisions arrive fully formed, "
        "and everyone insists it was their own idea.",
        _t(8, 9, 14, 6, 10, 10, 8, 4), (11, 17), (2, 7), (8, 9)),
    CultureTemplate(
        'ancestor_continuity', "The Standing Dead", 'exotic',
        "The dead retain legal personality; estates are never settled and "
        "the electorate only grows.",
        _t(4, 3, 15, 14, 12, 2, 3, 6), (6, 16), (6, 12), (3, 5, 13)),
    CultureTemplate(
        'dreaming_polity', "The Dreaming", 'exotic',
        "Policy is arrived at in a shared unconsciousness, and waking "
        "government exists to carry it out.",
        _t(5, 5, 15, 13, 13, 5, 4, 4), (8, 17), (4, 10), (8, 13)),
]

CULTURE_TEMPLATES: Dict[str, CultureTemplate] = {t.key: t for t in _TEMPLATES}


def templates_in_family(family: str) -> List[CultureTemplate]:
    return [t for t in _TEMPLATES if t.family == family]


def templates_for_tech_level(tech_level: int,
                             family: str = None) -> List[CultureTemplate]:
    """Templates that suit a given Tech Level, optionally within a family."""
    return [t for t in _TEMPLATES
            if t.suits(tech_level) and (family is None or t.family == family)]


def describe_palette() -> str:
    """The palette, grouped by family."""
    lines = []
    for family, blurb in FAMILIES.items():
        members = templates_in_family(family)
        lines.append(f"{family} - {blurb} ({len(members)})")
        for template in members:
            low, high = template.tech_level
            lines.append(f"  {template.key:24s} {template.name:26s} "
                         f"TL{low}-{high}")
        lines.append("")
    return "\n".join(lines).rstrip()


# ------------------------------------------------------------- generation

def _jitter(centre: int, spread: int = 2) -> int:
    """A trait value near its centre. Cultures of a kind still differ."""
    return max(1, min(15, centre + random.randint(-spread, spread)))


def culture_from_template(template: Any, spread: int = 2) -> CulturalProfile:
    """A cultural profile drawn from a template, jittered so two societies
    on the same template are still different places."""
    if isinstance(template, str):
        template = CULTURE_TEMPLATES[template]
    return CulturalProfile(**{key: _jitter(template.traits.get(key, 7), spread)
                              for key in TRAIT_KEYS})


def culture_for_template(key: str, nation: Any = None,
                         spread: int = 2) -> CulturalProfile:
    """The culture a named template produces. Raises on an unknown key so a
    typo fails loudly rather than silently generating something else."""
    if key not in CULTURE_TEMPLATES:
        raise ValueError(
            f"unknown culture template {key!r}. "
            f"Known templates: {', '.join(sorted(CULTURE_TEMPLATES))}")
    return culture_from_template(CULTURE_TEMPLATES[key], spread)


def procedural_culture(nation: Any, world: Any = None) -> CulturalProfile:
    """The default: the handbook's eight traits rolled from the society's
    own government, law, technology and population - no analogue applied."""
    from .classes import UWP
    from .society import generate_cultural_profile

    population = getattr(world, 'uwp', None)
    population_code = (population.population if population is not None
                       else Utils.eHex(6))

    stand_in = UWP(
        starport=getattr(getattr(world, 'uwp', None), 'starport', 'C') or 'C',
        population=population_code,
        government=Utils.eHex(getattr(nation, 'government_code', 0) or 0),
        law_level=Utils.eHex(getattr(nation, 'law_level', 0) or 0),
        tech_level=Utils.eHex(getattr(nation, 'tech_level', 0) or 0),
    )
    return generate_cultural_profile(stand_in)


def suggest_template(nation: Any, family: str = None,
                     tech_level: int = None) -> Optional[CultureTemplate]:
    """A template that would suit a nation's government and Tech Level.

    Useful when applying the palette to a world wholesale: each nation gets
    something that fits what it already is."""
    tech_level = (tech_level if tech_level is not None
                  else getattr(nation, 'tech_level', 5))
    government = getattr(nation, 'government_code', None)

    candidates = templates_for_tech_level(tech_level, family)
    if not candidates:
        candidates = templates_in_family(family) if family else list(_TEMPLATES)
    if not candidates:
        return None

    preferred = [t for t in candidates
                 if government is not None and government in t.governments]
    return random.choice(preferred or candidates)


def apply_template_palette(world: Any, family: str = None,
                           template: str = None) -> List[str]:
    """Gives every nation on a world a template-drawn culture.

    Pass `template` to put all of them on one, or `family` to draw each from
    a family that suits its Tech Level and government. Returns the template
    key used for each nation, in order."""
    nations = getattr(world, 'nations', None) or []
    applied = []
    for nation in nations:
        if template:
            chosen = CULTURE_TEMPLATES[template]
        else:
            chosen = suggest_template(nation, family)
        if chosen is None:
            applied.append("")
            continue
        nation.culture = culture_from_template(chosen)
        nation.culture_template = chosen.key
        nation.notes.append(f"Culture: {chosen.name} - {chosen.description}")
        applied.append(chosen.key)
    return applied


def culture_profile_string(culture: CulturalProfile) -> str:
    """The eight traits as the handbook prints them: two groups of four."""
    if culture is None:
        return ""
    values = [Utils.eHex(getattr(culture, key, 0)) for key in TRAIT_KEYS]
    return "".join(values[:4]) + "-" + "".join(values[4:])
