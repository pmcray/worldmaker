"""
Solar Analogue, Solar System Architectural Analogue, and Age/Metallicity-Coupled
Earth Analogue Evaluation for Traveller Stellar Systems and Sectors.

Benchmarks:
- Sol: Spectral Type G2 V (single star), Mass 1.00 M_sun, Luminosity 1.00 L_sun,
  Effective Temp 5772 K, Diameter 1.00 D_sun, Age 4.57 Gyr, Metallicity [Fe/H] = 0.00 dex.
- Earth Phanerozoic Habitability Window: 4.57 Gyr +/- 0.50 Gyr (4.07 to 5.07 Gyr).
  * 4.0 Gyr ago (< 0.6 Gyr, Hadean): Magma ocean / heavy bombardment, steam-CO2 atmosphere.
  * 2.5-4.0 Gyr ago (0.6-2.4 Gyr, Archean): Anoxic N2-CO2-CH4 atmosphere, microbial life only.
  * 0.5-2.1 Gyr ago (2.4-4.07 Gyr, Proterozoic): Low O2 (<1-10% PAL), pre-vascular land biosphere.
  * Present +/- 500 Myr (4.07-5.07 Gyr, Phanerozoic): Breathable N2/O2 atmosphere, complex life.
  * > +500 Myr from now (> 5.07 Gyr for 1 M_sun): Main-sequence brightening (+10%/Gyr) triggers
    carbonate-silicate CO2 starvation and moist/runaway greenhouse ocean loss.
- Solar System Orbital Architecture:
  * Inner Terrestrial Zone (<= HZCO + 1.15, ~0.35-1.7 AU): 4 rocky planets (Mercury 0.39 AU / Orbit 1.0,
    Venus 0.72 AU / Orbit 2.1, Earth 1.00 AU / Orbit 3.0, Mars 1.52 AU / Orbit 3.9) and 0 inner gas giants.
  * Frost Line / Main Belt (~2.2-3.6 AU, Orbit ~4.5-5.5): Planetoid belt separating rocky and Jovian zones.
  * Outer Gas Giant Zone (> HZCO + 1.15, ~2.0-35 AU): 4 gas/ice giants (Jupiter 5.2 AU / Orbit 6.0,
    Saturn 9.5 AU / Orbit 6.9, Uranus 19.2 AU / Orbit 8.0, Neptune 30.1 AU / Orbit 8.5) + Kuiper Belt (~30-50 AU).
"""

import math
import random
from typing import Dict, List, Any, Optional, Tuple

from .classes import Sector, StellarSystem, Star, PlanetaryBody
from .utils import Utils


SOL_BENCHMARK = {
    "spectral_type": "G2 V",
    "mass": 1.00,
    "luminosity": 1.00,
    "temp_k": 5772.0,
    "diameter": 1.00,
    "age_gyr": 4.57,
    "age_window_half_width_gyr": 0.50,  # 4.07 to 5.07 Gyr (+/- 500 Myr)
    "metallicity_feh": 0.00,
    "hzco_orbit": 3.00,
    "hzco_au": 1.00,
}

SOL_PLANET_SLOTS = [
    {"name": "Mercury", "body_type": "Terrestrial", "orbit_num": 1.0, "au": 0.39, "delta_hzco": -2.0},
    {"name": "Venus", "body_type": "Terrestrial", "orbit_num": 2.1, "au": 0.72, "delta_hzco": -0.9},
    {"name": "Earth", "body_type": "Terrestrial", "orbit_num": 3.0, "au": 1.00, "delta_hzco": 0.0},
    {"name": "Mars", "body_type": "Terrestrial", "orbit_num": 3.9, "au": 1.52, "delta_hzco": 0.9},
    {"name": "Main Asteroid Belt", "body_type": "Planetoid Belt", "orbit_num": 5.0, "au": 2.80, "delta_hzco": 2.0},
    {"name": "Jupiter", "body_type": "Gas Giant", "orbit_num": 6.0, "au": 5.20, "delta_hzco": 3.0},
    {"name": "Saturn", "body_type": "Gas Giant", "orbit_num": 6.9, "au": 9.54, "delta_hzco": 3.9},
    {"name": "Uranus", "body_type": "Gas Giant", "orbit_num": 8.0, "au": 19.20, "delta_hzco": 5.0},
    {"name": "Neptune", "body_type": "Gas Giant", "orbit_num": 8.5, "au": 30.06, "delta_hzco": 5.5},
    {"name": "Kuiper Belt", "body_type": "Planetoid Belt", "orbit_num": 9.0, "au": 39.50, "delta_hzco": 6.0},
]


def calculate_stellar_metallicity(system: StellarSystem) -> float:
    """
    Calculates and assigns stellar metallicity [Fe/H] in dex (where Sol = 0.00)
    using the Galactic thin/thick-disk age-metallicity relation and the
    Fischer & Valenti (2005) gas-giant planet-metallicity correlation.
    Uses a local seeded RNG so global dice roll sequences remain untouched.
    """
    pstar = system.primary_star
    sp_str = pstar.spectral_type if pstar else "M0 V"
    seed_key = f"{system.name}_{sp_str}_{system.age_gyr}"
    rng = random.Random(seed_key)

    age = system.age_gyr if system.age_gyr > 0 else 4.57
    # Galactic thin-disk age-metallicity relation:
    # At age = 4.57 Gyr, solar-neighborhood mean [Fe/H] is ~ -0.02 to -0.05 dex;
    # older thick-disk stars (> 9 Gyr) drop steeply toward metal-poor values.
    mean_feh = 0.12 - 0.030 * age
    if age > 9.0:
        mean_feh -= 0.085 * (age - 9.0)

    # Planet-metallicity correlation: gas-giant-rich systems are metal-enriched
    if system.gas_giant_count >= 3:
        mean_feh += 0.06
    elif system.gas_giant_count >= 1:
        mean_feh += 0.02
    else:
        mean_feh -= 0.05

    feh = round(max(-1.50, min(0.50, rng.gauss(mean_feh, 0.14))), 2)
    system.metallicity_feh = feh
    for star in system.stars:
        star.metallicity_feh = feh
    return feh


def evaluate_planetary_age_habitability(age_gyr: float, star_mass: float = 1.0) -> Dict[str, Any]:
    """
    Evaluates a terrestrial world's evolutionary/geological epoch and habitability
    factor as a function of system age (Gyr) and host star mass (M_sun).

    Reflects that Earth wasn't an Earth-like garden world 4 Gyr ago (Hadean/Archean)
    or even 500 Myr ago (late Proterozoic / pre-vascular land biosphere), and won't
    be in +500 Myr as main-sequence brightening triggers a moist/runaway greenhouse.
    """
    sol_age = SOL_BENCHMARK["age_gyr"]
    half_win = SOL_BENCHMARK["age_window_half_width_gyr"]
    win_min = sol_age - half_win  # 4.07 Gyr
    win_max = sol_age + half_win  # 5.07 Gyr

    # Main-sequence lifetime scales roughly as 10 * M^-2.5 Gyr.
    # For stars >= 1.0 M_sun, brightening happens faster; for lower-mass stars,
    # brightening is slower, though tectonic/radiogenic heat & oxygenation still
    # bound the optimal Earth-like window around ~4.0-5.2 Gyr.
    ms_lifespan_gyr = 10.0 / (max(0.1, star_mass) ** 2.5)
    effective_upper_win = min(win_max, 0.51 * ms_lifespan_gyr) if star_mass >= 1.0 else win_max

    age_delta = age_gyr - sol_age
    in_earth_window = (win_min <= age_gyr <= effective_upper_win)

    if age_gyr < 0.6:
        epoch = "Hadean (Magma Ocean / Heavy Bombardment)"
        habitability_factor = 0.0
        age_score_adj = -45.0
    elif age_gyr < 2.4:
        epoch = "Archean (Anoxic N2-CO2-CH4 / Microbial Only)"
        habitability_factor = 0.15
        age_score_adj = -30.0
    elif age_gyr < win_min:
        epoch = "Proterozoic (Low-O2 Pre-Cambrian / Pre-Land Flora)"
        frac = (age_gyr - 2.4) / max(0.1, win_min - 2.4)
        habitability_factor = round(0.35 + 0.40 * frac, 2)
        age_score_adj = -22.0 + 16.0 * frac
    elif age_gyr <= effective_upper_win:
        epoch = "Phanerozoic (Earth-Analogue Breathable Window)"
        dist_from_sol = abs(age_gyr - sol_age)
        habitability_factor = round(1.0 - 0.15 * (dist_from_sol / half_win), 2)
        age_score_adj = 25.0 - dist_from_sol * 16.0
    elif age_gyr <= ms_lifespan_gyr:
        epoch = "Post-Phanerozoic (Super-Greenhouse / Silicate Weathering Breakdown)"
        over_gyr = age_gyr - effective_upper_win
        habitability_factor = round(max(0.05, 0.70 - 0.12 * over_gyr), 2)
        age_score_adj = -8.0 - over_gyr * 9.0
    else:
        epoch = "Post-Main-Sequence (Stellar Giant / Degenerate Remnant)"
        habitability_factor = 0.0
        age_score_adj = -50.0

    return {
        "age_gyr": round(age_gyr, 3),
        "age_delta_from_earth_gyr": round(age_delta, 3),
        "in_earth_age_window": in_earth_window,
        "epoch": epoch,
        "habitability_factor": habitability_factor,
        "age_score_adjustment": round(age_score_adj, 2),
        "ms_lifespan_gyr": round(ms_lifespan_gyr, 2),
    }


def _parse_spectral_code(spectral_type: str) -> Tuple[str, int, str]:
    """Parses 'G2 V' into ('G', 2, 'V')."""
    if not spectral_type:
        return ("M", 5, "V")
    parts = spectral_type.strip().split()
    sp = parts[0]
    lum_class = parts[1] if len(parts) > 1 else "V"
    s_class = sp[0] if sp else "M"
    s_sub = int(sp[1:]) if len(sp) > 1 and sp[1:].isdigit() else 5
    return (s_class, s_sub, lum_class)


def compute_solar_analogue_score(system: StellarSystem) -> Dict[str, Any]:
    """
    Computes a comprehensive Solar Analogue score for a StellarSystem, comparing
    its primary star and multiplicity against Sol across:
    1. Spectral Type & Subtype (G2) and Luminosity Class (V)
    2. Stellar Mass (1.00 M_sun), Effective Temperature (5772 K), Luminosity (1.00 L_sun)
    3. System Age (4.57 Gyr, with explicit bonus for the 4.07-5.07 Gyr Earth window)
    4. Stellar Metallicity ([Fe/H] = 0.00 dex)
    5. Multiplicity (Single star vs. binary/trinary companions)
    """
    pstar = system.primary_star
    if not pstar:
        return {"score": -1e9, "hex_coord": system.hex_coord, "name": system.name}

    if system.metallicity_feh == 0.0 and all(s.metallicity_feh == 0.0 for s in system.stars):
        calculate_stellar_metallicity(system)

    s_class, s_sub, lum_class = _parse_spectral_code(pstar.spectral_type)
    non_comp_stars = [s for s in system.stars if not s.is_composite]
    multiplicity = len(non_comp_stars)

    score = 100.0

    # 1. Spectral & Luminosity Class (Sol = G2 V -> index 42)
    if lum_class != "V":
        score -= 55.0
    type_order = {"O": 0, "B": 1, "A": 2, "F": 3, "G": 4, "K": 5, "M": 6}
    sol_idx = 42  # G2
    star_idx = type_order.get(s_class, 6) * 10 + s_sub
    spectral_sub_diff = abs(star_idx - sol_idx)
    spectral_penalty = spectral_sub_diff * 2.5
    score -= spectral_penalty

    # 2. Mass (1.00 M_sun), Temp (5772 K), Luminosity (1.00 L_sun), Diameter (1.00 D_sun)
    mass_diff = abs(pstar.mass - SOL_BENCHMARK["mass"])
    temp_diff = abs(pstar.temp_k - SOL_BENCHMARK["temp_k"])
    lum_diff = abs(pstar.luminosity - SOL_BENCHMARK["luminosity"])
    physical_penalty = (mass_diff * 25.0) + (temp_diff / 100.0 * 1.5) + (lum_diff * 12.0)
    score -= physical_penalty

    # 3. Age (Sol = 4.57 Gyr; +/- 0.50 Gyr Phanerozoic Earth window)
    age_info = evaluate_planetary_age_habitability(system.age_gyr, pstar.mass)
    age_diff = abs(system.age_gyr - SOL_BENCHMARK["age_gyr"])
    if age_diff <= 0.50:
        age_adj = 18.0 - age_diff * 12.0
    else:
        age_adj = -(age_diff - 0.50) * 8.5
    score += age_adj

    # 4. Metallicity ([Fe/H] = 0.00 dex)
    feh = system.metallicity_feh
    feh_diff = abs(feh - SOL_BENCHMARK["metallicity_feh"])
    if feh_diff <= 0.10:
        feh_adj = 12.0 - feh_diff * 40.0
    else:
        feh_adj = -(feh_diff - 0.10) * 28.0
    score += feh_adj

    # 5. Multiplicity (Sol is a single star)
    if multiplicity == 1:
        mult_adj = 14.0
    else:
        mult_adj = -(multiplicity - 1) * 9.0
    score += mult_adj

    # Category classification
    if (
        lum_class == "V"
        and s_class == "G"
        and spectral_sub_diff <= 1
        and multiplicity == 1
        and age_diff <= 0.60
        and feh_diff <= 0.12
    ):
        category = "Solar Twin"
    elif (
        lum_class == "V"
        and s_class == "G"
        and spectral_sub_diff <= 3
        and age_diff <= 1.0
        and feh_diff <= 0.25
    ):
        category = "Coeval Solar Analogue"
    elif lum_class == "V" and s_class == "G":
        category = "G-Type Main-Sequence Star"
    elif lum_class == "V" and s_class in ("F", "K"):
        category = "FGK Main-Sequence Neighbour"
    else:
        category = "Non-Solar Star"

    return {
        "score": round(score, 2),
        "hex_coord": system.hex_coord,
        "name": system.name,
        "subsector_code": system.subsector_code,
        "subsector_name": system.subsector_name,
        "allegiance": system.allegiance,
        "category": category,
        "spectral_type": pstar.spectral_type,
        "all_stars": [s.spectral_type for s in non_comp_stars],
        "multiplicity": multiplicity,
        "mass": round(pstar.mass, 3),
        "luminosity": round(pstar.luminosity, 4),
        "temp_k": int(round(pstar.temp_k)),
        "diameter": round(pstar.diameter, 3),
        "hzco_orbit": round(pstar.hzco, 2),
        "hzco_au": round(Utils.orbit_to_au(pstar.hzco), 3),
        "age_gyr": round(system.age_gyr, 3),
        "age_delta_gyr": round(system.age_gyr - SOL_BENCHMARK["age_gyr"], 3),
        "in_earth_age_window": age_info["in_earth_age_window"],
        "geological_epoch": age_info["epoch"],
        "metallicity_feh": feh,
    }


def find_solar_analogues(
    sector: Sector,
    top_n: int = 10,
    single_star_only: bool = False,
) -> List[Dict[str, Any]]:
    """
    Searches a Sector for the closest Solar analogue stars (considering spectral class,
    luminosity class, mass, effective temperature, luminosity, age, metallicity [Fe/H],
    and multiplicity) and returns the top_n ranked matches.
    """
    results: List[Dict[str, Any]] = []
    for hex_coord, system in sector.systems.items():
        if not system.hex_coord:
            system.hex_coord = hex_coord
        info = compute_solar_analogue_score(system)
        if single_star_only and info.get("multiplicity", 0) != 1:
            continue
        results.append(info)

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_n]


def compute_solar_system_analogue_score(system: StellarSystem) -> Dict[str, Any]:
    """
    Evaluates how closely a StellarSystem's planetary orbital architecture resembles
    the Solar System:
    - Inner Terrestrial Zone (Orbit# <= HZCO + 1.15, ~0.35-1.7 AU for Sol):
      Rocky planets in Mercury/Venus/Earth/Mars-like positions and NO inner gas giants.
    - Frost-Line / Kuiper Planetoid Belts (~2-4.5 AU and ~25-45 AU scaled).
    - Outer Gas Giant Zone (Orbit# > HZCO + 1.15, ~2.0-35 AU for Sol):
      Gas giants in Jupiter/Saturn/Uranus/Neptune-like positions beyond the frost line.
    - Host star similarity (G/F/K V primary, HZCO near Orbit 3.0 / 1.0 AU, age, metallicity).
    """
    pstar = system.primary_star
    if not pstar:
        return {"score": -1e9, "hex_coord": system.hex_coord, "name": system.name}

    if system.metallicity_feh == 0.0 and all(s.metallicity_feh == 0.0 for s in system.stars):
        calculate_stellar_metallicity(system)

    worlds = sorted(
        [w for w in system.all_worlds if w.orbit_au > 0 and w.orbit_num <= 20.0],
        key=lambda w: w.orbit_num,
    )
    if not worlds:
        return {"score": -1e9, "hex_coord": system.hex_coord, "name": system.name}

    hzco = pstar.hzco
    # Inner rocky zone extends to just outside Mars's relative orbit (HZCO + 1.15)
    inner_limit = hzco + 1.15
    # Classical outer Jovian/ice-giant zone extends to HZCO + 6.5 (~50 AU for Sol)
    outer_limit = hzco + 6.5

    inner_worlds = [w for w in worlds if w.orbit_num <= inner_limit]
    outer_worlds = [w for w in worlds if inner_limit < w.orbit_num <= outer_limit]

    inner_t = [w for w in inner_worlds if w.body_type == "Terrestrial"]
    inner_g = [w for w in inner_worlds if w.body_type == "Gas Giant"]
    outer_g = [w for w in outer_worlds if w.body_type == "Gas Giant"]
    outer_t = [w for w in outer_worlds if w.body_type == "Terrestrial"]
    all_belts = [w for w in worlds if w.body_type == "Planetoid Belt"]

    score = 0.0

    # 1. Inner Terrestrial Zone (Sol has 4 inner rocky worlds and 0 inner gas giants)
    if len(inner_t) >= 2:
        score += 38.0 - abs(len(inner_t) - 4) * 4.5
    elif len(inner_t) == 1:
        score += 10.0
    else:
        score -= 40.0

    # Heavy penalty for inner/hot/warm gas giants inside the rocky zone
    score -= len(inner_g) * 32.0

    # 2. Outer Gas Giant Zone beyond the frost line (Sol has 4 outer giants)
    if len(outer_g) >= 2:
        score += 38.0 - abs(len(outer_g) - 3.5) * 4.5
    elif len(outer_g) == 1:
        score += 20.0
    else:
        score -= 40.0

    # 3. Clean radial segregation (exclusively rocky inner zone + outer gas giants)
    if len(inner_g) == 0 and len(inner_t) >= 2 and len(outer_g) >= 2:
        score += 25.0
    elif len(inner_g) == 0 and len(inner_t) >= 2 and len(outer_g) == 1:
        score += 12.0

    # 4. Habitable Zone terrestrial planet (Earth slot: |Orbit# - HZCO| <= 0.65)
    hz_terrestrials = [w for w in inner_t if abs(w.orbit_num - hzco) <= 0.65]
    if hz_terrestrials:
        score += 15.0

    # 5. Planetoid Belt presence (Main Asteroid Belt / Kuiper Belt analogues)
    frost_belts = [w for w in all_belts if (hzco + 0.5) <= w.orbit_num <= (hzco + 4.5)]
    kuiper_belts = [w for w in all_belts if w.orbit_num > (hzco + 4.5)]
    if frost_belts:
        score += 12.0
    if kuiper_belts:
        score += 6.0

    # 6. Slot-by-slot orbital position matching (relative to HZCO and in absolute AU)
    sol_t_slots = [s for s in SOL_PLANET_SLOTS if s["body_type"] == "Terrestrial"]
    t_deltas = [w.orbit_num - hzco for w in inner_t]
    matched_inner_slots = []
    for slot in sol_t_slots:
        if t_deltas:
            best_w = min(inner_t, key=lambda w: abs((w.orbit_num - hzco) - slot["delta_hzco"]))
            best_d = abs((best_w.orbit_num - hzco) - slot["delta_hzco"])
            if best_d <= 0.60:
                score += (0.60 - best_d) * 12.0
                matched_inner_slots.append(
                    f"{slot['name']} -> {best_w.designation} (Orbit {best_w.orbit_num:.1f}, {best_w.orbit_au:.2f} AU)"
                )

    sol_g_slots = [s for s in SOL_PLANET_SLOTS if s["body_type"] == "Gas Giant"]
    g_deltas = [w.orbit_num - hzco for w in outer_g]
    matched_outer_slots = []
    for slot in sol_g_slots:
        if g_deltas:
            best_w = min(outer_g, key=lambda w: abs((w.orbit_num - hzco) - slot["delta_hzco"]))
            best_d = abs((best_w.orbit_num - hzco) - slot["delta_hzco"])
            if best_d <= 1.10:
                score += (1.10 - best_d) * 9.0
                matched_outer_slots.append(
                    f"{slot['name']} -> {best_w.designation} ({best_w.size_code[:2]} at Orbit {best_w.orbit_num:.1f}, {best_w.orbit_au:.2f} AU)"
                )

    # 7. Host Star, Age & Metallicity context
    sp = pstar.spectral_type
    if sp.startswith("G") and sp.endswith(" V"):
        score += 22.0
    elif sp.startswith(("F", "K")) and sp.endswith(" V"):
        score += 10.0
    else:
        score -= 18.0

    # Proximity of HZCO to Sol's Orbit 3.0 (1.0 AU) so absolute AU positions also align
    score -= abs(hzco - 3.0) * 6.0

    # Age & Metallicity bonus
    age_diff = abs(system.age_gyr - SOL_BENCHMARK["age_gyr"])
    if age_diff <= 0.60:
        score += 10.0 - age_diff * 8.0
    else:
        score -= min(18.0, (age_diff - 0.60) * 2.5)

    score -= abs(system.metallicity_feh - 0.0) * 10.0

    non_comp = [s for s in system.stars if not s.is_composite]
    if len(non_comp) == 1:
        score += 8.0
    else:
        score -= (len(non_comp) - 1) * 4.0

    orbital_sequence = [
        f"{w.body_type[0]}@{w.orbit_num:.1f}({w.orbit_au:.2f}AU)"
        for w in worlds
    ]

    return {
        "score": round(score, 2),
        "hex_coord": system.hex_coord,
        "name": system.name,
        "subsector_code": system.subsector_code,
        "subsector_name": system.subsector_name,
        "allegiance": system.allegiance,
        "primary_star": pstar.spectral_type,
        "all_stars": [s.spectral_type for s in non_comp],
        "age_gyr": round(system.age_gyr, 3),
        "metallicity_feh": system.metallicity_feh,
        "hzco_orbit": round(hzco, 2),
        "hzco_au": round(Utils.orbit_to_au(hzco), 2),
        "inner_terrestrial_count": len(inner_t),
        "inner_gas_giant_count": len(inner_g),
        "outer_gas_giant_count": len(outer_g),
        "outer_terrestrial_count": len(outer_t),
        "planetoid_belt_count": len(all_belts),
        "hz_terrestrial_count": len(hz_terrestrials),
        "matched_inner_planets": matched_inner_slots,
        "matched_outer_giants": matched_outer_slots,
        "orbital_sequence": orbital_sequence,
    }


def find_solar_system_analogues(sector: Sector, top_n: int = 10) -> List[Dict[str, Any]]:
    """
    Searches a Sector for planetary systems whose orbital architecture (inner
    terrestrial planets inside the frost line, zero inner gas giants, planetoid belts,
    and outer gas giants in Jupiter/Saturn/Uranus/Neptune-like positions) most closely
    resembles the Solar System.
    """
    results: List[Dict[str, Any]] = []
    for hex_coord, system in sector.systems.items():
        if not system.hex_coord:
            system.hex_coord = hex_coord
        info = compute_solar_system_analogue_score(system)
        results.append(info)

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_n]


def compute_coupled_earth_similarity_score(
    world: PlanetaryBody,
    system: StellarSystem,
    include_age_and_metallicity: bool = True,
) -> float:
    """
    Computes an Earth-Similarity Index (ESI) score for a terrestrial world.
    When include_age_and_metallicity=True, incorporates the astrophysical and
    geobiological constraints of stellar age (4.57 +/- 0.50 Gyr Phanerozoic
    breathable window), stellar metallicity ([Fe/H] ~ 0.00 dex), and host star
    spectral class/multiplicity in addition to planetary Size (8), Atmosphere (6),
    Hydrographics (7), Temperature (~288 K), and Gravity (~1.0 G).
    """
    if world.body_type != "Terrestrial":
        return -1e9
    size = Utils.from_eHex(world.uwp.size if world.uwp and world.uwp.size else world.size_code)
    atm = Utils.from_eHex(world.uwp.atmosphere if world.uwp and world.uwp.atmosphere else world.atmosphere_code)
    hyd = Utils.from_eHex(world.uwp.hydrographics if world.uwp and world.uwp.hydrographics else world.hydrographics_code)
    pop = Utils.from_eHex(world.uwp.population) if world.is_mainworld and world.uwp else 1
    if (world.is_mainworld and pop == 0) or size == 0:
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
        if pstar.spectral_type.startswith("G") and pstar.spectral_type.endswith(" V"):
            s_sub = int(pstar.spectral_type[1]) if len(pstar.spectral_type) > 1 and pstar.spectral_type[1].isdigit() else 5
            score += 16.0 - abs(s_sub - 2) * 1.0
        elif pstar.spectral_type.startswith(("F", "K")) and pstar.spectral_type.endswith(" V"):
            score += 6.0
        else:
            score -= 10.0

    if include_age_and_metallicity:
        if system.metallicity_feh == 0.0 and all(s.metallicity_feh == 0.0 for s in system.stars):
            calculate_stellar_metallicity(system)

        star_mass = pstar.mass if pstar and pstar.mass > 0 else 1.0
        age_info = evaluate_planetary_age_habitability(system.age_gyr, star_mass)
        score += age_info["age_score_adjustment"]

        # Metallicity penalty around Solar [Fe/H] = 0.00
        score -= abs(system.metallicity_feh - 0.0) * 18.0

        # Single-star stability preference
        non_comp = [s for s in system.stars if not s.is_composite]
        if len(non_comp) == 1:
            score += 8.0
        else:
            score -= (len(non_comp) - 1) * 4.5

    return round(score, 2)


def find_earth_analogues(
    sector: Sector,
    top_n: int = 10,
    include_age_and_metallicity: bool = True,
    include_secondary_worlds: bool = True,
) -> List[Dict[str, Any]]:
    """
    Finds the top Earth-analogue terrestrial worlds across a Sector, optionally
    accounting for stellar age (4.57 +/- 0.50 Gyr Phanerozoic habitability window),
    metallicity ([Fe/H]), and secondary habitable-zone terrestrial worlds.
    """
    candidates: List[Dict[str, Any]] = []
    for hex_coord, system in sector.systems.items():
        if not system.hex_coord:
            system.hex_coord = hex_coord
        if system.metallicity_feh == 0.0 and all(s.metallicity_feh == 0.0 for s in system.stars):
            calculate_stellar_metallicity(system)

        pstar = system.primary_star
        star_mass = pstar.mass if pstar and pstar.mass > 0 else 1.0
        age_info = evaluate_planetary_age_habitability(system.age_gyr, star_mass)
        non_comp = [s.spectral_type for s in system.stars if not s.is_composite]

        for world in system.all_worlds:
            if world.body_type != "Terrestrial":
                continue
            if not include_secondary_worlds and not world.is_mainworld:
                continue

            coupled_score = compute_coupled_earth_similarity_score(
                world, system, include_age_and_metallicity=include_age_and_metallicity
            )
            physical_only_score = compute_coupled_earth_similarity_score(
                world, system, include_age_and_metallicity=False
            )
            if coupled_score <= -1e8:
                continue

            uwp_str = str(world.uwp) if world.is_mainworld and world.uwp else (
                f"X{world.size_code or '0'}{world.atmosphere_code or '0'}{world.hydrographics_code or '0'}000-0"
            )
            candidates.append({
                "score": coupled_score,
                "physical_only_score": physical_only_score,
                "hex_coord": hex_coord,
                "system_name": system.name,
                "world_name": world.name,
                "designation": world.designation,
                "is_mainworld": world.is_mainworld,
                "uwp": uwp_str,
                "orbit_num": round(world.orbit_num, 2),
                "orbit_au": round(world.orbit_au, 2),
                "mean_temperature_k": round(world.mean_temperature, 1),
                "gravity_g": round(world.gravity, 2),
                "primary_star": pstar.spectral_type if pstar else "N/A",
                "all_stars": non_comp,
                "age_gyr": round(system.age_gyr, 3),
                "in_earth_age_window": age_info["in_earth_age_window"],
                "geological_epoch": age_info["epoch"],
                "metallicity_feh": system.metallicity_feh,
            })

    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[:top_n]
