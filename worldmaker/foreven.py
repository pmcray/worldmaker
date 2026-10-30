"""
Canonical & Referee's Preserve Generator for the Foreven Sector (Year 1107).

Implements:
1. All 358 canonical star system hexes from the Far Future Enterprises Foreven
   Sector Reserve and the exact Zhodani Consulate (Iakr Sector) border.
2. Only the 4 FFE Reserve subsector names (D: Massina, H: Fessor, L: Reidain,
   P: Urnian) plus Zhodani/polity-themed names for the remaining 12 subsectors.
3. Full five-epoch macro-historical settlement model (-300,000 Ancients through
   the Rule of Man, Darrian Maghiz, Frontier Wars I-IV, Psionic Suppressions,
   and the 1107 Septiman War / eve of the Fifth Frontier War) consistent with
   surrounding sectors (Ziafrplians, Spinward Marches, Vanguard Reaches,
   The Beyond, and Far Frontiers).
4. Canonical & SCG-anchored worlds (Zdovesil, Tlebria, Hollis, Alenzar, Raschev,
   Parthinia, Avalar + all 27 Avalar Consulate systems, Tlesho + the Tlinzha
   Union, 4 Ancient Ruins, 12 Scattered Settlements, and the Subsector J
   Barren Anomaly).
5. Special Referee's Preserve elements in Year 1107:
   - The Heptamorphoid Hivemind Aliens (The Heptarchy of Septima, code 'He')
     waging the Septiman War against the Avalar Consulate across the J/N border.
   - Uplifted Terran Cats (Felis catus sapiens - The Chatelaine of Bastet,
     code 'Fe') in Spinward-Rimward Subsector M/I.
   - Halfling-like Human Minor Race (Homo sapiens parvulus - The Issugur /
     Periannath of Parthinia 3018 and The Shire 2835, code 'Hl').
   - Automatic Earth-Similarity Index (ESI) evaluation across all generated
     worlds to christen the most Earth-like planet 'Erith'.
"""

import math
import random
from typing import Dict, List, Optional, Tuple, Any

from .classes import (
    Sector,
    StellarSystem,
    Star,
    PlanetaryBody,
    Satellite,
    UWP,
    Sophont,
    Polity,
    Wave,
    CulturalProfile,
)
from .utils import Utils
from .generator import generate_full_system, assign_final_designations, flag_points_of_interest
from .geophysics import (
    generate_geophysics,
    generate_rotation_period,
    calculate_mean_temperature,
    generate_surface_features,
    generate_life,
)
from .society import (
    generate_trade_codes,
    generate_social_details,
    generate_expanded_tech_matrix,
    generate_government,
    generate_law_level,
    generate_starport,
    generate_tech_level,
)
from .analogues import (
    calculate_stellar_metallicity,
    evaluate_planetary_age_habitability,
    compute_solar_analogue_score,
    find_solar_analogues,
    compute_solar_system_analogue_score,
    find_solar_system_analogues,
    compute_coupled_earth_similarity_score,
    find_earth_analogues,
)


# ==============================================================================
# 1. CANONICAL 358 STAR HEXES & ZHODANI CONSULATE BORDER (FFE RESERVE)
# ==============================================================================

FOREVEN_RESERVE_HEXES: List[str] = [
    "0103", "0104", "0202", "0203", "0302", "0304", "0305", "0306", "0308", "0309",
    "0401", "0402", "0403", "0404", "0408", "0502", "0503", "0504", "0505", "0507",
    "0508", "0604", "0607", "0610", "0708", "0801", "0807", "0810", "0902", "0908",
    "0909", "0910", "1007", "1102", "1103", "1109", "1205", "1209", "1303", "1304",
    "1307", "1403", "1404", "1405", "1410", "1501", "1504", "1507", "1602", "1701",
    "1703", "1704", "1804", "1806", "1807", "1808", "1901", "1905", "2002", "2003",
    "2005", "2102", "2103", "2202", "2209", "2304", "2306", "2309", "2310", "2501",
    "2502", "2602", "2603", "2607", "2608", "2610", "2710", "2805", "2807", "2808",
    "2905", "2907", "2910", "3003", "3006", "3107", "3108", "3201", "3204", "3205",
    "3206", "0112", "0113", "0116", "0211", "0212", "0213", "0214", "0218", "0312",
    "0411", "0412", "0418", "0513", "0516", "0517", "0520", "0612", "0712", "0716",
    "0717", "0720", "0814", "0815", "0818", "0819", "0820", "0911", "0914", "0915",
    "0919", "1012", "1016", "1111", "1112", "1115", "1212", "1214", "1216", "1218",
    "1312", "1314", "1316", "1317", "1319", "1411", "1412", "1416", "1419", "1519",
    "1612", "1617", "1618", "1619", "1620", "1712", "1813", "1815", "1816", "1817",
    "1915", "1920", "2017", "2113", "2211", "2214", "2311", "2320", "2412", "2517",
    "2518", "2520", "2611", "2613", "2614", "2615", "2616", "2712", "2715", "2811",
    "2812", "2814", "2820", "2920", "3013", "3014", "3015", "3018", "3020", "3111",
    "3115", "3116", "3119", "3212", "3214", "3215", "3217", "0129", "0130", "0223",
    "0224", "0226", "0227", "0422", "0424", "0426", "0526", "0527", "0623", "0723",
    "0730", "0822", "0825", "0926", "0930", "1026", "1124", "1126", "1224", "1325",
    "1329", "1330", "1422", "1423", "1426", "1427", "1428", "1429", "1523", "1528",
    "1622", "1628", "1630", "1724", "1725", "1726", "1728", "1729", "1822", "1828",
    "1926", "1927", "2021", "2022", "2023", "2121", "2123", "2128", "2225", "2230",
    "2325", "2326", "2328", "2422", "2427", "2428", "2429", "2430", "2523", "2527",
    "2528", "2623", "2724", "2822", "2823", "2829", "2923", "2924", "2925", "2926",
    "2927", "3021", "3027", "3028", "3126", "3129", "3227", "3229", "3230", "0131",
    "0135", "0136", "0232", "0235", "0236", "0239", "0332", "0335", "0336", "0431",
    "0436", "0437", "0439", "0538", "0633", "0634", "0639", "0732", "0734", "0735",
    "0837", "0839", "0840", "0935", "1032", "1039", "1139", "1140", "1234", "1239",
    "1240", "1335", "1432", "1534", "1536", "1539", "1631", "1632", "1634", "1636",
    "1637", "1639", "1640", "1734", "1738", "1739", "1833", "1834", "1840", "1936",
    "1938", "2040", "2135", "2136", "2137", "2231", "2236", "2237", "2334", "2335",
    "2431", "2433", "2532", "2537", "2632", "2634", "2731", "2736", "2739", "2740",
    "2833", "2834", "2835", "2836", "2838", "2934", "2935", "2937", "2938", "2940",
    "3034", "3035", "3037", "3131", "3134", "3135", "3232", "3238",
]

FOREVEN_ZHODANI_HEXES = set([
    "0103", "0104", "0202", "0203", "0302", "0304", "0305", "0306", "0308", "0309",
    "0401", "0402", "0403", "0404", "0408", "0502", "0503", "0504", "0505", "0507",
    "0508", "0604", "0607", "0610", "0708", "0801", "0807", "0810", "0902", "0908",
    "0909", "0910", "1007", "1102", "1103", "1109", "1205", "1209", "1303", "1304",
    "1307", "1403", "1404", "1405", "1410", "1501", "1504", "1507", "1602", "1701",
    "1703", "1704", "1804", "1806", "1807", "1808", "1901", "1905", "2002", "2003",
    "2005", "2102", "2103", "2202", "2304", "2306", "2501", "2502", "2602", "2603",
    "2607", "2608", "2610", "2710", "2805", "2807", "2808", "2905", "2907", "2910",
    "3003", "3006", "3107", "3108", "3201", "3204", "3205", "3206", "0112", "0113",
    "0116", "0211", "0212", "0213", "0214", "0218", "0312", "0411", "0412", "0418",
    "0513", "0516", "0517", "0612", "0712", "0716", "0717", "0814", "0815", "0818",
    "0911", "0914", "0915", "1012", "1016", "1111", "1112", "1115", "1212", "1214",
    "1216", "1312", "1314", "1316", "1411", "1412", "1612", "1712", "1813", "1815",
    "1816", "1817", "1915", "1920", "2017", "2113", "2211", "2214", "2311", "2320",
    "2412", "2811",
    # SCG Decision #5 notes 2209, 2309, 2310 are barren systems inside Zhodani Subsector C
    "2209", "2309", "2310",
])


# ==============================================================================
# 2. SUBSECTOR NAMING (4 CANONICAL FFE RESERVE + 12 ZHODANI/POLITY THEMED)
# ==============================================================================

FOREVEN_SUBSECTORS: Dict[str, str] = {
    "A": "Vlazhdum",   # Coreward-Spinward Zhodani heartland
    "B": "Chtierabl",  # Coreward Zhodani interior
    "C": "Zdovesil",   # Zhodani Iakr Sector provincial capital subsector
    "D": "Massina",    # Canonical FFE Reserve (Zhodani-conquered ex-Imperial frontier)
    "E": "Tlesho",     # Zhodani southern frontier & Tlinzha Union border
    "F": "Tlebria",    # Zhodani corporate & frontier buffer
    "G": "Chiepzh",    # Zhodani-Imperial contested mid-frontier
    "H": "Fessor",     # Canonical FFE Reserve (Spinward Main extension border)
    "I": "Khefr",      # Isolated Spinward shadow reach behind Tlinzha bottleneck
    "J": "Septima",    # Subsector J Barren Anomaly & Heptamorphoid Hivemind front
    "K": "Hollis",     # Hollis Imperial Client hub & Spinward Main terminus
    "L": "Reidain",    # Canonical FFE Reserve (Alenzar, Raschev, Parthinia & Darrian border)
    "M": "Bastet",     # Spinward-Rimward refuge & Chatelaine of Uplifted Terran Cats
    "N": "Avalar",     # Avalar Consulate heartland & Septiman War front
    "O": "Presidio",   # Eastern march of the Avalar Consulate & Zuekgoz occupation zone
    "P": "Urnian",     # Canonical FFE Reserve (Imperial Client States & Five Sisters border)
}


# ==============================================================================
# 3. DEEP MACRO-HISTORY & SURROUNDING SECTORS (TO YEAR 1107)
# ==============================================================================

FOREVEN_MACRO_HISTORY: List[Dict[str, Any]] = [
    {
        "epoch": "Epoch I: The Ancients & Deep Time",
        "dates": "-300,000",
        "summary": (
            "Grandfather's children occupy Foreven, transplanting the halfling-like "
            "Issugur (Homo sapiens parvulus) from Pleistocene Terra to Parthinia (3018) "
            "and later The Shire (2835), scattering Droyne (0935, 1216) and Chirpers "
            "(0104, 1303), and leaving four devastated Ancient Ruins worlds (1726, 2615, "
            "2740, 3006). Meanwhile, eight native sophont species evolve independently, "
            "including the two-headed octopod Tlinzha of Tlesho (0720) and the dormant "
            "seven-fold radial Heptamorphoid Hivemind of Septima Prime (1628)."
        ),
    },
    {
        "epoch": "Epoch II: Zhodani Coreward Wave, Rule of Man & Darrian Contact",
        "dates": "-5000 to -955",
        "summary": (
            "Zhodani scouts from coreward Ziafrplians explore Iakr (-5000) and settle "
            "Subsectors A, B, and C (-4000 to -1000), establishing the provincial capital "
            "at Zdovesil (1212) and contacting the Tlinzha (-4880). During the Rule of Man "
            "(-1856 to -1850), the Solomani Tvastar-class manufactory starship 'Avalar' "
            "settles Avalar (1636) while its companion seedship 'Caelum Felis' lands "
            "genetically uplifted Terran cats (Felis catus sapiens) at Bastet (0131). "
            "Zhodani explorers contact Avalar in -1635 and introduce psionics (-1000), "
            "which the Avalar Church canonizes at the Council of Revelation (-588). "
            "To trailing, the pre-Maghiz Darrian Empire contacts native worlds (1927, 2328) "
            "before collapsing in the Maghiz solar flare of -955."
        ),
    },
    {
        "epoch": "Epoch III: Pre-War Imperial Thin Wave & Spinward Main Extension",
        "dates": "-21 to 589",
        "summary": (
            "Avalar achieves Jump-1 (-21) and settles Tranquilidad (1637) in Year 18. "
            "Imperial scouts from the Spinward Marches reach Avalar in 206. Prior to 600, "
            "an Imperial thin settlement wave crosses from Vilis, Darrian, and Five Sisters "
            "into the four trailing subsectors—Massina (D), Fessor (H), Reidain (L), and "
            "Urnian (P)—extending the Spinward Main through Raschev (3230) and Alenzar "
            "(3229) to the Naval/Scout stronghold at Hollis (2523)."
        ),
    },
    {
        "epoch": "Epoch IV: Frontier Wars I–II & Geopolitical Partition",
        "dates": "589 to 750",
        "summary": (
            "In the First Frontier War (589–604), Zhodani forces conquer Massina (D), "
            "driving out Imperial forces and leaving unabsorbed human colonies under "
            "Consular oversight. Following the Second Frontier War (615–620), the Zhodani "
            "push a defensive thin settlement wave into Subsectors E, F, and G (600–700) "
            "and sign the Treaty of 628 formally establishing the 27-system Avalar "
            "Consulate in Subsectors N and O as a psionic client buffer blocking Imperial "
            "expansion to spinward."
        ),
    },
    {
        "epoch": "Epoch V: Psionic Suppressions, The Septiman War & Eve of the Fifth Frontier War",
        "dates": "800 to 1107",
        "summary": (
            "The Imperial Psionic Suppressions (800–826) drive a major wave of psionic "
            "refugees into the Avalar Consulate. During the Third (979–986) and Fourth "
            "(1082–1084) Frontier Wars, Avalar and Imperial forces in Urnian trade bloody "
            "raids (devastating Tranquilidad in 985), and in 1045 Avalar occupies the "
            "Vargr corsair world of Zuekgoz (1938). Meanwhile, in Subsector J, the "
            "seven-fold radial Heptamorphoid Hivemind of Septima Prime (1628)—having "
            "stripped the 'Bermuda Triangle' worlds of northern Subsector J (1124–1622) "
            "barren to gestate living spore-dreadnoughts—erupts southward in 1104. "
            "Now in 1107, as the Fifth Frontier War ignites in the Spinward Marches, "
            "Defence Minister Admiral Jorj Valenz's Avalar Consular Armada is locked in "
            "desperate combat against the Heptarchy of Septima along the Lun Escarpa (1630) "
            "– Rocaroja (1432) – Pres Tinto (1734) fortress line."
        ),
    },
]


# ==============================================================================
# 4. CANONICAL, SCG & REFEREE-PRESERVE PRE-SPECIFIED SYSTEMS
# ==============================================================================

# Subsector J & C Barren Anomaly worlds (SCG Decision #5)
SUBSECTOR_J_BARREN_ANOMALY: Dict[str, Dict[str, Any]] = {
    "1124": {"name": "Velo-Vacua", "starport": "X", "note": "Subsector J Barren Anomaly: failed colony; ships vanish in jump emergence."},
    "1224": {"name": "Verdant Ghost", "starport": "E", "uwp": "E666000-0", "note": "Subsector J Barren Anomaly: eerie uninhabited Garden world with mapped landing beacons from vanished colony."},
    "1325": {"name": "Silent Eden", "starport": "E", "uwp": "E767000-0", "note": "Subsector J Barren Anomaly: abandoned Garden world stripped of colonists by early Heptamorph spore-probes."},
    "1422": {"name": "Cinder-1422", "starport": "X", "note": "Subsector J Barren Anomaly: biosphere stripped barren; electromagnetic 7-harmonic hum."},
    "1423": {"name": "Chokepoint-1423", "starport": "X", "uwp": "X656000-0", "no_gas_giant": True, "note": "Subsector J Barren Anomaly: sole Jump-2 bridge across the anomaly; no gas giant (requires risky ocean wilderness refueling)."},
    "1523": {"name": "Hollow-1523", "starport": "X", "note": "Subsector J Barren Anomaly: derelict orbital docks; zero survivors."},
    "1622": {"name": "Frost-1622", "starport": "X", "uwp": "X311000-0", "note": "Subsector J Barren Anomaly: cold airless world with crystallized Heptamorph relay pylons."},
    "0822": {"name": "Periphery-0822", "starport": "X", "uwp": "X200000-0", "note": "Anomaly Periphery: cold vacuum world where scout ships report phantom 7-fold sensor echoes."},
    "1218": {"name": "Periphery-1218", "starport": "X", "note": "Anomaly Periphery: abandoned Zhodani border listening post."},
    "1319": {"name": "Periphery-1319", "starport": "X", "note": "Anomaly Periphery: failed frontier settlement on edge of the Septiman void."},
    "1419": {"name": "Periphery-1419", "starport": "X", "note": "Anomaly Periphery: barren rock marking the northern quarantine line of Subsector J."},
    "2209": {"name": "Zhdo-2209", "starport": "X", "allegiance": "Zh", "note": "Zhodani Subsector C Barren Trio: unexplained sterile system inside the Consulate."},
    "2309": {"name": "Zhdo-2309", "starport": "X", "allegiance": "Zh", "note": "Zhodani Subsector C Barren Trio: Consular Navy jump-shadow monitoring buoy."},
    "2310": {"name": "Zhdo-2310", "starport": "X", "allegiance": "Zh", "note": "Zhodani Subsector C Barren Trio: uninhabited system under Zhodani Consular survey."},
}

# Pre-defined Canonical, SCG, and Referee's Preserve Anchor Systems
FOREVEN_FIXED_SYSTEMS: Dict[str, Dict[str, Any]] = {
    # --- 1. FFE Reserve & Classic Traveller Canonical Worlds ---
    "1212": {
        "name": "Zdovesil",
        "uwp": "A65588A-9",
        "allegiance": "Zh",
        "bases": ["Zhodani Naval", "Zhodani Base"],
        "pbg": "103",
        "primary_spectral": "M1 V",
        "companion_spectral": "M3 V",
        "epoch": "Epoch II (-4000)",
        "wave": "Zhodani Coreward Heartland",
        "note": "Canonical Zhodani provincial capital for Iakr (Foreven) Sector within Iadr Nsobl Province.",
    },
    "1618": {
        "name": "Tlebria",
        "uwp": "B667876-C",
        "allegiance": "Zh",
        "bases": ["Zhodani Base"],
        "pbg": "212",
        "epoch": "Epoch IV (640)",
        "wave": "Zhodani Counter-Expansion Wave",
        "note": "Canonical Zhodani corporate shipping hub (CT Book 7: Merchant Prince); headquarters of Tlebria Interstellar.",
    },
    "2523": {
        "name": "Hollis",
        "uwp": "A370642-C",
        "allegiance": "Cs",
        "bases": ["Naval", "Scout"],
        "pbg": "303",
        "primary_spectral": "M3 V",
        "epoch": "Epoch III (410)",
        "wave": "Imperial Spinward Main Thin Wave",
        "note": "Canonical Imperial Client State housing both Imperial Naval and Scout bases; Spinward Main terminus.",
    },
    "3229": {
        "name": "Alenzar",
        "uwp": "C000414-9",
        "allegiance": "Cs",
        "bases": [],
        "pbg": "513",
        "primary_spectral": "M0 III",
        "epoch": "Epoch III (480)",
        "wave": "Imperial Spinward Main Thin Wave",
        "note": "Canonical Imperial Client State asteroid belt system (CT Double Adventure 5: The Chamax Plague).",
    },
    "3230": {
        "name": "Raschev",
        "uwp": "C8697C4-6",
        "allegiance": "Cs",
        "bases": [],
        "pbg": "123",
        "primary_spectral": "M3 V",
        "epoch": "Epoch III (465)",
        "wave": "Imperial Spinward Main Thin Wave",
        "note": "Canonical Imperial Client State in Reidain Subsector (CT Double Adventure 5: The Horde).",
    },
    "3018": {
        "name": "Parthinia",
        "uwp": "C694655-C",
        "allegiance": "Hl",
        "bases": [],
        "travel_zone": "A",
        "epoch": "Epoch I (-300,000)",
        "wave": "Ancients Transplant / Halfling Minor Race",
        "note": "Canonical world (CT Alien Realms) with human mining outpost and upland hill-warren reservations of the Issugur (Homo sapiens parvulus), a halfling-like human minor race transplanted from Terra by the Ancients.",
    },

    # --- 2. The 27 Systems of the Avalar Consulate (SCG pp. 44-49) ---
    "1636": {
        "name": "Avalar",
        "uwp": "A75599C-C",
        "allegiance": "Av",
        "bases": ["Naval"],
        "pbg": "904",
        "primary_spectral": "M0 V",
        "epoch": "Epoch II (-1850)",
        "wave": "Solomani Tvastar Colony / Avalar Core",
        "note": "Canonical capital of the 27-system Avalar Consulate (9 billion pop); settled in -1850 by the Tvastar-class starship Avalar. Seat of the Grand Congress at Alunizar and command center for the 1107 Septiman War against the Heptamorphoid Hivemind.",
    },
    "1630": {
        "name": "Lun Escarpa",
        "uwp": "B400310-C",
        "allegiance": "Av",
        "bases": ["Naval"],
        "travel_zone": "A",
        "epoch": "Epoch IV (780)",
        "wave": "Avalar Outer Ripple (Septiman War Front)",
        "note": "Northernmost naval fortress of the Avalar Consulate; under direct siege by Heptamorphoid Hivemind bioships from Septima Prime (1628) in 1107.",
    },
    "1234": {
        "name": "Amanecer",
        "uwp": "C212347-9",
        "allegiance": "Av",
        "bases": [],
        "epoch": "Epoch IV (810)",
        "wave": "Avalar Outer Ripple",
        "note": "Spinward ice-capped listening post of the Avalar Consulate.",
    },
    "1335": {
        "name": "Ardiente",
        "uwp": "B461885-B",
        "allegiance": "Av",
        "bases": [],
        "epoch": "Epoch IV (628)",
        "wave": "Avalar Inner Ripple",
        "note": "Rich colonial world settled in 628 at the formal founding of the Avalar Consulate.",
    },
    "1432": {
        "name": "Rocaroja",
        "uwp": "B100798-A",
        "allegiance": "Av",
        "bases": ["Naval"],
        "travel_zone": "A",
        "epoch": "Epoch IV (760)",
        "wave": "Avalar Outer Ripple (Septiman War Front)",
        "note": "Fortified vacuum naval base anchoring the western flank of the Avalar–Heptamorph War front.",
    },
    "1534": {
        "name": "Acerbo",
        "uwp": "E877100-7",
        "allegiance": "Av",
        "bases": [],
        "epoch": "Epoch III (510)",
        "wave": "Avalar Core Cluster",
        "note": "Sparsely inhabited reserve world within the Avalar core cluster.",
    },
    "1536": {
        "name": "Lun Varga",
        "uwp": "C336412-9",
        "allegiance": "Av",
        "bases": [],
        "epoch": "Epoch III (320)",
        "wave": "Avalar Core Cluster",
        "note": "Early Jump-1 colony of the Avalar core cluster.",
    },
    "1539": {
        "name": "Horizonte",
        "uwp": "D87A653-6",
        "allegiance": "Av",
        "bases": [],
        "epoch": "Epoch IV (740)",
        "wave": "Avalar Inner Ripple",
        "note": "Pelagic waterworld of the southern Avalar Consulate.",
    },
    "1631": {
        "name": "Buergeria",
        "uwp": "C542635-6",
        "allegiance": "Av",
        "bases": [],
        "travel_zone": "A",
        "epoch": "Epoch IV (790)",
        "wave": "Avalar Outer Ripple (Septiman War Front)",
        "note": "Staging depot immediately behind the Lun Escarpa (1630) anti-Heptamorph battlefront.",
    },
    "1632": {
        "name": "Escandi",
        "uwp": "E746321-3",
        "allegiance": "Av",
        "bases": [],
        "epoch": "Epoch IV (775)",
        "wave": "Avalar Outer Ripple",
        "note": "Low-tech frontier supply world along the coreward Avalar military corridor.",
    },
    "1634": {
        "name": "Hortali",
        "uwp": "A9B8787-C",
        "allegiance": "Av",
        "bases": [],
        "epoch": "Epoch III (480)",
        "wave": "Avalar Core Cluster",
        "note": "High-tech fluid-ocean industrial shipyard world of the Avalar Consulate.",
    },
    "1637": {
        "name": "Tranquilidad",
        "uwp": "C669638-8",
        "allegiance": "Av",
        "bases": [],
        "epoch": "Epoch III (18)",
        "wave": "Avalar Core Cluster",
        "note": "First interstellar colony of Avalar (settled Year 18); devastated by an Imperial strike in 985 during the Third Frontier War.",
    },
    "1639": {
        "name": "Lun Estrad",
        "uwp": "B4346A8-A",
        "allegiance": "Av",
        "bases": [],
        "epoch": "Epoch IV (680)",
        "wave": "Avalar Inner Ripple",
        "note": "Southern industrial and mining hub of the Avalar Consulate.",
    },
    "1640": {
        "name": "Orilla",
        "uwp": "B400233-C",
        "allegiance": "Av",
        "bases": ["Naval"],
        "epoch": "Epoch IV (710)",
        "wave": "Avalar Inner Ripple",
        "note": "Rimward border naval station of the Consular Armada.",
    },
    "1734": {
        "name": "Pres Tinto",
        "uwp": "B452464-C",
        "allegiance": "Av",
        "bases": ["Naval", "Zhodani Base"],
        "epoch": "Epoch V (983)",
        "wave": "Avalar Inner Ripple",
        "note": "Essential Consular Armada fortress ('Presidio Tinto', established 983) under direct military rule; coordinates joint Avalar-Zhodani psionic defense against the Heptamorphoid Hivemind.",
    },
    "1738": {
        "name": "Pres Alfa",
        "uwp": "B443454-C",
        "allegiance": "Av",
        "bases": ["Naval", "Zhodani Base"],
        "epoch": "Epoch V (983)",
        "wave": "Avalar Inner Ripple",
        "note": "Southern Consular Armada fortress world ('Presidio Alfa') with deep meson sites and Zhodani liaison advisors.",
    },
    "1739": {
        "name": "Lun Rico",
        "uwp": "D442221-7",
        "allegiance": "Av",
        "bases": [],
        "epoch": "Epoch IV (730)",
        "wave": "Avalar Inner Ripple",
        "note": "Quiet mining colony in southern Avalar space.",
    },
    "1833": {
        "name": "Salacia",
        "uwp": "C98A154-C",
        "allegiance": "Av",
        "bases": [],
        "epoch": "Epoch IV (750)",
        "wave": "Avalar Inner Ripple",
        "note": "High-tech deep-ocean research world of the Avalar Consulate.",
    },
    "1834": {
        "name": "Cloacina",
        "uwp": "C510647-8",
        "allegiance": "Av",
        "bases": [],
        "epoch": "Epoch IV (690)",
        "wave": "Avalar Inner Ripple",
        "note": "Arid mineral processing world in the central Consulate.",
    },
    "1840": {
        "name": "Atun",
        "uwp": "C66A336-A",
        "allegiance": "Av",
        "bases": [],
        "epoch": "Epoch IV (795)",
        "wave": "Avalar Outer Ripple",
        "note": "Rimward maritime harvesting colony of Avalar.",
    },
    "1936": {
        "name": "Tresca",
        "uwp": "D76A340-6",
        "allegiance": "Av",
        "bases": [],
        "epoch": "Epoch IV (720)",
        "wave": "Avalar Inner Ripple",
        "note": "Waterworld waypoint linking Avalar to the eastern Presidio march.",
    },
    "1938": {
        "name": "Zuekgoz",
        "uwp": "C657864-6",
        "allegiance": "Av",
        "bases": ["Military"],
        "travel_zone": "A",
        "epoch": "Epoch II (Vargr Scatter) / Occupied 1045",
        "wave": "Scattered Vargr Colony (Avalar Military Occupation)",
        "note": "Vargr-populated Garden world occupied by 20 brigades of Avalar Naval Infantry since 1045 to suppress corsair raids.",
    },
    "2135": {
        "name": "Fragos",
        "uwp": "A000641-C",
        "allegiance": "Av",
        "bases": ["Naval"],
        "epoch": "Epoch V (855)",
        "wave": "Avalar Outer Ripple",
        "note": "Major asteroid naval shipyard established in 855; former command of Defence Minister Admiral Jorj Valenz and construction site of Avalar's new battlecruisers.",
    },
    "2136": {
        "name": "Ninfa",
        "uwp": "B567757-B",
        "allegiance": "Av",
        "bases": [],
        "epoch": "Epoch IV (704)",
        "wave": "Avalar Inner Ripple",
        "note": "Rich agricultural breadbasket of the eastern Avalar Consulate (settled 704).",
    },
    "2137": {
        "name": "Drevas",
        "uwp": "D410444-9",
        "allegiance": "Av",
        "bases": [],
        "epoch": "Epoch IV (760)",
        "wave": "Avalar Outer Ripple",
        "note": "Cold vacuum support outpost near Ninfa.",
    },
    "2236": {
        "name": "Larissa",
        "uwp": "C659841-7",
        "allegiance": "Av",
        "bases": [],
        "epoch": "Epoch IV (744)",
        "wave": "Avalar Outer Ripple",
        "note": "Pre-existing human colony that voluntarily joined the Avalar Consulate in 744; raided by Imperial cruisers in 1084.",
    },
    "2237": {
        "name": "Lun Orcus",
        "uwp": "B100341-C",
        "allegiance": "Av",
        "bases": ["Naval"],
        "epoch": "Epoch V (870)",
        "wave": "Avalar Outer Ripple",
        "note": "Trailing-most naval picket base of the Avalar Consulate facing Imperial client states in Urnian; raided in 1084.",
    },

    # --- 3. The Heptamorphoid Hivemind (The Heptarchy of Septima, Code 'He') ---
    "1628": {
        "name": "Septima Prime",
        "uwp": "B6A69FB-C",
        "allegiance": "He",
        "bases": ["Naval"],
        "travel_zone": "R",
        "epoch": "Epoch I (Native Sophont Homeworld)",
        "wave": "Heptamorphoid Hivemind Nexus",
        "note": "Homeworld of the Heptamorphs (Khept-7): a 7-fold radially symmetric biological/psionic hivemind native to a dense exotic atmosphere (SCG 1628). Since 1104, Septima Prime has waged the Septiman War against the Avalar Consulate (Lun Escarpa 1630).",
    },
    "1428": {
        "name": "Hept-Secundus",
        "uwp": "C5867FA-B",
        "allegiance": "He",
        "bases": ["Military"],
        "travel_zone": "R",
        "epoch": "Epoch V (1092)",
        "wave": "Heptamorphoid Hivemind Expansion",
        "note": "Western brood-cluster of the Heptarchy of Septima; launches spore-cruiser strikes against Avalar's Rocaroja (1432) naval base.",
    },
    "1429": {
        "name": "Synapse-Velo",
        "uwp": "C4646F9-B",
        "allegiance": "He",
        "bases": [],
        "travel_zone": "R",
        "epoch": "Epoch V (1098)",
        "wave": "Heptamorphoid Hivemind Expansion",
        "note": "Planetary psionic-resonator array amplifying the Heptamorph Hivemind's 7-harmonic telepathic lattice.",
    },
    "1528": {
        "name": "Chitin-Reach",
        "uwp": "B7978FB-C",
        "allegiance": "He",
        "bases": ["Naval"],
        "travel_zone": "R",
        "epoch": "Epoch V (1088)",
        "wave": "Heptamorphoid Hivemind Expansion",
        "note": "Primary orbital gestation yard for the Heptamorphoid Hivemind's heptagonal bioships.",
    },
    "1728": {
        "name": "Khept-Spire",
        "uwp": "C6757FA-B",
        "allegiance": "He",
        "bases": ["Military"],
        "travel_zone": "R",
        "epoch": "Epoch V (1095)",
        "wave": "Heptamorphoid Hivemind Expansion",
        "note": "Forward assault hive-world staging attacks toward Lun Escarpa (1630) and Pres Tinto (1734).",
    },
    "1729": {
        "name": "Resonance-7",
        "uwp": "D3546F9-A",
        "allegiance": "He",
        "bases": [],
        "travel_zone": "R",
        "epoch": "Epoch V (1103)",
        "wave": "Heptamorphoid Hivemind Expansion",
        "note": "Frontline contested world in the 1107 Avalar–Heptamorph War; scarred by Consular Armada orbital bombardment.",
    },
    "1828": {
        "name": "Biolattice-Alpha",
        "uwp": "C5667FA-B",
        "allegiance": "He",
        "bases": [],
        "travel_zone": "R",
        "epoch": "Epoch V (1101)",
        "wave": "Heptamorphoid Hivemind Expansion",
        "note": "Easternmost anchor of the 7-system Heptarchy of Septima.",
    },

    # --- 4. Uplifted Terran Cats (Felis catus sapiens - Chatelaine of Bastet, Code 'Fe') ---
    "0131": {
        "name": "Bastet",
        "uwp": "A654956-E",
        "allegiance": "Fe",
        "bases": ["Naval", "Scout"],
        "epoch": "Epoch II (-1851)",
        "wave": "Rule of Man Seedship / Uplifted Terran Feline Freehold",
        "note": "Capital of the Chatelaine of Bastet (SCG 0131): a high-tech (TL14) Garden world settled in -1851 by genetically uplifted Terran cats (Felis catus sapiens) from the Rule of Man research vessel Caelum Felis.",
    },
    "0232": {
        "name": "Chatelaine",
        "uwp": "B666754-C",
        "allegiance": "Fe",
        "bases": ["Scout"],
        "epoch": "Epoch III (140)",
        "wave": "Uplifted Terran Feline Freehold",
        "note": "Arboreal canopy world of the Uplifted Terran Cats; hub of sleek high-agility Jump-3 courier vessels.",
    },
    "0332": {
        "name": "Mau",
        "uwp": "B565743-C",
        "allegiance": "Fe",
        "bases": [],
        "epoch": "Epoch III (290)",
        "wave": "Uplifted Terran Feline Freehold",
        "note": "Warm savannah world of the Feline Freehold where visiting Aslan ihatei are bewildered by 6-kg Terran felids operating TL12 starports.",
    },
    "0431": {
        "name": "Pasht",
        "uwp": "C544642-B",
        "allegiance": "Fe",
        "bases": [],
        "epoch": "Epoch IV (610)",
        "wave": "Uplifted Terran Feline Freehold",
        "note": "Border watch-post of the Chatelaine of Bastet monitoring spinward trade routes.",
    },
    "0825": {
        "name": "Catspaw",
        "uwp": "C677776-9",
        "allegiance": "Fe",
        "bases": ["Scout"],
        "epoch": "Epoch IV (720)",
        "wave": "Uplifted Terran Feline Freehold / Native Co-Habitation",
        "note": "Temperate garden waystation (SCG 0825) shared by Feline Freehold traders and a peaceful indigenous minor sophont.",
    },

    # --- 5. Halfling-like Human Minor Race (Homo sapiens parvulus - Issugur / Periannath, Code 'Hl') ---
    "2835": {
        "name": "The Shire",
        "uwp": "C577757-7",
        "allegiance": "Hl",
        "bases": [],
        "epoch": "Epoch I (-300,000)",
        "wave": "Ancients Transplant / Halfling Minor Race",
        "note": "Flourishing pastoral homeworld of the Periannath / Issugur (Homo sapiens parvulus, SCG 2835)—a 1-meter-tall, burrowing-hillside, seven-meal-a-day halfling human minor race with natural immunity to psionic coercion, open for peaceful agricultural trade.",
    },
    "2834": {
        "name": "Bywater",
        "uwp": "C666643-7",
        "allegiance": "Hl",
        "bases": [],
        "epoch": "Epoch III (310)",
        "wave": "Halfling Agrarian Settlement",
        "note": "Terraced river-valley colony of the Halfling Periannath, famed across Urnian and Reidain for pipe-weed, vintage ales, and orchard produce.",
    },
    "2935": {
        "name": "Bucklebury",
        "uwp": "D566632-6",
        "allegiance": "Hl",
        "bases": [],
        "epoch": "Epoch III (420)",
        "wave": "Halfling Agrarian Settlement",
        "note": "Quiet rural Halfling ferry-world whose hill-delvings conceal an Ancient subterranean vault.",
    },

    # --- 6. The Tlinzha of the Tlesho Union (SCG pp. 55-62, Code 'Tl') ---
    "0720": {
        "name": "Tlesho",
        "uwp": "A998844-A",
        "allegiance": "Tl",
        "bases": ["Naval"],
        "travel_zone": "A",
        "primary_spectral": "F5 V",
        "companion_spectral": "M3 V",
        "epoch": "Epoch I (Native Sophont Homeworld)",
        "wave": "Tlesho Union Core",
        "note": "Homeworld of the Tlinzha (SCG p. 55): two-headed bilateral octopod scavengers orbiting a flare-prone M3 V companion to an F5 V primary. Capital of the xenophobic 4-system Tlesho Union.",
    },
    "0819": {
        "name": "Zhdikevli",
        "uwp": "C675656-9",
        "allegiance": "Tl",
        "bases": [],
        "travel_zone": "A",
        "epoch": "Epoch III (340)",
        "wave": "Tlesho Union Expansion",
        "note": "Member world of the Tlesho Union (Tlinzha octopods); closed to non-Zhodani outsiders.",
    },
    "0820": {
        "name": "Chtenchee",
        "uwp": "C554645-9",
        "allegiance": "Tl",
        "bases": [],
        "travel_zone": "A",
        "epoch": "Epoch III (380)",
        "wave": "Tlesho Union Expansion",
        "note": "Member world of the Tlesho Union guarding the spinward chokepoint into Subsector I.",
    },
    "0919": {
        "name": "Zdefr",
        "uwp": "D433546-8",
        "allegiance": "Tl",
        "bases": [],
        "travel_zone": "A",
        "epoch": "Epoch III (410)",
        "wave": "Tlesho Union Expansion",
        "note": "Trailing picket world of the Tlesho Union governed by the Scholars of the Protocols of the Consumption of Meats.",
    },

    # --- 7. Remaining SCG Native Sophonts, Ancient Ruins & Scattered Settlements ---
    "0103": {
        "name": "Vlazh-0103",
        "uwp": "E5589BD-3",
        "allegiance": "Zh",
        "travel_zone": "R",
        "epoch": "Epoch I (Native Sophont)",
        "wave": "Native Sophont (Zhodani Interdiction)",
        "note": "SCG Native Sophont homeworld under Zhodani Consular Red Zone protective interdiction.",
    },
    "0214": {
        "name": "Krrzhd-0214",
        "uwp": "E5209EF-6",
        "allegiance": "Zh",
        "travel_zone": "R",
        "epoch": "Epoch I (Native Sophont)",
        "wave": "Native Sophont (Zhodani Interdiction)",
        "note": "SCG Native Sophont desert homeworld; fiercely xenophobic industrial natives under Zhodani Red Zone quarantine.",
    },
    "1725": {
        "name": "Subterra-1725",
        "uwp": "E223686-3",
        "allegiance": "Na",
        "epoch": "Epoch I (Native Sophont)",
        "wave": "Native Sophont",
        "note": "SCG Native Sophont world: cold low-gravity world with subterranean native sophonts.",
    },
    "1927": {
        "name": "Darr-Contact",
        "uwp": "E666988-7",
        "allegiance": "Na",
        "epoch": "Epoch I (Native Sophont) / -1050 Darrian Contact",
        "wave": "Native Sophont (Pre-Maghiz Darrian Contact)",
        "note": "SCG Native Sophont garden world preserving ancient star-charts from pre-Maghiz Darrian explorers (-1050).",
    },
    "2328": {
        "name": "Mirel-2328",
        "uwp": "D87A653-5",
        "allegiance": "Na",
        "epoch": "Epoch I (Native Sophont) / -1020 Darrian Contact",
        "wave": "Native Sophont (Pre-Maghiz Darrian Contact)",
        "note": "SCG Native Sophont waterworld whose oral traditions record the Darrian golden age before the Maghiz.",
    },
    "1726": {
        "name": "Relic-1726",
        "uwp": "X300000-0",
        "allegiance": "Na",
        "epoch": "Epoch I (-300,000 Ancient Ruins)",
        "wave": "Ancient Ruins",
        "note": "SCG Ancient Ruins site: airless world cratered during the Final War of the Ancients (-300,000).",
    },
    "2615": {
        "name": "Relic-2615",
        "uwp": "E300210-B",
        "allegiance": "Na",
        "epoch": "Epoch I (-300,000 Ancient Ruins)",
        "wave": "Ancient Ruins (Xenoarchaeological Outpost)",
        "note": "SCG Ancient Ruins site with a small Imperial/Darrian xenoarchaeological team excavating a vitrified city.",
    },
    "2740": {
        "name": "Relic-2740",
        "uwp": "X000000-0",
        "allegiance": "Na",
        "epoch": "Epoch I (-300,000 Ancient Ruins)",
        "wave": "Ancient Ruins",
        "note": "SCG Ancient Ruins asteroid belt containing shattered planetary fragments from an Ancient weapon test.",
    },
    "3006": {
        "name": "Nsobl-Relic",
        "uwp": "X100000-0",
        "allegiance": "Zh",
        "travel_zone": "R",
        "epoch": "Epoch I (-300,000 Ancient Ruins)",
        "wave": "Ancient Ruins (Zhodani Military Interdiction)",
        "note": "SCG Ancient Ruins site inside Zhodani space; strictly interdicted (Red Zone) by the Zhodani Consular Navy.",
    },
    "0104": {
        "name": "Chirper-0104",
        "uwp": "B35A515-E",
        "allegiance": "Zh",
        "epoch": "Epoch I (-300,000 Chirper Scatter)",
        "wave": "Scattered Settlement (Zhodani Science Corp)",
        "note": "SCG Scattered Settlement: 80% Chirper population administered by a TL14 Zhodani scientific directorate.",
    },
    "0408": {
        "name": "Zhod-Preserve",
        "uwp": "D997648-1",
        "allegiance": "Zh",
        "travel_zone": "R",
        "epoch": "Epoch I (-300,000 Minor Human)",
        "wave": "Scattered Settlement (Zhodani Protective Interdiction)",
        "note": "SCG Scattered Settlement: Iron-Age Minor Human race under Zhodani Red Zone protective interdiction.",
    },
    "0708": {
        "name": "Spartan-0708",
        "uwp": "B66A767-C",
        "allegiance": "Zh",
        "travel_zone": "A",
        "epoch": "Epoch II (-1800 Rule of Man)",
        "wave": "Scattered Settlement (Unabsorbed Solomani)",
        "note": "SCG Scattered Settlement: Lost Second Imperium Solomani waterworld under Zhodani military rule (Unabsorbed Amber Zone).",
    },
    "0935": {
        "name": "Oytrip-0935",
        "uwp": "C57488D-9",
        "allegiance": "Na",
        "travel_zone": "A",
        "epoch": "Epoch I (-300,000 Droyne)",
        "wave": "Scattered Settlement (Isolationist Droyne)",
        "note": "SCG Scattered Settlement: Isolationist Droyne community (Oytrip) guarding deep-time records in Subsector N.",
    },
    "1216": {
        "name": "Droyne-1216",
        "uwp": "B767837-9",
        "allegiance": "Zh",
        "epoch": "Epoch I (-300,000 Droyne)",
        "wave": "Scattered Settlement (Zhodani Full Member)",
        "note": "SCG Scattered Settlement: Droyne garden world integrated as a full member of the Zhodani Consulate.",
    },
    "1303": {
        "name": "Chirper-1303",
        "uwp": "X76737B-0",
        "allegiance": "Zh",
        "travel_zone": "R",
        "epoch": "Epoch I (-300,000 Chirper)",
        "wave": "Scattered Settlement (Zhodani Interdiction)",
        "note": "SCG Scattered Settlement: Primitive Chirper sanctuary world under Zhodani Red Zone interdiction.",
    },
    "2823": {
        "name": "Gvegh-2823",
        "uwp": "C699876-8",
        "allegiance": "Na",
        "travel_zone": "A",
        "epoch": "Epoch III (Vargr Scatter)",
        "wave": "Scattered Settlement (Vargr Balkanized World)",
        "note": "SCG Scattered Settlement: 80% Vargr population divided among warring charisma-pack states along the Spinward Main extension.",
    },
    # Zhodani Coreward Route Endpoints from Ziafrplians (SCG p. 27 & p. 63)
    "1102": {
        "name": "Ziafr-Gate West",
        "allegiance": "Zh",
        "bases": ["Zhodani Naval", "Zhodani Base"],
        "min_starport": "B",
        "epoch": "Epoch II (-3500)",
        "wave": "Zhodani Coreward Comm Spine",
        "note": "Canonical Zhodani communication/X-boat route endpoint linking Iakr (Foreven) to Ziafrplians Sector.",
    },
    "1701": {
        "name": "Ziafr-Gate North",
        "allegiance": "Zh",
        "bases": ["Zhodani Naval", "Zhodani Base"],
        "min_starport": "B",
        "epoch": "Epoch II (-3500)",
        "wave": "Zhodani Coreward Comm Spine",
        "note": "Canonical Zhodani communication/X-boat route endpoint linking Iakr (Foreven) to Ziafrplians Sector.",
    },
    "2602": {
        "name": "Ziafr-Gate Mid",
        "allegiance": "Zh",
        "bases": ["Zhodani Naval", "Zhodani Base"],
        "min_starport": "B",
        "epoch": "Epoch II (-3200)",
        "wave": "Zhodani Coreward Comm Spine",
        "note": "Canonical Zhodani communication/X-boat route endpoint linking Iakr (Foreven) to Ziafrplians Sector.",
    },
    "3201": {
        "name": "Ziafr-Gate East",
        "allegiance": "Zh",
        "bases": ["Zhodani Naval", "Zhodani Base"],
        "min_starport": "B",
        "epoch": "Epoch II (-3000)",
        "wave": "Zhodani Coreward Comm Spine",
        "note": "Canonical Zhodani communication/X-boat route endpoint on the Vilis/Ziafrplians corner.",
    },
    # Imperial Navy 'Droyne Cage' outpost opposite Andor & Candory (SCG p. 64)
    "3135": {
        "name": "Candory Watch",
        "allegiance": "Cs",
        "bases": ["Naval", "Scout"],
        "min_starport": "B",
        "epoch": "Epoch IV (670)",
        "wave": "Imperial Five Sisters Security Perimeter",
        "note": "Imperial Client State naval base completing the 3-parsec Imperial Navy 'cage' around the Droyne worlds of Andor and Candory in Five Sisters (SCG p. 64).",
    },
}


# ==============================================================================
# 5. HELPER FUNCTIONS FOR HEX GEOMETRY & SUBSECTOR MAPPING
# ==============================================================================

def hex_to_col_row(hex_coord: str) -> Tuple[int, int]:
    return int(hex_coord[:2]), int(hex_coord[2:])


def hex_to_subsector_code(hex_coord: str) -> str:
    col, row = hex_to_col_row(hex_coord)
    sub_col = (col - 1) // 8
    sub_row = (row - 1) // 10
    idx = sub_row * 4 + sub_col
    return chr(ord("A") + idx)


def parsec_distance(hex1: str, hex2: str) -> int:
    """Exact odd-q flat-topped Traveller hex grid distance in parsecs."""
    c1, r1 = hex_to_col_row(hex1)
    c2, r2 = hex_to_col_row(hex2)
    # Convert 1-based odd-q offset to cube coordinates
    q1 = c1 - 1
    q2 = c2 - 1
    row1 = r1 - 1
    row2 = r2 - 1
    x1 = q1
    z1 = row1 - (q1 - (q1 & 1)) // 2
    y1 = -x1 - z1
    x2 = q2
    z2 = row2 - (q2 - (q2 & 1)) // 2
    y2 = -x2 - z2
    return (abs(x1 - x2) + abs(y1 - y2) + abs(z1 - z2)) // 2


def get_settlement_wave_info(hex_coord: str) -> Tuple[int, str, str, str]:
    """
    Returns (population_dm, settlement_epoch, settlement_wave, default_allegiance)
    for any hex in Foreven according to the Sector Construction Guide Multipass rules
    (SCG pp. 24-27) and the five macro-historical epochs.
    """
    sub_code = hex_to_subsector_code(hex_coord)
    in_zh = hex_coord in FOREVEN_ZHODANI_HEXES

    # 1. Fixed systems override
    if hex_coord in FOREVEN_FIXED_SYSTEMS:
        spec = FOREVEN_FIXED_SYSTEMS[hex_coord]
        return (
            0,
            spec.get("epoch", "Epoch III"),
            spec.get("wave", "Canonical Anchor"),
            spec.get("allegiance", "Zh" if in_zh else "Na"),
        )

    # 2. Subsector J/C Barren Anomaly
    if hex_coord in SUBSECTOR_J_BARREN_ANOMALY:
        anom = SUBSECTOR_J_BARREN_ANOMALY[hex_coord]
        return (
            -12,
            "Epoch V (Anomalous Void)",
            "Subsector J Barren Anomaly",
            anom.get("allegiance", "Zh" if in_zh else "Na"),
        )

    # 3. Mature Zhodani Core (Subsectors A, B, C inside Zhodani border)
    if in_zh and sub_code in ("A", "B", "C"):
        return (
            0,
            "Epoch II (-4000 to -1000)",
            "Mature Zhodani Consulate Heartland",
            "Zh",
        )

    # 4. Zhodani-conquered Massina (Subsector D)
    if sub_code == "D":
        return (
            0,
            "Epoch III/IV (Pre-589 Imperial -> 604 Zhodani Conquest)",
            "Massina Frontier Wave (Zhodani Assimilation)",
            "Zh" if in_zh else "Na",
        )

    # 5. Zhodani Counter-Expansion into E, F, G (600-700)
    if sub_code in ("E", "F", "G"):
        return (
            -1,
            "Epoch IV (600–700)",
            "Zhodani Post-Frontier-War Thin Wave",
            "Zh" if in_zh else "Na",
        )

    # 6. Trailing Subsectors H (Fessor), L (Reidain), P (Urnian): >500 yr Imperial Thin Wave
    if sub_code in ("H", "L", "P"):
        # Systems near Hollis/Alenzar/Raschev/3135 often align as Imperial Client States
        col, row = hex_to_col_row(hex_coord)
        alleg = "Cs" if col >= 29 and row >= 21 else "Na"
        return (
            0,
            "Epoch III (200–589)",
            "Imperial Spinward Main Thin Wave",
            alleg,
        )

    # 7. Subsectors N & O (outside the 27 named Avalar systems, buffered by Avalar + Imperial wave)
    if sub_code in ("N", "O"):
        return (
            0,
            "Epoch IV (628–850)",
            "Avalar Ripple & Rimward Trade Buffer",
            "Na",
        )

    # 8. Isolated Spinward Shadow Region (Subsectors I, M, and western J/N)
    if sub_code in ("I", "M") or (sub_code == "J" and int(hex_coord[:2]) <= 12):
        return (
            -2,
            "Epoch V (800–1107)",
            "Isolated Spinward Backfill (Far Frontiers / Beyond)",
            "Na",
        )

    # 9. Remaining central frontier (Subsector K and eastern J)
    return (
        -1,
        "Epoch IV (620–750)",
        "Central Foreven Frontier Thin Wave",
        "Cs" if hex_coord in ("2623", "2724", "2822") else "Na",
    )


# ==============================================================================
# 6. NAMING POOLS BY CULTURAL / POLITY SPHERE
# ==============================================================================

ZHODANI_NAMES = [
    "Zhdovl", "Chlebl", "Tliavzh", "Krrzhd", "Vlazhdu", "Nsoblir", "Qlaqlech",
    "Zdefral", "Chiepavr", "Tlanzh", "Dravzhd", "Plesht", "Zhdikol", "Vrenzh",
    "Bliazh", "Tlovr", "Khezhda", "Shtebr", "Dlazh", "Zhdevra", "Flesht",
    "Nchaq", "Vlozh", "Zhdant", "Chlovr", "Tleshia", "Qrabl", "Zhdorv",
]

IMPERIAL_MARCHES_NAMES = [
    "Vanguard", "New Vilis", "Marches Reach", "Calandron", "Arcturus Gate",
    "Durendal", "Kestrel", "Bellerophon", "Caledon", "Highwatch", "Stirling",
    "Grendel", "Palamon", "Corinthia", "Aethelgard", "Valkyrie", "Tarsus",
    "Miremont", "Halcyon", "Castellan", "Ironwood", "Veridian", "Pendragon",
    "Oakhaven", "Montrose", "Dunbar", "Lismore", "Kintyre", "Galloway",
]

FRONTIER_NAMES = [
    "Driftmark", "Wayfarer", "Sable", "Cinderfall", "Khoros", "Nyx", "Vesper",
    "Solace", "Outreach", "Crossroads", "Talon", "Pyre", "Coldwater", "Mirage",
    "Ashfall", "beacon", "Riftward", "Perdition", "Glimmer", "Siren", "Anvil",
]


def _generate_contextual_name(hex_coord: str, allegiance: str, sub_code: str, rng: random.Random) -> str:
    if allegiance == "Zh" or sub_code in ("A", "B", "C", "E", "F"):
        stem = rng.choice(ZHODANI_NAMES)
        return f"{stem}-{hex_coord[:2]}" if rng.random() < 0.25 else stem
    elif allegiance == "Cs" or sub_code in ("H", "K", "L", "P"):
        stem = rng.choice(IMPERIAL_MARCHES_NAMES)
        return stem
    else:
        stem = rng.choice(FRONTIER_NAMES + IMPERIAL_MARCHES_NAMES)
        return stem


# ==============================================================================
# 7. SCG PHYSICAL & SOCIAL VARIANT GENERATORS + UWP PARSING
# ==============================================================================

def parse_uwp_str(uwp_str: str) -> UWP:
    clean = uwp_str.strip()
    sp = clean[0]
    sz = clean[1]
    at = clean[2]
    hy = clean[3]
    po = clean[4]
    go = clean[5]
    lw = clean[6]
    tl = clean.split("-")[1] if "-" in clean else clean[7]
    return UWP(
        starport=sp,
        size=sz,
        atmosphere=at,
        hydrographics=hy,
        population=po,
        government=go,
        law_level=lw,
        tech_level=tl,
    )


def min_survivable_tl(atm: int) -> int:
    """Minimum Tech Level for long-term environmental viability (SCG p. 21)."""
    if atm in (0, 1):
        return 8
    elif atm in (2, 3, 13, 14):
        return 5
    elif atm in (4, 7, 9):
        return 3
    elif atm == 10:
        return 8
    elif atm == 11:
        return 9
    elif atm == 12:
        return 10
    elif atm == 15:
        return 8
    return 0


def generate_scg_foreven_uwp(
    pop_dm: int,
    allegiance: str,
    is_barren_anomaly: bool = False,
    min_starport: Optional[str] = None,
) -> UWP:
    """
    Generates a Mainworld UWP using the exact Sector Construction Guide Foreven
    variants (SCG p. 16 & pp. 25-27):
    - Size: 2D-2 (on 10, roll 4+ to increase up to 15; clamped to 0..10 for standard UWP display)
    - Atmosphere: 2D-7 + Size (Size 2-4: DM-2; Size 1: DM-5; Size 0: 0)
    - Hydrographics: 2D-7 + Atmosphere (DM-4 if Atm 9+; Size 0-1: 0)
    - Population: 2D-2 + pop_dm
    - Environmental viability & Polity TL caps (Zhodani/General <= 14, Avalar <= 12).
    """
    uwp = UWP()

    # 1. Size
    size_val = Utils.D6(2) - 2
    if size_val == 0:
        atm_val = 0
        hyd_val = 0
    else:
        atm_val = Utils.D6(2) - 7 + size_val
        if size_val == 1:
            atm_val -= 5
        elif 2 <= size_val <= 4:
            atm_val -= 2
        atm_val = max(0, min(15, atm_val))

        if size_val <= 1:
            hyd_val = 0
        else:
            hyd_dm = -4 if atm_val >= 9 else 0
            hyd_val = max(0, min(10, Utils.D6(2) - 7 + atm_val + hyd_dm))

    if is_barren_anomaly or pop_dm <= -10:
        uwp.size = Utils.eHex(size_val)
        uwp.atmosphere = Utils.eHex(atm_val)
        uwp.hydrographics = Utils.eHex(hyd_val)
        uwp.population = "0"
        uwp.government = "0"
        uwp.law_level = "0"
        uwp.starport = "X"
        uwp.tech_level = "0"
        return uwp

    pop_val = max(0, min(10, Utils.D6(2) - 2 + pop_dm))
    if pop_val == 0:
        uwp.size = Utils.eHex(size_val)
        uwp.atmosphere = Utils.eHex(atm_val)
        uwp.hydrographics = Utils.eHex(hyd_val)
        uwp.population = "0"
        uwp.government = "0"
        uwp.law_level = "0"
        uwp.starport = "X"
        uwp.tech_level = "0"
        return uwp

    gov_val = min(15, generate_government(pop_val))
    law_val = min(15, generate_law_level(gov_val))
    sp_val = generate_starport(pop_val)

    if min_starport:
        order = ["X", "E", "D", "C", "B", "A"]
        if order.index(sp_val) < order.index(min_starport):
            sp_val = min_starport

    tl_val = generate_tech_level(sp_val, size_val, atm_val, hyd_val, pop_val)

    # Enforce SCG environmental survivability and polity TL caps (SCG p. 27)
    req_tl = min_survivable_tl(atm_val)
    max_tl = 12 if allegiance == "Av" else 14
    tl_val = min(max_tl, tl_val)

    if tl_val < req_tl:
        if allegiance in ("Zh", "Av", "Fe", "He", "Cs"):
            tl_val = req_tl
            if sp_val in ("X", "E"):
                sp_val = "D"
        else:
            # Outside polity support, non-survivable worlds become Pop 0 barren worlds
            uwp.size = Utils.eHex(size_val)
            uwp.atmosphere = Utils.eHex(atm_val)
            uwp.hydrographics = Utils.eHex(hyd_val)
            uwp.population = "0"
            uwp.government = "0"
            uwp.law_level = "0"
            uwp.starport = "X"
            uwp.tech_level = "0"
            return uwp

    uwp.size = Utils.eHex(size_val)
    uwp.atmosphere = Utils.eHex(atm_val)
    uwp.hydrographics = Utils.eHex(hyd_val)
    uwp.population = Utils.eHex(pop_val)
    uwp.government = Utils.eHex(gov_val)
    uwp.law_level = Utils.eHex(law_val)
    uwp.starport = sp_val
    uwp.tech_level = Utils.eHex(tl_val)
    return uwp


def _apply_uwp_to_mainworld(system: StellarSystem, target_uwp: UWP, mainworld_name: str):
    """Synchronizes a StellarSystem's mainworld with a target UWP and recomputes WBH geophysics."""
    terrestrials = [w for w in system.all_worlds if w.body_type == "Terrestrial"]
    if not terrestrials:
        # Ensure at least one terrestrial mainworld around primary star
        primary = system.primary_star
        hz = primary.hzco if primary else 3.0
        mw = PlanetaryBody(
            name=mainworld_name,
            parent_star_group=primary.designation if primary else "A",
            body_type="Terrestrial",
            orbit_num=round(hz, 2),
            orbit_au=Utils.orbit_to_au(hz),
            eccentricity=0.01,
            period_years=1.0,
            is_mainworld=True,
        )
        if primary:
            primary.orbiting_bodies.append(mw)
    else:
        # Pick terrestrial closest to HZCO as mainworld
        primary = system.primary_star
        hz = primary.hzco if primary else 3.0
        for w in terrestrials:
            w.is_mainworld = False
        mw = min(terrestrials, key=lambda w: abs(w.orbit_num - hz))
        mw.is_mainworld = True

    mw.name = mainworld_name
    mw.uwp = target_uwp
    mw.size_code = target_uwp.size
    mw.atmosphere_code = target_uwp.atmosphere
    mw.hydrographics_code = target_uwp.hydrographics
    mw.diameter_km = 0.0

    mw.mean_temperature = calculate_mean_temperature(mw, system)
    generate_geophysics(mw, system)
    generate_rotation_period(mw, system)
    mw.surface_features = generate_surface_features(mw)
    mw.life_details = generate_life(mw)
    generate_expanded_tech_matrix(mw.uwp, mw)
    generate_trade_codes(mw)
    mw.notes = [n for n in mw.notes if not n.startswith(("Cultural ", "Faction "))]
    generate_social_details(mw)
    assign_final_designations(system)


def _generate_bases_for_foreven_system(system: StellarSystem, rng: random.Random):
    """Applies SCG Foreven base generation rules (Zhodani, Avalar, Imperial Client, Independent)."""
    if system.bases:
        return
    mw = next((w for w in system.all_worlds if w.is_mainworld), None)
    if not mw:
        return
    port = mw.uwp.starport
    alleg = system.allegiance
    bases = []

    if alleg == "Zh":
        # Zhodani have no separate scout service; naval base automatically pairs with military base (SCG p. 27)
        if port in ("A", "B") and Utils.D6(2) >= 8:
            bases.extend(["Zhodani Naval", "Zhodani Base"])
    elif alleg == "Cs":
        if port == "A":
            if Utils.D6(2) >= 8:
                bases.append("Naval")
            if Utils.D6(2) >= 10:
                bases.append("Scout")
        elif port == "B":
            if Utils.D6(2) >= 8:
                bases.append("Naval")
            if Utils.D6(2) >= 8:
                bases.append("Scout")
        elif port in ("C", "D"):
            if Utils.D6(2) >= 8:
                bases.append("Scout")
    elif alleg in ("Fe", "Tl", "He"):
        if port in ("A", "B") and Utils.D6(2) >= 8:
            bases.append("Naval")
    else:
        # Independent trailing systems: half standard frequency (SCG p. 27)
        if system.subsector_code in ("H", "K", "L", "P") and rng.randint(1, 6) >= 4:
            if port in ("A", "B") and Utils.D6(2) >= 9:
                bases.append("Scout")
                system.allegiance = "Cs"
        if port in ("C", "D", "E") and Utils.D6(2) == 12:
            bases.append("Pirate")

    system.bases = bases


def _evaluate_travel_zone(system: StellarSystem):
    """Applies SCG p. 27 Amber/Red Travel Zone heuristics if not already set."""
    if system.travel_zone:
        return
    mw = next((w for w in system.all_worlds if w.is_mainworld), None)
    if not mw:
        return
    atm = Utils.from_eHex(mw.uwp.atmosphere)
    gov = Utils.from_eHex(mw.uwp.government)
    law = Utils.from_eHex(mw.uwp.law_level)

    if atm in (10, 11, 12) and mw.mean_temperature >= 320:
        system.travel_zone = "A"
    elif gov + law >= 20:
        system.travel_zone = "A"
    elif gov == 7 and Utils.from_eHex(mw.uwp.population) >= 6:
        system.travel_zone = "A"
    elif system.subsector_code == "D" and system.allegiance == "Zh" and gov in (6, 7):
        # Unabsorbed ex-Imperial colony in Massina
        system.travel_zone = "A"
        system.historical_notes.append("Unabsorbed ex-Imperial colony under Zhodani cultural corrective oversight.")


# ==============================================================================
# 8. EARTH-SIMILARITY INDEX (ESI) & CHRISTENING OF 'ERITH'
# ==============================================================================

def compute_earth_similarity_score(
    world: PlanetaryBody,
    system: StellarSystem,
    include_age_and_metallicity: bool = False,
) -> float:
    """
    Computes an Earth-Similarity Index (ESI) score for a terrestrial world.
    Earth benchmark: Size 8 (~12,742 km, 1.0 G), Atmosphere 6 (Standard),
    Hydrographics 7 (~70%), Mean Temp ~288 K (Temperate), G-type star,
    and (when include_age_and_metallicity=True) Phanerozoic age window
    (4.57 +/- 0.50 Gyr) and Solar metallicity ([Fe/H] = 0.00 dex).
    """
    if include_age_and_metallicity:
        return compute_coupled_earth_similarity_score(
            world, system, include_age_and_metallicity=True
        )
    if world.body_type != "Terrestrial":
        return -1e9
    size = Utils.from_eHex(world.uwp.size)
    atm = Utils.from_eHex(world.uwp.atmosphere)
    hyd = Utils.from_eHex(world.uwp.hydrographics)
    pop = Utils.from_eHex(world.uwp.population)
    if pop == 0 or size == 0:
        return -1e9

    score = 100.0
    score -= abs(size - 8) * 12.0
    if atm == 6:
        score += 20.0
    elif atm in (5, 8):
        score += 8.0
    else:
        score -= abs(atm - 6) * 15.0

    score -= abs(hyd - 7) * 8.0
    temp_k = world.mean_temperature if world.mean_temperature > 0 else 288.0
    score -= abs(temp_k - 288.0) * 0.4
    if world.gravity > 0:
        score -= abs(world.gravity - 1.0) * 15.0

    pstar = system.primary_star
    if pstar and pstar.spectral_type:
        if pstar.spectral_type.startswith("G"):
            score += 12.0
        elif pstar.spectral_type.startswith(("F", "K")):
            score += 5.0

    return score


def designate_erith(sector: Sector) -> str:
    """
    Finds the most Earth-like planet across all generated non-fixed systems in
    Foreven and christens it 'Erith', enriching it with canonical Erith settlements.
    """
    best_hex = ""
    best_world: Optional[PlanetaryBody] = None
    best_score = -1e9

    for hex_coord, system in sector.systems.items():
        if hex_coord in FOREVEN_FIXED_SYSTEMS or hex_coord in SUBSECTOR_J_BARREN_ANOMALY:
            continue
        mw = next((w for w in system.all_worlds if w.is_mainworld), None)
        if not mw:
            continue
        score = compute_earth_similarity_score(mw, system)
        if score > best_score:
            best_score = score
            best_hex = hex_coord
            best_world = mw

    if best_hex and best_world:
        sys = sector.systems[best_hex]
        sys.name = "Erith"
        best_world.name = "Erith"
        # Ensure Earth-like physical parameters (Size 8, Atm 6, Hyd 7, Temperate ~288K)
        best_world.uwp.size = "8"
        best_world.uwp.atmosphere = "6"
        best_world.uwp.hydrographics = "7"
        best_world.size_code = "8"
        best_world.atmosphere_code = "6"
        best_world.hydrographics_code = "7"
        best_world.diameter_km = 12742.0
        best_world.gravity = 1.0
        best_world.density = 1.0
        best_world.mean_temperature = 288.0
        best_world.climate_zone = "Temperate"
        generate_trade_codes(best_world)
        generate_expanded_tech_matrix(best_world.uwp, best_world)
        erith_note = (
            "Erith (Earth-analogue of Foreven): The single most Earth-like terrestrial "
            "garden world in the Foreven Sector (12,742 km diameter, 1.0 G, standard O2/N2 "
            "atmosphere, 70% ocean cover, 288 K mean temperature). Major settlements on "
            "its principal temperate island-continent include Presport, Melgate, Calling, "
            "Tennerport, Gotoe, Eastport, Parkhead, and Bradbeck."
        )
        best_world.notes.insert(0, erith_note)
        sys.historical_notes.append(erith_note)
        sector.erith_hex = best_hex

    return best_hex


# ==============================================================================
# 9. SOPHONTS & POLITIES REGISTRATION FOR FOREVEN (1107)
# ==============================================================================

def build_foreven_sophonts() -> Dict[str, Sophont]:
    return {
        "1212": Sophont(
            name="Zhodani (Humaniti)",
            homeworld_hex="1212",
            is_major=True,
            morphology="Bilateral (Tall Humaniti)",
            limbs="4 limbs (2 arms, 2 legs)",
            sensory_organs=["Standard Human Senses", "Trained Psionic Talents"],
            reproduction="Sexual (Dimorphic)",
            diet="Omnivore",
            psychology="Harmonious, three-caste psionic society (Nobles, Intendants, Proles)",
            evolutionary_track="Zhdant native / settled Iakr Sector since -4000",
            history_summary="Rulers of the Zhodani Consulate's Iakr Sector (Iadr Nsobl Province) from Zdovesil (1212).",
        ),
        "1628": Sophont(
            name="Heptamorphs (Khept-7 Hivemind)",
            homeworld_hex="1628",
            is_major=False,
            morphology="Radial Heptamorphic Symmetry (7-fold chitinous-neural nodes)",
            limbs="7 articulated locomotory/manipulator appendages with 7 compound-psionic ocelli",
            sensory_organs=[
                "7-Band Ultraviolet/Infrared Ocelli",
                "Heptagonal Synaptic Telepathic Lattice",
                "Magnetoreceptive Resonance",
            ],
            reproduction="Spore-brood eusocial gestation directed by Queen-Nexus nodes",
            diet="Chemo-organic & biosphere-harvesting",
            psychology="Collective distributed hivemind consciousness; views individualist sophonts as chaotic noise",
            evolutionary_track="Dense exotic atmosphere (Atm A) pressure-reefs of Septima Prime (1628)",
            history_summary=(
                "Evolved on Septima Prime (1628); harvested the worlds of northern Subsector J "
                "(creating the Subsector J Barren Anomaly) to grow living spore-dreadnoughts, and "
                "launched the Septiman War against the Avalar Consulate in 1104."
            ),
        ),
        "0131": Sophont(
            name="Uplifted Terran Cats (Felis catus sapiens)",
            homeworld_hex="0131",
            is_major=False,
            morphology="Bilateral Digitigrade Felid (5–8 kg agile quadrupedal/bipedal form)",
            limbs="4 limbs (forepaws with engineered opposable thumbs, hind leaping legs, balance tail)",
            sensory_organs=[
                "Tapetum Lucidum Low-Light Vision",
                "Ultrasonic Pinnae Hearing",
                "Vibrissae Micro-Airflow Tactile Array",
            ],
            reproduction="Sexual (Dimorphic, litter size 1–3)",
            diet="Obligate Carnivore (cultured gourmet protein & live-hunt preserves)",
            psychology="Fiercely independent, intensely curious, nocturnal-crepuscular, high-reflex astrogators",
            evolutionary_track="Genetically uplifted on Terra from Felis catus during the Rule of Man (-1851)",
            history_summary=(
                "Arrived aboard the Rule of Man seedship Caelum Felis in -1851; established the "
                "high-tech Chatelaine of Bastet (0131, 0232, 0332, 0431, 0825) in spinward-rimward Foreven."
            ),
        ),
        "2835": Sophont(
            name="Issugur / Periannath (Halflings - Homo sapiens parvulus)",
            homeworld_hex="2835",
            is_major=False,
            morphology="Bilateral Diminutive Humaniti (0.95–1.10 m tall, furry leathery soles)",
            limbs="4 limbs (2 nimble arms, 2 unshod Tough-soled legs)",
            sensory_organs=["Acute Hearing", "Quiet-Step Proprioception", "Natural Psionic Null-Resonance"],
            reproduction="Sexual (Dimorphic)",
            diet="Omnivore (Agrarian gourmet; seven traditional meals per day)",
            psychology="Peaceable, clannish, pastoral, burrow-dwelling, surprisingly resilient under crisis",
            evolutionary_track="Transplanted from Pleistocene Terra by the Ancients (~-300,000) to Parthinia (3018) and The Shire (2835)",
            history_summary=(
                "Ancient-transplanted Minor Human Race preserved on Parthinia (3018) and thriving in "
                "autonomous agrarian shires at The Shire (2835), Bywater (2834), and Bucklebury (2935)."
            ),
        ),
        "0720": Sophont(
            name="Tlinzha",
            homeworld_hex="0720",
            is_major=False,
            morphology="Bilateral Two-Headed Octopod (U-shaped 2m scaled body)",
            limbs="8 limbs (4 central walking legs, 2 arms at Red-Sun Head, 2 arms at White-Sun Head)",
            sensory_organs=[
                "Red-Head Armored Infrared Eyes",
                "White-Head Retractable Stalked UV-Visual Eyes",
                "Synaesthetic Olfactory-Auditory Pores",
            ],
            reproduction="Asexual Parthenogenic Budding",
            diet="Pack Scavenger (governed by the sacred Protocols of the Consumption of Meats)",
            psychology="Territorial, ritualistic, dual-hemisphere vigilance; suspicious of offworlders",
            evolutionary_track="Monsoon uplands of binary-star Tlesho (0720, F5 V + M3 V flare star)",
            history_summary=(
                "Contacted by Zhodani in -4880; reverse-engineered Jump-1 drive from a wrecked Imperial "
                "trader by 300; rule the xenophobic 4-system Tlesho Union (0720, 0819, 0820, 0919)."
            ),
        ),
    }


def build_foreven_polities(sector: Sector) -> List[Polity]:
    polities = [
        Polity(
            name="Zhodani Consulate (Iakr Province)",
            capital_hex="1212",
            allegiance_code="Zh",
            polity_type="Major Race Polity",
            defense_index=10,
        ),
        Polity(
            name="Avalar Consulate",
            capital_hex="1636",
            allegiance_code="Av",
            polity_type="Pocket Empire (Zhodani Client State)",
            defense_index=8,
        ),
        Polity(
            name="Heptarchy of Septima (Heptamorphoid Hivemind)",
            capital_hex="1628",
            allegiance_code="He",
            polity_type="Xenomorphic Hivemind Polity (At War with Avalar)",
            defense_index=8,
        ),
        Polity(
            name="Chatelaine of Bastet (Uplifted Terran Cats)",
            capital_hex="0131",
            allegiance_code="Fe",
            polity_type="Uplift Freehold",
            defense_index=6,
        ),
        Polity(
            name="Periannath Shires & Issugur Commonwealth",
            capital_hex="2835",
            allegiance_code="Hl",
            polity_type="Minor Human Agrarian Commonwealth",
            defense_index=4,
        ),
        Polity(
            name="Tlesho Union (Tlinzha)",
            capital_hex="0720",
            allegiance_code="Tl",
            polity_type="Minor Race Pocket Empire",
            defense_index=6,
        ),
        Polity(
            name="Imperial Client States (Spinward Marches Sphere)",
            capital_hex="2523",
            allegiance_code="Cs",
            polity_type="Imperial Client Network",
            defense_index=7,
        ),
    ]

    by_code = {p.allegiance_code: p for p in polities}
    for hex_coord, sys in sector.systems.items():
        if sys.allegiance in by_code:
            by_code[sys.allegiance].controlled_systems.append(hex_coord)

    return polities


# ==============================================================================
# 10. FULL FOREVEN SECTOR GENERATOR (1107)
# ==============================================================================

def generate_foreven_sector(seed: int = 1107) -> Tuple[Sector, List[Sector]]:
    """
    Deterministically generates the complete 32x40 Foreven Sector (in Year 1107)
    across all 358 canonical star hexes, complete with every system's primary and
    companion stars, gas giants, planetoid belts, secondary terrestrial worlds,
    and moons, plus the 16 subsector objects (A to P).
    """
    rng = random.Random(seed)
    sector = Sector(
        name="Foreven Sector (Iakr - 1107)",
        width=32,
        height=40,
        subsector_names=dict(FOREVEN_SUBSECTORS),
        macro_history=list(FOREVEN_MACRO_HISTORY),
    )
    sector.native_sophonts = build_foreven_sophonts()
    sector.settlement_waves = [
        Wave("Zhodani Coreward Heartland", "1212", 50, "thick", 0.5),
        Wave("Imperial Spinward Main Thin Wave", "3225", 6, "thin", 3.0),
        Wave("Zhodani Post-Frontier-War Counter-Wave", "1612", 5, "thin", 2.5),
        Wave("Avalar Consulate Expansion Ripple", "1636", 5, "thick", 2.0),
        Wave("Heptamorphoid Hivemind Swarm", "1628", 1, "thick", 3.0),
        Wave("Chatelaine of Bastet Uplift Freehold", "0131", 8, "thick", 1.0),
    ]

    used_names = set()

    for idx, hex_coord in enumerate(FOREVEN_RESERVE_HEXES):
        # Seed deterministically per hex so every hex in Foreven is 100% reproducible
        hex_seed = (seed * 1_000_003 + int(hex_coord) * 7919 + idx) & 0x7FFFFFFF
        random.seed(hex_seed)
        hex_rng = random.Random(hex_seed)

        sub_code = hex_to_subsector_code(hex_coord)
        sub_name = FOREVEN_SUBSECTORS[sub_code]
        pop_dm, epoch, wave_name, default_alleg = get_settlement_wave_info(hex_coord)

        fixed = FOREVEN_FIXED_SYSTEMS.get(hex_coord)
        anomaly = SUBSECTOR_J_BARREN_ANOMALY.get(hex_coord)

        if fixed and "name" in fixed:
            sys_name = fixed["name"]
        elif anomaly and "name" in anomaly:
            sys_name = anomaly["name"]
        else:
            candidate = _generate_contextual_name(hex_coord, default_alleg, sub_code, hex_rng)
            if candidate in used_names:
                candidate = f"{candidate} {hex_coord}"
            sys_name = candidate
        used_names.add(sys_name)

        # Generate full WBH stellar system (stars, orbits, gas giants, belts, secondary worlds, moons)
        system = generate_full_system(name=sys_name, population_dm=max(-4, pop_dm))
        system.hex_coord = hex_coord
        system.subsector_code = sub_code
        system.subsector_name = sub_name
        system.settlement_epoch = epoch
        system.settlement_wave = wave_name
        system.population_dm = pop_dm
        system.allegiance = default_alleg

        # Determine target Mainworld UWP
        if fixed and "uwp" in fixed:
            target_uwp = parse_uwp_str(fixed["uwp"])
        elif anomaly and "uwp" in anomaly:
            target_uwp = parse_uwp_str(anomaly["uwp"])
        else:
            min_sp = fixed.get("min_starport") if fixed else None
            target_uwp = generate_scg_foreven_uwp(
                pop_dm=pop_dm,
                allegiance=default_alleg,
                is_barren_anomaly=(anomaly is not None),
                min_starport=min_sp,
            )

        _apply_uwp_to_mainworld(system, target_uwp, sys_name)

        # Apply canonical stellar / PBG / base overrides where specified
        if fixed:
            if "primary_spectral" in fixed and system.primary_star:
                system.primary_star.spectral_type = fixed["primary_spectral"]
            if "pbg" in fixed:
                system.pbg = fixed["pbg"]
                system.planetoid_belt_count = int(fixed["pbg"][1])
                system.gas_giant_count = int(fixed["pbg"][2])
            if "bases" in fixed:
                system.bases = list(fixed["bases"])
            if "travel_zone" in fixed:
                system.travel_zone = fixed["travel_zone"]
            if "note" in fixed:
                system.historical_notes.append(fixed["note"])
                mw = next((w for w in system.all_worlds if w.is_mainworld), None)
                if mw:
                    mw.notes.insert(0, fixed["note"])

        if anomaly:
            if anomaly.get("no_gas_giant"):
                system.gas_giant_count = 0
                for st in system.stars:
                    st.orbiting_bodies = [b for b in st.orbiting_bodies if b.body_type != "Gas Giant"]
            system.travel_zone = "A"
            system.historical_notes.append(anomaly["note"])
            mw = next((w for w in system.all_worlds if w.is_mainworld), None)
            if mw:
                mw.notes.insert(0, anomaly["note"])

        # Compute PBG string if not preset
        if not system.pbg:
            mw = next((w for w in system.all_worlds if w.is_mainworld), None)
            pop_val = Utils.from_eHex(mw.uwp.population) if mw else 0
            pop_mult = hex_rng.randint(1, 9) if pop_val > 0 else 0
            b_cnt = min(9, system.planetoid_belt_count)
            g_cnt = min(9, system.gas_giant_count)
            system.pbg = f"{pop_mult}{b_cnt}{g_cnt}"

        _generate_bases_for_foreven_system(system, hex_rng)
        _evaluate_travel_zone(system)
        calculate_stellar_metallicity(system)
        system.historical_notes.append(
            f"Macro-History: {system.settlement_epoch} — {system.settlement_wave} (Pop DM {system.population_dm:+d})."
        )

        sector.systems[hex_coord] = system

    # Evaluate natural Solar Analogues, Solar System Architectural Analogues,
    # and Age/Metallicity-Coupled Earth Analogues across all 358 systems
    sector.solar_analogues = find_solar_analogues(sector, top_n=10)
    if sector.solar_analogues:
        sector.solar_analogue_hex = sector.solar_analogues[0]["hex_coord"]
        top_sol = sector.solar_analogues[0]
        sol_sys = sector.systems[sector.solar_analogue_hex]
        sol_sys.historical_notes.append(
            f"Closest Solar Analogue in Foreven ({top_sol['category']}, Score {top_sol['score']}): "
            f"{top_sol['spectral_type']} primary ({top_sol['mass']} M_sun, {top_sol['luminosity']} L_sun, "
            f"{top_sol['temp_k']} K), Age {top_sol['age_gyr']} Gyr ({top_sol['geological_epoch']}), "
            f"Metallicity [Fe/H] = {top_sol['metallicity_feh']:+.2f} dex."
        )

    sector.solar_system_analogues = find_solar_system_analogues(sector, top_n=10)
    if sector.solar_system_analogues:
        sector.solar_system_analogue_hex = sector.solar_system_analogues[0]["hex_coord"]
        top_ss = sector.solar_system_analogues[0]
        ss_sys = sector.systems[sector.solar_system_analogue_hex]
        ss_sys.historical_notes.append(
            f"Closest Solar System Architectural Analogue in Foreven (Score {top_ss['score']}): "
            f"{top_ss['inner_terrestrial_count']} inner rocky planets, 0 inner gas giants, "
            f"{top_ss['outer_gas_giant_count']} outer gas giants, and {top_ss['planetoid_belt_count']} planetoid belts "
            f"around a {top_ss['primary_star']} primary."
        )

    sector.earth_analogues = find_earth_analogues(
        sector, top_n=10, include_age_and_metallicity=True, include_secondary_worlds=True
    )

    # Christen the single most Earth-like planet 'Erith'
    designate_erith(sector)

    # Build Polities & Sector-Wide Trade / Comm Routes
    sector.polities = build_foreven_polities(sector)
    _calculate_foreven_routes(sector)

    # Partition into the 16 standard 8x10 Subsectors (A through P)
    subsectors = _partition_into_subsectors(sector)

    return sector, subsectors


_FOREVEN_NEIGHBOR_PAIRS: List[Tuple[str, str, int]] = []
for _i in range(len(FOREVEN_RESERVE_HEXES)):
    _h1 = FOREVEN_RESERVE_HEXES[_i]
    for _j in range(_i + 1, len(FOREVEN_RESERVE_HEXES)):
        _h2 = FOREVEN_RESERVE_HEXES[_j]
        _d = parsec_distance(_h1, _h2)
        if _d <= 2:
            _FOREVEN_NEIGHBOR_PAIRS.append((_h1, _h2, _d))


def _calculate_foreven_routes(sector: Sector):
    """
    Calculates both Jump-1 and key Jump-2 trade/military/comm routes across Foreven,
    respecting the Tlinzha chokepoint, the Avalar–Heptamorph war front, and the
    Spinward Main extension.
    """
    sp_map = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1, "X": 0}
    wtn_by_hex: Dict[str, float] = {}
    for h, s in sector.systems.items():
        mw = next((w for w in s.all_worlds if w.is_mainworld), None)
        if mw:
            wtn_by_hex[h] = sp_map.get(mw.uwp.starport, 0) + Utils.from_eHex(mw.uwp.population) / 2.0

    for h1, h2, dist in _FOREVEN_NEIGHBOR_PAIRS:
        if h1 not in wtn_by_hex or h2 not in wtn_by_hex:
            continue
        s1 = sector.systems[h1]
        s2 = sector.systems[h2]

        # No peaceful trade routes across hostile Heptamorph or Tlinzha borders
        if (s1.allegiance == "He") != (s2.allegiance == "He"):
            continue
        if (s1.allegiance == "Tl") != (s2.allegiance == "Tl"):
            continue

        # Same-polity clusters connect at Jump-1/2
        same_polity = (s1.allegiance == s2.allegiance) and (
            s1.allegiance in ("Zh", "Av", "He", "Fe", "Hl", "Tl", "Cs")
        )
        trade_score = wtn_by_hex[h1] + wtn_by_hex[h2]

        if dist == 1:
            if same_polity and trade_score >= 7.0:
                rtype = "major" if trade_score >= 11.5 else "minor"
                sector.routes.append((h1, h2, rtype))
            elif trade_score >= 10.0:
                rtype = "major" if trade_score >= 13.0 else "minor"
                sector.routes.append((h1, h2, rtype))
        elif dist == 2 and same_polity and trade_score >= 11.0:
            sector.routes.append((h1, h2, "minor"))


def _partition_into_subsectors(sector: Sector) -> List[Sector]:
    """Splits the 32x40 Foreven Sector into 16 8x10 Subsector objects (A to P) with local coordinates."""
    subsectors: List[Sector] = []
    for sub_row in range(4):
        for sub_col in range(4):
            idx = sub_row * 4 + sub_col
            letter = chr(ord("A") + idx)
            sub_name = FOREVEN_SUBSECTORS[letter]
            sub = Sector(
                name=f"Subsector {letter}: {sub_name}",
                width=8,
                height=10,
                subsector_names={letter: sub_name},
                erith_hex=sector.erith_hex,
            )

            col_min = sub_col * 8 + 1
            col_max = col_min + 7
            row_min = sub_row * 10 + 1
            row_max = row_min + 9

            global_to_local = {}
            for hex_coord, sys in sector.systems.items():
                c, r = hex_to_col_row(hex_coord)
                if col_min <= c <= col_max and row_min <= r <= row_max:
                    lc = c - col_min + 1
                    lr = r - row_min + 1
                    local_hex = f"{lc:02d}{lr:02d}"
                    sub.systems[local_hex] = sys
                    global_to_local[hex_coord] = local_hex

            for h1, h2, rtype in sector.routes:
                if h1 in global_to_local and h2 in global_to_local:
                    sub.routes.append((global_to_local[h1], global_to_local[h2], rtype))

            subsectors.append(sub)

    return subsectors
