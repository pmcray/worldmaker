import random
from typing import List, Dict, Any, Tuple, Optional

from .classes import Sophont, CulturalProfile
from .utils import Utils

# Classic Traveller Major Races catalog
MAJOR_RACES = {
    "Aslan": {
        "morphology": "Bilateral (Feline-analogues)",
        "limbs": "4 limbs (2 arms, 2 legs, retractible claws)",
        "sensory_organs": ["Standard Vision (High Low-light)", "Acute Hearing"],
        "reproduction": "Sexual (Dimorphic)",
        "diet": "Carnivore (Hunter)",
        "psychology": "High honor, territorial social grouping",
        "evolutionary_track": "Forest / Plains predators",
        "history_summary": "Highly expansive space-faring empire ruled by clan structure."
    },
    "Zhodani": {
        "morphology": "Bilateral (Humaniti)",
        "limbs": "4 limbs (2 arms, 2 legs)",
        "sensory_organs": ["Standard Human Senses", "Psionic Sensitivity"],
        "reproduction": "Sexual",
        "diet": "Omnivore",
        "psychology": "Highly cohesive, caste-oriented, psionically cooperative",
        "evolutionary_track": "Temperate plains",
        "history_summary": "Stable, long-standing consulate ruled by psionic noble castes."
    },
    "Vargr": {
        "morphology": "Bilateral (Canine-analogues)",
        "limbs": "4 limbs (2 arms, 2 legs)",
        "sensory_organs": ["Olfactory dominant", "Low-light vision"],
        "reproduction": "Sexual",
        "diet": "Carnivore",
        "psychology": "High charisma drive, decentralized, authority-shifting pack focus",
        "evolutionary_track": "Plains hunter",
        "history_summary": "Highly fragmented polities spanning the Vargr Extents."
    },
    "Imperial Human": {
        "morphology": "Bilateral (Vilani/Solomani)",
        "limbs": "4 limbs (2 arms, 2 legs)",
        "sensory_organs": ["Standard Senses"],
        "reproduction": "Sexual",
        "diet": "Omnivore",
        "psychology": "Individualistic, highly adaptable",
        "evolutionary_track": "Grassland / Savannah",
        "history_summary": "Part of the multi-world feudal structure of the Third Imperium."
    }
}

def generate_minor_race(homeworld_hex: str, name: str = "") -> Sophont:
    """Procedurally generates a detailed Minor Sophont Race based on SCG rules."""
    if not name:
        prefixes = ["Chil", "Dra", "Eld", "Flax", "Grom", "Hyth", "Isk", "Kro", "Lur", "Mrax", "Nax", "Oph", "Pru", "Qur", "Scy", "Tla", "Urr", "Vux", "Zad"]
        suffixes = ["ian", "ax", "oid", "ite", "on", "ar", "i", "eth", "ur"]
        name = random.choice(prefixes) + random.choice(suffixes)

    # Procedural biology rolls (SCG pp. 50-60)
    morphology_options = ["Bilateral Symmetry", "Radial Symmetry", "Spherical", "Amorphous / Fluidic"]
    morphology = random.choice(morphology_options)

    limbs_options = ["2 arms, 2 legs", "4 arms, 2 legs", "6 multi-segmented legs", "8 tentacles", "No limbs (uses cilia or slithers)"]
    limbs = random.choice(limbs_options)

    sensory_list = [
        "Standard Vision & Hearing", "Infrared Thermal Pits", "Ultraviolet Vision",
        "High-Frequency Sonar Echo-location", "Electromagnetic Field Receptors",
        "Chemical Taste-feelers", "Barometric Pressure Organs"
    ]
    random.shuffle(sensory_list)
    sensory_organs = sensory_list[:random.randint(1, 3)]

    reproduction_options = ["Sexual (Dimorphic)", "Asexual (Fission)", "Spore-based cyclical lifecycle", "Egg-laying parthenogenesis"]
    reproduction = random.choice(reproduction_options)

    diet_options = ["Carnivore (Hunter)", "Carnivore (Pouncer)", "Herbivore (Grazer)", "Herbivore (Browser)", "Omnivore", "Chemosynthetic autotroph"]
    diet = random.choice(diet_options)

    psychology_options = ["Highly cooperative (Hive-like structure)", "Solitary and territorial", "Fiercely xenophobic and protective", "Inquisitive and exploration-driven", "Decentralized and shifting packs"]
    psychology = random.choice(psychology_options)

    evolution_options = ["Aquatic ocean depths", "Arboreal rainforest canopy", "Arid rocky desert canyons", "Subterranean cavern complexes", "High-gravity plains"]
    evolutionary_track = random.choice(evolution_options)

    sophont = Sophont(
        name=name,
        homeworld_hex=homeworld_hex,
        is_major=False,
        morphology=morphology,
        limbs=limbs,
        sensory_organs=sensory_organs,
        reproduction=reproduction,
        diet=diet,
        psychology=psychology,
        evolutionary_track=evolutionary_track,
        history_summary=f"Procedurally generated minor race native to system hex {homeworld_hex}."
    )
    return sophont

def get_major_race(name: str, homeworld_hex: str) -> Sophont:
    """Returns a pre-defined Major Sophont Race."""
    data = MAJOR_RACES.get(name, MAJOR_RACES["Imperial Human"])
    return Sophont(
        name=name,
        homeworld_hex=homeworld_hex,
        is_major=True,
        morphology=data["morphology"],
        limbs=data["limbs"],
        sensory_organs=data["sensory_organs"],
        reproduction=data["reproduction"],
        diet=data["diet"],
        psychology=data["psychology"],
        evolutionary_track=data["evolutionary_track"],
        history_summary=data["history_summary"]
    )
