"""Sophont design (SCG pp.50-60).

Minor races are generated from the Sophont Physical Characteristics table, a
D66 table whose 36 outcomes fall into six categories keyed by the first die:
symmetry, limb count, manipulator type, environment, behaviour and gender.
Major races of Charted Space are catalogued rather than rolled.
"""
import random
from typing import Any, Dict, List

from .classes import Sophont, CulturalProfile
from .utils import Utils

# Sophont Physical Characteristics (SCG pp.52-54), the full D66 table.
SYMMETRY = {
    1: ("Amorphous", "no defined shape, or able to transform it"),
    2: ("Asymmetrical", "no symmetry, or symmetry broken between sides"),
    3: ("Bilateral", "two sides, one mirroring the other"),
    4: ("Spherical", "limbs protruding symmetrically in three dimensions"),
    5: ("Radial", "four or more degrees of symmetry about a central axis"),
    6: ("Trilateral", "a threefold axis of symmetry"),
}

LIMBS = {
    1: ("Bipod", "two limbs, or one per degree of symmetry"),
    2: ("Hexapod", "six limbs, or three per degree of symmetry"),
    3: ("Decapod", "ten limbs, or five per degree of symmetry"),
    4: ("Many-limbed", "six or more limbs per degree of symmetry"),
    5: ("Octopod", "eight limbs, or four per degree of symmetry"),
    6: ("Tetrapod", "four limbs, or two per degree of symmetry"),
}

MANIPULATORS = {
    1: ("Grasper", "three or more mutually opposed digits that clamp"),
    2: ("Gripper", "two opposed flaps or digits that clamp"),
    3: ("Hand", "two groups of opposed digits that hold"),
    4: ("Paw", "multiple unopposed digits that hold"),
    5: ("Socket", "hollows or suckers that hold"),
    6: ("Tentacle", "flexible digits that entwine or coil"),
}

ENVIRONMENT = {
    1: ("Amphibian", "survives in both gaseous and liquid environments"),
    2: ("Aquatic", "evolved for a primarily liquid environment"),
    3: ("Floating", "floats in air or on liquid through buoyancy"),
    4: ("Flying", "actively flies or glides"),
    5: ("Subterranean", "lives beneath the surface, burrowing"),
    6: ("Triphibian", "survives in air, on the surface and in liquid"),
}

BEHAVIOUR = {
    1: ("Carnivore", "subsists by hunting motile prey"),
    2: ("Herbivore", "subsists on immotile food"),
    3: ("Immobile", "immobile or extremely slow; autotroph or filter-feeder"),
    4: ("Omnivore", "a generalist, eating motile and immotile food alike"),
    5: ("Parasite", "nourished through a parasitic or mutualistic bond"),
    6: ("Scavenger", "harvests food from lifeforms it did not kill"),
}

GENDER = {
    1: ("Asexual", "reproduces by budding, cloning or splitting"),
    2: ("Extreme gender dimorphism", "genders differ enormously in size or plan"),
    3: ("Hermaphrodite", "individuals are serially or simultaneously multi-gendered"),
    4: ("Metamorphic life cycle", "multiple stages separated by metamorphosis"),
    5: ("Multiple sexes", "three or more genders are needed to reproduce"),
    6: ("Non-intelligent gender", "one or more genders are not sophont"),
}

_CATEGORIES = [
    ('symmetry', SYMMETRY),
    ('limbs', LIMBS),
    ('manipulators', MANIPULATORS),
    ('environment', ENVIRONMENT),
    ('behaviour', BEHAVIOUR),
    ('gender', GENDER),
]

# Sensory organs are not a D66 category in the guide; these follow the
# environment a species evolved in.
_SENSES_BY_ENVIRONMENT = {
    'Aquatic': ["Pressure-sensitive lateral line", "Sonar echo-location",
                "Electroreception", "Low-light vision"],
    'Amphibian': ["Wide-spectrum vision", "Pressure sense", "Chemical taste-feelers"],
    'Triphibian': ["Wide-spectrum vision", "Pressure sense", "Acute hearing"],
    'Flying': ["Acute distance vision", "Magnetic field sense", "Air-pressure organs"],
    'Floating': ["Barometric pressure organs", "Wide-angle vision"],
    'Subterranean': ["Infrared thermal pits", "Vibration sense", "Acute olfaction"],
}
_DEFAULT_SENSES = ["Standard vision and hearing", "Acute olfaction",
                   "Ultraviolet vision", "Infrared thermal pits",
                   "Chemical taste-feelers"]

_PREFIXES = ["Chil", "Dra", "Eld", "Flax", "Grom", "Hyth", "Isk", "Kro", "Lur",
             "Mrax", "Nax", "Oph", "Pru", "Qur", "Scy", "Tla", "Urr", "Vux",
             "Zad", "Bel", "Cyr", "Dho", "Esh", "Gith", "Jal", "Khe", "Mor"]
_SUFFIXES = ["ian", "ax", "oid", "ite", "on", "ar", "i", "eth", "ur", "ka",
             "esh", "ai", "ori", "un"]


# Classic Traveller Major Races catalogue
MAJOR_RACES = {
    "Aslan": {
        "symmetry": "Bilateral", "limbs": "Tetrapod",
        "manipulators": "Hand (retractile claws)",
        "environment": "Subterranean-descended plains dweller",
        "behaviour": "Carnivore", "gender": "Extreme gender dimorphism",
        "morphology": "Bilateral (feline analogues)",
        "sensory_organs": ["Low-light vision", "Acute hearing"],
        "psychology": "High honour, territorial clan grouping",
        "evolutionary_track": "Forest and plains predators",
        "history_summary": "Expansive spacefaring hierate ruled by clan structure.",
    },
    "Zhodani": {
        "symmetry": "Bilateral", "limbs": "Tetrapod", "manipulators": "Hand",
        "environment": "Amphibian-descended plains dweller",
        "behaviour": "Omnivore", "gender": "Multiple sexes",
        "morphology": "Bilateral (Humaniti)",
        "sensory_organs": ["Standard human senses", "Psionic sensitivity"],
        "psychology": "Cohesive, caste-oriented, psionically cooperative",
        "evolutionary_track": "Temperate plains",
        "history_summary": "Long-standing consulate ruled by psionic noble castes.",
    },
    "Vargr": {
        "symmetry": "Bilateral", "limbs": "Tetrapod", "manipulators": "Paw",
        "environment": "Subterranean-descended plains dweller",
        "behaviour": "Carnivore", "gender": "Extreme gender dimorphism",
        "morphology": "Bilateral (canine analogues)",
        "sensory_organs": ["Olfactory dominant", "Low-light vision"],
        "psychology": "Charisma-driven, decentralised, authority-shifting packs",
        "evolutionary_track": "Plains hunter",
        "history_summary": "Fragmented polities spanning the Vargr Extents.",
    },
    "Imperial Human": {
        "symmetry": "Bilateral", "limbs": "Tetrapod", "manipulators": "Hand",
        "environment": "Amphibian-descended savannah dweller",
        "behaviour": "Omnivore", "gender": "Multiple sexes",
        "morphology": "Bilateral (Vilani/Solomani)",
        "sensory_organs": ["Standard senses"],
        "psychology": "Individualistic, highly adaptable",
        "evolutionary_track": "Grassland and savannah",
        "history_summary": "Part of the feudal structure of the Third Imperium.",
    },
    "Droyne": {
        "symmetry": "Bilateral", "limbs": "Hexapod", "manipulators": "Hand",
        "environment": "Flying", "behaviour": "Omnivore",
        "gender": "Non-intelligent gender",
        "morphology": "Bilateral, six-limbed, winged",
        "sensory_organs": ["Standard vision and hearing",
                           "Wide-angle compound-assisted vision"],
        "psychology": "Caste-bound; the Ritual of Caste assigns each adult a role",
        "evolutionary_track": "Arid uplands, gliding between thermals",
        "history_summary": ("Scattered across Charted Space by the Ancients, "
                            "surviving in isolated coyns of a few thousand."),
    },
}

# Species this package can place from a published source but which are not
# Major Races. Chirpers are the Droyne's non-sophont kin; Solomani and the
# Minor Human Races are Humaniti transplanted by the Ancients or stranded by
# a fallen empire.
CATALOGUED_RACES = {
    "Chirper": {
        "symmetry": "Bilateral", "limbs": "Hexapod", "manipulators": "Paw",
        "environment": "Flying", "behaviour": "Omnivore",
        "gender": "Non-intelligent gender",
        "morphology": "Bilateral, six-limbed, winged (degenerate Droyne)",
        "sensory_organs": ["Standard vision and hearing"],
        "psychology": "Pre-technological, gregarious, incurious",
        "evolutionary_track": "Arid uplands; the same stock as the Droyne",
        "history_summary": ("Droyne who lost the Ritual of Caste and with it "
                            "technological society; borderline sophont."),
    },
    "Solomani": {
        "symmetry": "Bilateral", "limbs": "Tetrapod", "manipulators": "Hand",
        "environment": "Amphibian-descended savannah dweller",
        "behaviour": "Omnivore", "gender": "Multiple sexes",
        "morphology": "Bilateral (Humaniti, Terran stock)",
        "sensory_organs": ["Standard senses"],
        "psychology": "Individualistic, factional, expansionist",
        "evolutionary_track": "Grassland and savannah",
        "history_summary": ("Humaniti of Terran origin; a lost colony this far "
                            "spinward predates the Third Imperium."),
    },
    "Minor Human": {
        "symmetry": "Bilateral", "limbs": "Tetrapod", "manipulators": "Hand",
        "environment": "Amphibian-descended savannah dweller",
        "behaviour": "Omnivore", "gender": "Multiple sexes",
        "morphology": "Bilateral (Humaniti, transplanted stock)",
        "sensory_organs": ["Standard senses"],
        "psychology": "Shaped by millennia of isolation on a single world",
        "evolutionary_track": "Terran, then whatever their new world demanded",
        "history_summary": ("One of the many human populations the Ancients "
                            "moved off Terra 300,000 years ago."),
    },
    "Tlinzha": {
        "symmetry": "Bilateral", "limbs": "Octopod", "manipulators": "Grasper",
        "environment": "Subterranean", "behaviour": "Scavenger",
        "gender": "Asexual",
        "morphology": ("Bilateral octopod: two pairs of legs amidships, arms "
                       "and sensory organs at both ends"),
        "sensory_organs": ["Infrared vision ('red head')",
                           "High-acuity visual spectrum vision ('white head')",
                           "Olfactory tonal sense"],
        "psychology": ("Tradition-bound and xenophobic; gregarious among their "
                       "own kind"),
        "evolutionary_track": ("High-gravity, dense-atmosphere world of a "
                               "flare-prone red dwarf"),
        "history_summary": ("Natives of Tlesho who reached TL2 under the "
                            "Protocols of the Consumption of Meats, then "
                            "reverse-engineered jump drive from a seized "
                            "Imperial ship. They hold four systems as the "
                            "Tlesho Union and fire on unauthorised visitors."),
    },
}


def roll_d66_characteristic(category: str = None) -> Dict[str, str]:
    """Rolls one entry on the Sophont Physical Characteristics table.

    Pass a category name to roll within it; otherwise the first die selects
    the category, as the table intends."""
    if category is None:
        first = Utils.D6()
        name, table = _CATEGORIES[first - 1]
    else:
        match = next((c for c in _CATEGORIES if c[0] == category), None)
        if match is None:
            raise ValueError(f"unknown category {category!r}")
        name, table = match

    second = Utils.D6()
    value, description = table[second]
    return {'category': name, 'value': value, 'description': description}


def generate_sophont_name(used: set = None) -> str:
    for _ in range(100):
        name = random.choice(_PREFIXES) + random.choice(_SUFFIXES)
        if used is None or name not in used:
            if used is not None:
                used.add(name)
            return name
    return random.choice(_PREFIXES) + random.choice(_SUFFIXES)


def generate_minor_race(homeworld_hex: str, name: str = "",
                        world: Any = None) -> Sophont:
    """Generates a minor sophont race by rolling once in each of the six
    categories of the Sophont Physical Characteristics table (SCG p.53)."""
    if not name:
        name = generate_sophont_name()

    rolled = {c[0]: roll_d66_characteristic(c[0]) for c in _CATEGORIES}

    symmetry = rolled['symmetry']['value']
    limbs = rolled['limbs']['value']
    manipulators = rolled['manipulators']['value']
    environment = rolled['environment']['value']
    behaviour = rolled['behaviour']['value']
    gender = rolled['gender']['value']

    senses = list(_SENSES_BY_ENVIRONMENT.get(environment, _DEFAULT_SENSES))
    random.shuffle(senses)
    senses = senses[:random.randint(1, min(3, len(senses)))]

    # Psychology follows from ecological role and social pressures
    if behaviour in ('Carnivore', 'Parasite'):
        psychology = random.choice([
            "Solitary and territorial", "Cooperative pack hunters",
            "Ambush-oriented and patient"])
    elif behaviour == 'Herbivore':
        psychology = random.choice([
            "Highly gregarious herd society", "Cautious and consensus-driven"])
    elif behaviour == 'Immobile':
        psychology = random.choice([
            "Contemplative, communicating chemically",
            "Deeply conservative, with long deliberation"])
    else:
        psychology = random.choice([
            "Inquisitive and exploration-driven",
            "Opportunistic and adaptable",
            "Decentralised and shifting alliances"])

    sophont = Sophont(
        name=name,
        homeworld_hex=homeworld_hex,
        is_major=False,
        morphology=f"{symmetry}, {limbs}",
        limbs=f"{limbs} with {manipulators.lower()} manipulators",
        sensory_organs=senses,
        reproduction=gender,
        diet=behaviour,
        psychology=psychology,
        evolutionary_track=f"{environment} ({rolled['environment']['description']})",
        history_summary=(
            f"{name} are a {symmetry.lower()} {limbs.lower()} species native "
            f"to hex {homeworld_hex}: {rolled['behaviour']['description']}, "
            f"{rolled['environment']['description']}."),
    )

    sophont.symmetry = symmetry
    sophont.limb_count = limbs
    sophont.manipulators = manipulators
    sophont.environment = environment
    sophont.behaviour = behaviour
    sophont.gender = gender
    sophont.characteristic_rolls = rolled

    # Physical characteristic DMs the guide suggests for the species
    # (SCG p.55): body plan and niche shift Strength, Dexterity and Endurance.
    dms = {'STR': 0, 'DEX': 0, 'END': 0}
    if limbs in ('Many-limbed', 'Octopod', 'Decapod'):
        dms['DEX'] += 1
    if manipulators in ('Hand', 'Grasper'):
        dms['DEX'] += 1
    elif manipulators in ('Socket', 'Paw'):
        dms['DEX'] -= 1
    if environment == 'Aquatic':
        dms['STR'] += 1
        dms['DEX'] -= 1
    elif environment == 'Flying':
        dms['STR'] -= 2
        dms['DEX'] += 2
    elif environment == 'Subterranean':
        dms['STR'] += 1
        dms['END'] += 1
    if behaviour == 'Carnivore':
        dms['STR'] += 1
    elif behaviour in ('Herbivore', 'Immobile'):
        dms['END'] += 1
    sophont.characteristic_dms = dms

    return sophont


def get_major_race(name: str, homeworld_hex: str) -> Sophont:
    """Returns a catalogued Major Race of Charted Space."""
    data = MAJOR_RACES.get(name, MAJOR_RACES["Imperial Human"])
    return _build_catalogued(name, homeworld_hex, data, is_major=True)


def get_catalogued_race(name: str, homeworld_hex: str) -> Sophont:
    """Returns any species this package catalogues, Major Race or not.

    Unlike get_major_race, an unknown name is not silently turned into an
    Imperial Human: a published source naming a species this package has no
    entry for gets a minimal record carrying that name, so the sector still
    says who lives there."""
    data = MAJOR_RACES.get(name)
    if data is not None:
        return _build_catalogued(name, homeworld_hex, data, is_major=True)
    data = CATALOGUED_RACES.get(name)
    if data is not None:
        return _build_catalogued(name, homeworld_hex, data, is_major=False)

    sophont = Sophont(name=name, homeworld_hex=homeworld_hex, is_major=False,
                      history_summary=f"{name}, native to hex {homeworld_hex}.")
    sophont.characteristic_dms = {'STR': 0, 'DEX': 0, 'END': 0}
    return sophont


def _build_catalogued(name: str, homeworld_hex: str, data: Dict[str, Any],
                      is_major: bool) -> Sophont:
    sophont = Sophont(
        name=name,
        homeworld_hex=homeworld_hex,
        is_major=is_major,
        morphology=data["morphology"],
        limbs=f"{data['limbs']} with {data['manipulators'].lower()}",
        sensory_organs=list(data["sensory_organs"]),
        reproduction=data["gender"],
        diet=data["behaviour"],
        psychology=data["psychology"],
        evolutionary_track=data["evolutionary_track"],
        history_summary=data["history_summary"],
    )
    sophont.symmetry = data["symmetry"]
    sophont.limb_count = data["limbs"]
    sophont.manipulators = data["manipulators"]
    sophont.environment = data["environment"]
    sophont.behaviour = data["behaviour"]
    sophont.gender = data["gender"]
    sophont.characteristic_dms = {'STR': 0, 'DEX': 0, 'END': 0}
    return sophont
