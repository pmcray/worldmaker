"""Expanded atmosphere characteristics (WBH pp.78-98).

Beyond the single Atmosphere digit of the UWP, the handbook derives total
atmospheric pressure, oxygen fraction and partial pressure, scale height, and
the subtype detail for tainted, exotic, corrosive, insidious, very dense, low
and unusual atmospheres.
"""
import math
import random
from typing import Any, Dict, Optional

from .utils import Utils

# Atmosphere Codes table (WBH p.79): pressure range in bar and its span.
# 'Varies' entries carry a representative range so pressure is still defined.
ATMOSPHERE_CODES: Dict[int, Dict[str, Any]] = {
    0:  {'name': 'None',             'min': 0.0,   'span': 0.0009, 'gear': 'Vacc Suit'},
    1:  {'name': 'Trace',            'min': 0.001, 'span': 0.089,  'gear': 'Vacc Suit'},
    2:  {'name': 'Very Thin, Tainted', 'min': 0.1, 'span': 0.32,   'gear': 'Respirator and Filter'},
    3:  {'name': 'Very Thin',        'min': 0.1,   'span': 0.32,   'gear': 'Respirator'},
    4:  {'name': 'Thin, Tainted',    'min': 0.43,  'span': 0.27,   'gear': 'Filter'},
    5:  {'name': 'Thin',             'min': 0.43,  'span': 0.27,   'gear': 'None'},
    6:  {'name': 'Standard',         'min': 0.70,  'span': 0.79,   'gear': 'None'},
    7:  {'name': 'Standard, Tainted', 'min': 0.70, 'span': 0.79,   'gear': 'Filter'},
    8:  {'name': 'Dense',            'min': 1.50,  'span': 0.99,   'gear': 'None'},
    9:  {'name': 'Dense, Tainted',   'min': 1.50,  'span': 0.99,   'gear': 'Filter'},
    10: {'name': 'Exotic',           'min': 0.10,  'span': 2.40,   'gear': 'Air Supply'},
    11: {'name': 'Corrosive',        'min': 1.00,  'span': 90.0,   'gear': 'Vacc Suit'},
    12: {'name': 'Insidious',        'min': 1.00,  'span': 90.0,   'gear': 'Vacc Suit'},
    13: {'name': 'Very Dense',       'min': 2.50,  'span': 7.50,   'gear': 'Varies by altitude'},
    14: {'name': 'Low',              'min': 0.10,  'span': 0.32,   'gear': 'Varies by altitude'},
    15: {'name': 'Unusual',          'min': 0.10,  'span': 2.40,   'gear': 'Varies'},
    16: {'name': 'Gas, Helium',      'min': 100.0, 'span': 400.0,  'gear': 'HEV Suit'},
    17: {'name': 'Gas, Hydrogen',    'min': 1000.0, 'span': 4000.0, 'gear': 'Not Survivable'},
}

TAINTED_CODES = (2, 4, 7, 9)

# Taint subtype / severity / persistence (WBH pp.85-88)
TAINT_SUBTYPES = {
    2: 'Chlorine', 3: 'Fluorine', 4: 'Sulphur Compounds', 5: 'Nitrogen Compounds',
    6: 'Low Oxygen', 7: 'Particulates', 8: 'High Carbon Dioxide',
    9: 'Organic Toxins', 10: 'Radioactive Particulates', 11: 'Heavy Metals',
    12: 'Biologic',
}
TAINT_SEVERITY = {2: 'Trivial', 3: 'Mild', 4: 'Mild', 5: 'Moderate',
                  6: 'Moderate', 7: 'Moderate', 8: 'Severe', 9: 'Severe',
                  10: 'Extreme', 11: 'Extreme', 12: 'Lethal'}
TAINT_PERSISTENCE = {2: 'Intermittent (rare)', 3: 'Intermittent', 4: 'Intermittent',
                     5: 'Seasonal', 6: 'Seasonal', 7: 'Regional', 8: 'Regional',
                     9: 'Planet-wide', 10: 'Planet-wide', 11: 'Planet-wide',
                     12: 'Planet-wide (permanent)'}

EXOTIC_SUBTYPES = {
    2: 'Very Thin, Irritant', 3: 'Very Thin', 4: 'Thin, Irritant', 5: 'Thin',
    6: 'Standard', 7: 'Standard, Irritant', 8: 'Dense', 9: 'Dense, Irritant',
    10: 'Very Dense', 11: 'Gas, Helium', 12: 'Gas, Hydrogen',
}
CORROSIVE_TYPES = {2: 'Acidic (sulphuric)', 3: 'Acidic (hydrochloric)',
                   4: 'Acidic', 5: 'Caustic', 6: 'Caustic (alkaline)',
                   7: 'Oxidising', 8: 'Oxidising (halogen)', 9: 'Reducing',
                   10: 'Reducing (hydride)', 11: 'Superheated Vapour',
                   12: 'Multiple Corrosive Agents'}
UNUSUAL_TYPES = {2: 'Ellipsoidal', 3: 'Layered', 4: 'Layered',
                 5: 'Variable Pressure', 6: 'Variable Pressure',
                 7: 'Periodic (seasonal collapse)', 8: 'Periodic',
                 9: 'Episodic Outgassing', 10: 'Highly Ionised',
                 11: 'Panthalassic Vapour', 12: 'Exotic Suspension'}


def total_pressure(atm_code: int) -> float:
    """Total Atmospheric Pressure (bar) = Minimum Pressure Range + Span x r,
    where r is a linear 0-1 roll (WBH p.80)."""
    entry = ATMOSPHERE_CODES.get(atm_code)
    if not entry:
        return 0.0
    if entry['span'] <= 0:
        return round(entry['min'], 4)
    r = random.randint(1, 100) / 100.0
    return round(entry['min'] + entry['span'] * r, 4)


def oxygen_fraction(atm_code: int) -> float:
    """Oxygen fraction for atmospheres that have free oxygen (WBH p.80).
    Habitable worlds run 10-30%; the book's roll is ((1D-1)x5 + 1D-1)/100."""
    if atm_code not in (2, 3, 4, 5, 6, 7, 8, 9, 13, 14):
        return 0.0
    # ((1D-1) x 5 + 1D-1) / 100 already spans 0.00-0.30; a stable biosphere
    # sits in the 10-30% band, so the floor is raised rather than the whole
    # range shifted.
    raw = ((Utils.D6() - 1) * 5 + (Utils.D6() - 1)) / 100.0
    return round(min(0.30, max(0.08, raw)), 4)


def scale_height(mean_temp_k: float, gravity: float) -> float:
    """Scale Height (km) ~ 8.5km x Mean Temperature / (g x 288) (WBH p.81)."""
    if gravity <= 0 or mean_temp_k <= 0:
        return 0.0
    return round(8.5 * mean_temp_k / (gravity * 288.0), 3)


def pressure_at_altitude(surface_pressure: float, altitude_km: float,
                         scale_h: float) -> float:
    """Pressure(a) = Pressure(mean) / e^(height / H) (WBH p.81)."""
    if scale_h <= 0:
        return surface_pressure
    return round(surface_pressure / math.exp(altitude_km / scale_h), 5)


def _roll_taint() -> Dict[str, str]:
    return {
        'type': TAINT_SUBTYPES.get(Utils.D6(2), 'Particulates'),
        'severity': TAINT_SEVERITY.get(Utils.D6(2), 'Moderate'),
        'persistence': TAINT_PERSISTENCE.get(Utils.D6(2), 'Regional'),
    }


def _composition_for(atm_code: int, o2_fraction: float) -> str:
    """A short description of the atmosphere's bulk composition."""
    if atm_code == 0:
        return "Vacuum"
    if atm_code == 1:
        return "Trace gases (outgassed CO2, argon)"
    if atm_code in (16,):
        return "Helium-dominated, with hydrogen"
    if atm_code == 17:
        return "Hydrogen-dominated (gas dwarf)"
    if atm_code == 11:
        return "Carbon dioxide with corrosive vapours"
    if atm_code == 12:
        return "Corrosive agents with insidious penetrants"
    if atm_code == 10:
        return "Nitrogen and methane with complex organics"
    if 2 <= atm_code <= 9 or atm_code in (13, 14):
        return f"Nitrogen-oxygen ({o2_fraction * 100:.0f}% O2), trace argon and CO2"
    return "Mixed gases"


def generate_atmosphere_details(world: Any) -> None:
    """Fills in the expanded atmosphere fields for a world or satellite."""
    code_str = getattr(world, 'atmosphere_code', '') or ''
    if not str(code_str).strip():
        return
    atm = Utils.from_eHex(code_str)

    entry = ATMOSPHERE_CODES.get(atm)
    if not entry:
        return

    world.atmosphere_name = entry['name']
    world.survival_gear = entry['gear']
    world.atmos_pressure_bar = total_pressure(atm)
    world.oxygen_fraction = oxygen_fraction(atm)
    world.partial_pressure_oxygen = round(
        world.oxygen_fraction * world.atmos_pressure_bar, 4)
    world.scale_height_km = scale_height(
        getattr(world, 'mean_temperature', 0.0) or 0.0,
        getattr(world, 'gravity', 0.0) or 0.0)
    world.atmosphere_composition = _composition_for(atm, world.oxygen_fraction)

    # Subtype detail by category
    if atm in TAINTED_CODES:
        world.atmosphere_taint = _roll_taint()
    elif atm == 10:  # Exotic
        world.atmosphere_subtype = EXOTIC_SUBTYPES.get(Utils.D6(2), 'Standard')
        if 'Irritant' in world.atmosphere_subtype:
            world.atmosphere_taint = _roll_taint()
    elif atm in (11, 12):  # Corrosive / Insidious
        world.atmosphere_subtype = CORROSIVE_TYPES.get(Utils.D6(2), 'Acidic')
    elif atm == 15:  # Unusual
        world.atmosphere_subtype = UNUSUAL_TYPES.get(Utils.D6(2), 'Layered')

    # Very Dense (D) and Low (E): the safe-altitude band matters to visitors
    if atm == 13:
        world.minimum_safe_altitude_km = _safe_altitude_very_dense(world)
    elif atm == 14:
        world.safe_altitude_below_mean_km = _safe_altitude_low(world)

    # Oxygen-poor air is itself a taint (WBH p.133 habitability note)
    if 0 < world.partial_pressure_oxygen < 0.10:
        world.low_oxygen = True


def _safe_altitude_very_dense(world: Any) -> float:
    """Minimum Safe Altitude = ln(Bad Ratio) x Scale Height, where the bad
    ratio compares the offending partial pressure to a safe one (WBH p.90)."""
    h = getattr(world, 'scale_height_km', 0.0)
    ppo = getattr(world, 'partial_pressure_oxygen', 0.0)
    if h <= 0 or ppo <= 0:
        return 0.0
    bad_ratio = ppo / 0.5  # safe oxygen partial pressure < 0.5 bar
    if bad_ratio <= 1:
        return 0.0
    return round(math.log(bad_ratio) * h, 3)


def _safe_altitude_low(world: Any) -> float:
    """Low Bad Ratio = 0.1 / ppo; safe altitude below the mean baseline is
    ln(ratio) x scale height (WBH p.91)."""
    h = getattr(world, 'scale_height_km', 0.0)
    ppo = getattr(world, 'partial_pressure_oxygen', 0.0)
    if h <= 0 or ppo <= 0:
        return 0.0
    ratio = 0.1 / ppo
    if ratio <= 1:
        return 0.0
    return round(math.log(ratio) * h, 3)


def check_runaway_greenhouse(world: Any, system_age_gyr: float) -> bool:
    """Runaway greenhouse occurs on 12+: 2D + 1 per Gyr of system age, plus
    1 per full 10K above 303K (WBH p.81)."""
    temp = getattr(world, 'mean_temperature', 0.0) or 0.0
    dm = int(math.ceil(max(0.0, system_age_gyr)))
    if temp > 303:
        dm += int((temp - 303) // 10)
    return Utils.D6(2) + dm >= 12
