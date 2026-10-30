"""Special Circumstances (WBH pp.219-234).

Empty hexes and their survey process, detailed dead-star generation (white
dwarfs, neutron stars, pulsars, black holes), brown dwarfs by type, dead-star
and brown-dwarf planetary systems, protostar and primordial systems, rogue
planets, nebulae, star clusters, artificial worlds and the empty-hex jump
modifiers.
"""
import math
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .classes import PlanetaryBody, Satellite, Sector, Star, StellarSystem
from .utils import Utils
from .data import DATA

SOLAR_DIAMETER_KM = 1391000.0
EARTH_DIAMETER_KM = 12742.0


# ------------------------------------------------------------- dead stars

# White Dwarf Aging table (WBH p.227), for a 0.6 solar mass white dwarf.
# Diameter stays fixed; temperature and luminosity fall with age in Gyr.
WHITE_DWARF_AGING = [
    # (age Gyr, temperature K, luminosity)
    (0.0, 100000.0, 2500.0),
    (0.1, 25000.0, 0.20),
    (0.5, 10000.0, 0.0025),
    (1.0, 8000.0, 0.0010),
    (1.5, 7000.0, 0.00059),
    (2.5, 5500.0, 0.00023),
    (5.0, 5000.0, 0.00015),
    (10.0, 4000.0, 0.000063),
    (13.0, 3800.0, 0.000051),
]


def _interpolate_aging(age_gyr: float) -> float:
    """Temperature of a 0.6 solar-mass white dwarf at an age, interpolated
    from the aging table."""
    table = WHITE_DWARF_AGING
    if age_gyr <= table[0][0]:
        return table[0][1]
    for (a0, t0, _), (a1, t1, _) in zip(table, table[1:]):
        if age_gyr <= a1:
            span = a1 - a0
            frac = (age_gyr - a0) / span if span else 0.0
            return t0 + (t1 - t0) * frac
    return table[-1][1]


def _luminosity_of(diameter_sol: float, temp_k: float) -> float:
    """Luminosity formula (WBH p.20): D^2 x (T / 5772)^4."""
    return max(1e-12, (diameter_sol ** 2) * ((temp_k / 5772.0) ** 4))


def generate_white_dwarf(age_gyr: float = None) -> Star:
    """White dwarf generation (WBH p.227).

    Mass = d10/100 + (2D-1)/10, capped under the 1.44 Chandrasekhar limit;
    diameter = (1/Mass) x 0.01 (terrestrial-planet sized); temperature from
    the aging table, scaled by Mass/0.6."""
    star = Star(designation="A", spectral_type="D")
    star.mass = round(min(1.43, Utils.d10() / 100.0 + (Utils.D6(2) - 1) / 10.0), 3)
    star.diameter = round((1.0 / star.mass) * 0.01, 5)
    if age_gyr is None:
        age_gyr = round(random.uniform(0.1, 10.0), 2)
    star.temp_k = round(_interpolate_aging(age_gyr) * (star.mass / 0.6), 1)
    star.luminosity = _luminosity_of(star.diameter, star.temp_k)
    star.hzco = Utils.calculate_hzco(star.luminosity)
    star.mao = 0.001  # Dead star minimum allowable orbit (WBH p.229)
    return star


def generate_neutron_star(kind: str = None, age_gyr: float = None) -> Star:
    """Neutron star generation (WBH p.228).

    Mass = 1 + 1D/10, exploding into (1D-1)/10 on a six, always under the
    2.16 collapse limit; diameter 19+1D kilometres. One neutron star in 100
    is a pulsar, one in a million a still-active magnetar."""
    if kind is None:
        roll = random.randint(1, 1000000)
        if roll == 1:
            kind = 'Magnetar'
        elif roll <= 10000:
            kind = 'Pulsar'
        else:
            kind = 'Neutron Star'
    # Magnetars share the pulsar's Traveller behaviour; the spectral token
    # stays inside the renderer-known set.
    spectral = 'Pulsar' if kind in ('Pulsar', 'Magnetar') else 'Neutron Star'
    star = Star(designation="A", spectral_type=spectral)

    mass_roll = Utils.D6()
    mass = 1.0 + mass_roll / 10.0
    if mass_roll == 6:
        mass += (Utils.D6() - 1) / 10.0
    star.mass = round(min(2.16, mass), 2)
    diameter_km = 19 + Utils.D6()
    star.diameter = round(diameter_km / SOLAR_DIAMETER_KM, 8)
    if age_gyr is None:
        age_gyr = round(random.uniform(0.1, 10.0), 2)
    star.temp_k = round(_interpolate_aging(age_gyr) * (star.mass / 0.6), 1)
    star.luminosity = _luminosity_of(star.diameter, star.temp_k)
    star.hzco = Utils.calculate_hzco(star.luminosity)
    star.mao = 0.001
    return star


def generate_black_hole() -> Star:
    """Black hole generation (WBH p.228).

    Mass = 2.1 + 1D - 1 + d10/10, with each rolled six adding another 1D;
    diameter = 5.9 km x mass. It radiates nothing."""
    star = Star(designation="A", spectral_type="Black Hole")
    mass = 2.1 + Utils.d10() / 10.0
    roll = Utils.D6()
    mass += roll - 1
    while roll == 6:
        roll = Utils.D6()
        mass += roll
    star.mass = round(mass, 2)
    star.diameter = round((5.9 * star.mass) / SOLAR_DIAMETER_KM, 9)
    star.temp_k = 0.0
    star.luminosity = 0.0
    star.hzco = 0.0
    star.mao = 0.001
    return star


# ------------------------------------------------------------ brown dwarfs

# Brown Dwarf Types table (WBH p.226): type, temperature, mass, diameter
# (solar), luminosity at about one billion years, ordered by falling mass.
BROWN_DWARF_TYPES = [
    ('L0', 2400.0, 0.080, 0.10, 0.00029),
    ('L5', 1850.0, 0.060, 0.08, 0.000066),
    ('T0', 1300.0, 0.050, 0.09, 0.000020),
    ('T5', 900.0, 0.040, 0.11, 0.0000070),
    ('Y0', 550.0, 0.025, 0.10, 0.00000081),
    ('Y5', 300.0, 0.013, 0.10, 0.000000072),
]

_BD_SEQUENCE = ['L', 'T', 'Y']


def brown_dwarf_type(mass: float, age_gyr: float = 1.0) -> str:
    """Type and subtype of a brown dwarf by mass, aged one subtype per
    billion years above 0.05 solar masses and two below (WBH p.226)."""
    # Index into the table by mass: find the bracketing rows and interpolate
    # a subtype position along the L0..Y5 sequence (each row is 5 subtypes).
    rows = BROWN_DWARF_TYPES
    if mass >= rows[0][2]:
        position = 0.0
    elif mass <= rows[-1][2]:
        position = (len(rows) - 1) * 5.0
    else:
        position = 0.0
        for i, ((_, _, m0, _, _), (_, _, m1, _, _)) in enumerate(
                zip(rows, rows[1:])):
            if m1 <= mass <= m0:
                frac = (m0 - mass) / (m0 - m1) if m0 != m1 else 0.0
                position = (i + frac) * 5.0
                break
    ageing = (age_gyr - 1.0) * (1.0 if mass > 0.05 else 2.0)
    position = max(0.0, min(len(rows) * 5.0 + 4, position + max(0.0, ageing)))
    letter = _BD_SEQUENCE[min(len(_BD_SEQUENCE) - 1, int(position) // 10)]
    subtype = int(position) % 10
    return f"{letter}{subtype}"


def _brown_dwarf_temperature(mass: float) -> float:
    """Temperature interpolated from the Brown Dwarf Types table by mass."""
    rows = BROWN_DWARF_TYPES
    if mass >= rows[0][2]:
        return rows[0][1]
    if mass <= rows[-1][2]:
        return rows[-1][1]
    for (_, t0, m0, _, _), (_, t1, m1, _, _) in zip(rows, rows[1:]):
        if m1 <= mass <= m0:
            frac = (m0 - mass) / (m0 - m1) if m0 != m1 else 0.0
            return t0 + (t1 - t0) * frac
    return rows[-1][1]


def generate_brown_dwarf(age_gyr: float = None) -> Star:
    """Brown dwarf generation (WBH pp.226-227).

    Mass = 1D/100 + (4D-1)/1000 (0.013 to 0.083 solar masses); the diameter
    uses the large gas giant sizing roll of 2D+6 Earth diameters, DM-2 for
    masses between 0.05 and 0.07."""
    star = Star(designation="A", spectral_type="BD")
    star.mass = round(Utils.D6() / 100.0 + (Utils.D6(4) - 1) / 1000.0, 4)
    diameter_roll = Utils.D6(2) + 6
    if 0.05 <= star.mass <= 0.07:
        diameter_roll -= 2
    star.diameter = round(diameter_roll * EARTH_DIAMETER_KM / SOLAR_DIAMETER_KM, 4)
    if age_gyr is None:
        age_gyr = round(random.uniform(0.5, 10.0), 2)
    star.temp_k = round(_brown_dwarf_temperature(star.mass), 1)
    star.luminosity = _luminosity_of(star.diameter, star.temp_k)
    star.hzco = Utils.calculate_hzco(star.luminosity)
    star.mao = 0.005  # Brown dwarf minimum allowable orbit (WBH p.227)
    return star


# ------------------------------------------------ special planetary systems

def _generate_special_system(name: str, primary: Star, age_gyr: float,
                             count_profile: dict,
                             population_dm: int = 0) -> StellarSystem:
    """Runs the standard generation chain on a pre-built exotic primary."""
    from .generator import generate_full_system
    system = StellarSystem(name=name)
    system.stars.append(primary)
    return generate_full_system(name, population_dm=population_dm,
                                system=system, age_gyr=age_gyr,
                                count_profile=count_profile)


def dead_star_system_exists(kinds: List[str]) -> bool:
    """Dead Star Planetary System Exists on 2D 8+ (WBH p.229): DM-2 for a
    multiple dead-star system, DM-2 for a neutron star, DM-4 for a black
    hole; a natural 12 always succeeds."""
    roll = Utils.D6(2)
    if roll == 12:
        return True
    dm = 0
    if len(kinds) > 1:
        dm -= 2
    if any(k in ('Neutron Star', 'Pulsar', 'Magnetar') for k in kinds):
        dm -= 2
    if 'Black Hole' in kinds:
        dm -= 4
    return roll + dm >= 8


def generate_dead_star_system(name: str = "Dead Star System",
                              kind: str = 'D',
                              age_gyr: float = None) -> StellarSystem:
    """A system around a dead star primary (WBH pp.227-229).

    kind is 'D' (white dwarf), 'Neutron Star', 'Pulsar', 'Magnetar' or
    'Black Hole'. Gas giants are rarer, belts commoner, terrestrials 1D-2,
    and the MAO drops to 0.001. Worlds around a pulsar or magnetar carry a
    radioactive taint at severity and persistence 9."""
    if age_gyr is None:
        age_gyr = round(random.uniform(1.0, 12.0), 2)
    if kind == 'D':
        primary = generate_white_dwarf(age_gyr)
    elif kind in ('Neutron Star', 'Pulsar', 'Magnetar'):
        primary = generate_neutron_star(kind, age_gyr)
    elif kind == 'Black Hole':
        primary = generate_black_hole()
    else:
        raise ValueError(f"unknown dead star kind: {kind}")

    if not dead_star_system_exists([kind]):
        # No planetary system survived the star's death
        system = StellarSystem(name=name, age_gyr=age_gyr)
        system.stars.append(primary)
        return system

    profile = {
        'gas_giant_present_max': 5,   # absent on 6+ (standard: absent on 10+)
        'belt_present_min': 6,        # present on 6+ (standard 8+)
        'terrestrial_count': lambda: Utils.D6() - 2,
    }
    system = _generate_special_system(name, primary, age_gyr, profile)

    if kind in ('Pulsar', 'Magnetar'):
        for world in system.all_worlds:
            if world.body_type != 'Terrestrial':
                continue
            world.atmosphere_taint = {
                'type': 'Radioactive Particulates',
                'severity': '9', 'persistence': '9'}
            world.notes.append(
                f"{kind} radiation: radioactive taint, severity 9, persistence 9")
    return system


def generate_brown_dwarf_system(name: str = "Brown Dwarf System",
                                age_gyr: float = None) -> StellarSystem:
    """A small planetary system around a brown dwarf primary (WBH p.227):
    gas giants only on 2D 7-, MAO 0.005."""
    if age_gyr is None:
        age_gyr = round(random.uniform(0.5, 12.0), 2)
    primary = generate_brown_dwarf(age_gyr)
    profile = {'gas_giant_present_max': 7}
    return _generate_special_system(name, primary, age_gyr, profile)


# ---------------------------------------- protostar and primordial systems

# Atmosphere remap bands (WBH pp.225-226). The top band is open-ended so the
# era's positive DM can never push a result off the end of the table.
_PROTOSTAR_ATMO_REMAP = ((2, 5, 10), (6, 12, 12), (13, 15, 15), (16, 99, 17))
_PRIMORDIAL_ATMO_REMAP = ((2, 7, 10), (8, 12, 12), (13, 15, 15), (16, 99, 17))


def _remap_atmosphere(value: int, bands) -> int:
    for low, high, result in bands:
        if low <= value <= high:
            return result
    return value


def crust_formation_age_myr(size: int) -> float:
    """A solid crust forms after (Size - 2)^2 + 2 million years (WBH p.225)."""
    return (max(0, size - 2)) ** 2 + 2


def _apply_young_system_conditions(system: StellarSystem, age_myr: float,
                                   atmo_remap, eccentricity_dm: int,
                                   atmosphere_dm: int, no_life_note: str):
    """The conditions shared by protostar and primordial systems (WBH p.225):
    hot early atmospheres, magma oceans on young large worlds, boosted
    eccentricities, capped terrestrial sizes and no recognisable native
    life."""
    for world in system.all_worlds:
        if world.body_type == 'Gas Giant':
            continue
        if world.body_type == 'Planetoid Belt':
            continue

        # Re-roll eccentricity with the era's DM
        roll = min(12, max(5, Utils.D6(2) + eccentricity_dm))
        ecc_data = DATA['eccentricity_values'].get(roll)
        if ecc_data:
            world.eccentricity = round(
                max(0.0, min(0.999, ecc_data['base'] + ecc_data['roll']())), 3)

        # Maximum size equals the system age in million years; the remaining
        # protoplanetary mass stays as chunks in the surrounding debris.
        size = Utils.from_eHex(world.size_code)
        max_size = max(1, int(age_myr))
        if size > max_size:
            world.notes.append(
                f"Still accreting: protoplanetary chunks share the orbit "
                f"(final Size {world.size_code})")
            size = max_size
            world.size_code = Utils.eHex(size)
            world.uwp.size = world.size_code

        # Hot, thick early atmospheres: the era's DM applies to the roll, and
        # the result then collapses onto the era's bands.
        atm = Utils.from_eHex(world.atmosphere_code or 0)
        if size > 0 and atm:
            atm = _remap_atmosphere(atm + atmosphere_dm, atmo_remap)
            world.atmosphere_code = Utils.eHex(atm)
            world.uwp.atmosphere = world.atmosphere_code

        # Magma oceans until the crust solidifies
        if size >= 2 and age_myr < crust_formation_age_myr(size):
            world.hydrographics_code = 'A'
            world.uwp.hydrographics = 'A'
            world.surface_features = "Ocean of liquid magma; no solid crust yet"
            world.mean_temperature = max(world.mean_temperature or 0.0, 1500.0)
            world.high_temperature = max(world.high_temperature or 0.0, 1500.0)
            world.notes.append("Magma ocean (surface above 1,500K)")

        # No recognisable native life this early
        world.biomass_rating = 0
        world.biocomplexity_rating = 0
        world.biodiversity_rating = 0
        world.compatibility_rating = 0
        world.native_lifeform_profile = "0000"
        world.native_sophont = False
        world.extinct_sophont = False
        world.life_details = no_life_note


def generate_protostar_system(name: str = "Protostar System",
                              age_myr: float = None) -> StellarSystem:
    """A star system still forming (WBH pp.224-225).

    The primary rolls its type with DM+1 and behaves as a Class V star whose
    diameter is inflated by (2D-2)/10, luminosity scaling with the square of
    the change. Every planetary orbit also holds a planetoid belt; systems
    under two million years old have no significant moons and vast gas giant
    rings."""
    from .stellar import generate_primary_star

    if age_myr is None:
        age_myr = max(0.5, Utils.D6(2) - 2 + random.random())  # under ~10 Myr
    age_gyr = round(age_myr / 1000.0, 5)

    primary = generate_primary_star(special_roll=min(12, Utils.D6(2) + 1))
    swell = 1.0 + (Utils.D6(2) - 2) / 10.0
    primary.diameter = round(primary.diameter * swell, 4)
    primary.luminosity = round(primary.luminosity * swell ** 2, 6)
    primary.spectral_type = f"{primary.spectral_type.split(' ')[0]} V"
    primary.hzco = Utils.calculate_hzco(primary.luminosity)

    profile = {'belt_present_min': 6}
    system = _generate_special_system(name, primary, age_gyr, profile)
    system.stars[0].orbiting_bodies.sort(key=lambda w: w.orbit_num)

    # Every orbital slot with a planet also holds a planetoid belt
    extra_belts = []
    for world in list(system.all_worlds):
        if world.body_type in ('Terrestrial', 'Gas Giant'):
            belt = PlanetaryBody(
                name=f"{world.name} Debris", parent_star_group=world.parent_star_group,
                body_type='Planetoid Belt', orbit_num=world.orbit_num,
                orbit_au=world.orbit_au, size_code='0')
            belt.notes.append("Protoplanetary debris sharing the orbit")
            extra_belts.append(belt)
    if extra_belts:
        system.stars[0].orbiting_bodies.extend(extra_belts)
        system.planetoid_belt_count += len(extra_belts)
        system.total_worlds += len(extra_belts)

    for world in system.all_worlds:
        if world.body_type != 'Gas Giant':
            continue
        if age_myr < 2.0:
            if world.size_code.startswith('GM'):
                world.size_code = 'GS' + world.size_code[2:]
                world.notes.append("Still accreting: medium gas giant at small size")
            world.satellites = [s for s in world.satellites if s.is_ring]
            world.ring_profile = (
                f"Vast accretion ring system out to {Utils.D6(2)} planetary diameters")
            world.notes.append("Vast protoplanetary ring disk")

    _apply_young_system_conditions(
        system, age_myr, _PROTOSTAR_ATMO_REMAP, eccentricity_dm=2,
        atmosphere_dm=4,
        no_life_note="No recognisable native life: protostar system")
    system.name = name
    return system


def is_primordial_host(star: Star) -> bool:
    """Stars of more than 8 solar masses, all Class Ia/Ib/II stars and all
    O-types (except O subdwarfs) host primordial systems (WBH p.225)."""
    spectral = star.spectral_type or ""
    if star.mass > 8.0:
        return True
    if spectral.endswith((' Ia', ' Ib', ' II')):
        return True
    return spectral.startswith('O') and not spectral.endswith(' VI')


def generate_primordial_system(name: str = "Primordial System",
                               age_myr: float = None) -> StellarSystem:
    """A system younger than 100 million years but past its protostar stage
    (WBH pp.225-226): widespread debris, doubled belt spans, possible
    co-orbital planets, magma oceans on the largest worlds."""
    if age_myr is None:
        age_myr = 10.0 + random.random() * 90.0
    age_gyr = round(age_myr / 1000.0, 5)

    profile = {'belt_present_min': 4}  # standard 8+, with DM+4
    from .generator import generate_full_system
    system = generate_full_system(name, system=None, age_gyr=age_gyr,
                                  count_profile=profile)

    primary = system.primary_star

    # All planetoid belt spans double and may overlap other orbits
    for world in system.all_worlds:
        if world.body_type == 'Planetoid Belt' and world.belt_span:
            world.belt_span = round(world.belt_span * 2, 3)
            world.notes.append("Primordial belt: span doubled, may overlap orbits")

    # Co-orbital extra planets on a 1D roll of 6
    extras = []
    for world in list(system.all_worlds):
        if world.body_type not in ('Terrestrial', 'Gas Giant'):
            continue
        if Utils.D6() == 6:
            extra = PlanetaryBody(
                name=f"{world.name} Companion",
                parent_star_group=world.parent_star_group,
                body_type='Terrestrial',
                orbit_num=round(world.orbit_num + (Utils.D6(2) - 7) / 10.0, 2),
                size_code=Utils.eHex(Utils.D6()))
            extra.orbit_num = max(0.01, extra.orbit_num)
            extra.orbit_au = Utils.orbit_to_au(extra.orbit_num)
            if primary and primary.mass > 0:
                extra.period_years = math.sqrt(
                    extra.orbit_au ** 3 / primary.mass)
            extra.notes.append("Co-orbital protoplanet in the same basic orbit")
            extras.append(extra)
    if extras:
        system.stars[0].orbiting_bodies.extend(extras)
        system.terrestrial_planet_count += len(extras)
        system.total_worlds += len(extras)

    _apply_young_system_conditions(
        system, age_myr, _PRIMORDIAL_ATMO_REMAP, eccentricity_dm=1,
        atmosphere_dm=2,
        no_life_note="No recognisable native life: primordial system")
    system.name = name
    return system


# ------------------------------------------------------------ rogue worlds

def generate_rogue_gas_giant(category: str = None) -> PlanetaryBody:
    """A rogue gas giant adrift in an empty hex (WBH p.220), sized with the
    standard rules; moon counts take DM-1 per dice."""
    if category is None:
        category = random.choice(['GS', 'GM', 'GL'])
    body = PlanetaryBody(name="Rogue Giant", body_type='Gas Giant')
    d_roll = DATA['gas_giant_sizing'][category]['d_roll']()
    body.diameter_km = d_roll * 12800
    body.mass_terran = DATA['gas_giant_sizing'][category]['m_roll']()
    body.size_code = f"{category}{Utils.eHex(d_roll)}"
    body.notes.append("Rogue world: no parent star")
    # Significant moons with DM-1 per dice (2D for GM/GL, 1D for GS)
    if category == 'GS':
        moons = max(0, DATA['significant_moon_quantity']['small_gas_giant']() - 1)
    else:
        moons = max(0, DATA['significant_moon_quantity']['medium_large_gas_giant']() - 2)
    for _ in range(moons):
        body.satellites.append(
            Satellite(parent_body=body, size_code=Utils.eHex(Utils.D6())))
    return body


def generate_rogue_terrestrial(large: bool = False) -> PlanetaryBody:
    """A rogue terrestrial world (WBH p.220): large ones are Size 1D+9,
    small ones 2D-2 (0 becomes 1, A becomes 9); composition rolls take a
    DM of -(1D-1); Size 3+ worlds count moons at DM-2."""
    body = PlanetaryBody(name="Rogue World", body_type='Terrestrial')
    if large:
        size = Utils.D6() + 9
    else:
        size = Utils.D6(2) - 2
        if size == 0:
            size = 1
        elif size >= 10:
            size = 9
    body.size_code = Utils.eHex(size)

    # Composition with the negative origin DM
    dm = -(Utils.D6() - 1)
    if size <= 4:
        dm -= 1
    elif size >= 6:
        dm += 1
    comp_data = DATA['terrestrial_composition']['table'].get(
        min(15, max(2, Utils.D6(2) + dm)))
    body.density = comp_data['density']
    body.core_composition = comp_data['comp']
    body.diameter_km = size * 1600 + random.randint(-800, 799)
    body.gravity = round((body.density * body.diameter_km) / 12742, 2)
    body.mass_terran = round(body.density * (body.diameter_km / 12742) ** 3, 3)

    # Frozen wanderer: only internal heat keeps it above the background
    body.atmosphere_code = '0' if size < 3 else '1'
    body.hydrographics_code = '0'
    body.mean_temperature = round(10.0 + random.random() * 20.0, 1)
    body.climate_zone = "Cryogenic (Glacial)"
    body.notes.append("Rogue world: no parent star")

    if size > 2:
        moons = max(0, DATA['significant_moon_quantity']['planet_size_3_9']() - 2)
        for _ in range(moons):
            body.satellites.append(
                Satellite(parent_body=body,
                          size_code=Utils.eHex(max(0, size - 1 - Utils.D6()))))
    return body


def generate_rogue_small_body() -> Dict[str, str]:
    """A rogue small body (WBH p.220): Size S on a 1D roll of 6, otherwise a
    single Size 0 rock; composition icy on 1-2, water-bearing on 3-5, bone
    dry on 6 - and unverifiable remotely."""
    size = 'S' if Utils.D6() == 6 else '0'
    comp_roll = Utils.D6()
    if comp_roll <= 2:
        composition = 'Mostly icy'
    elif comp_roll <= 5:
        composition = 'Water content, extraction requires mining'
    else:
        composition = 'Bone dry, useless as fuel'
    return {'size': size, 'composition': composition}


# -------------------------------------------------------------- empty hexes

# Empty Hex Objects table (WBH p.221): survey index needed to chart the
# object and detection points required per attempt from one parsec away.
EMPTY_HEX_OBJECTS = {
    'Neutron Star/Black Hole': {'si': 7, 'detection': 80},
    'White Dwarf': {'si': 3, 'detection': 0},   # automatic
    'Brown Dwarf': {'si': 4, 'detection': 20},
    'Large Gas Giant': {'si': 6, 'detection': 60},
    'Medium Gas Giant': {'si': 7, 'detection': 80},
    'Small Gas Giant': {'si': 8, 'detection': 160},
    'Terrestrial (A+)': {'si': 9, 'detection': 240},
    'Terrestrial (1-9)': {'si': 10, 'detection': 480},
    'Small Bodies': {'si': 12, 'detection': 480},
}


@dataclass
class EmptyHexSurvey:
    """What a full survey of an 'empty' hex would find (WBH pp.219-221)."""
    hex_coord: str = ""
    star_system: Optional[StellarSystem] = None
    rogue_worlds: List[PlanetaryBody] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return self.star_system is None and not self.rogue_worlds


def generate_empty_hex(density_target: int = 4,
                       name: str = "Deep Space") -> EmptyHexSurvey:
    """Runs the empty-hex process (WBH p.220).

    First a neutron star or black hole (3D roll of 18, then the region's
    system existence check), then a white dwarf (1D roll of 6, then the
    check), then a brown dwarf (the check alone); rogue gas giants and
    terrestrials can coexist with any of them."""
    survey = EmptyHexSurvey()

    def exists() -> bool:
        return Utils.D6() >= density_target

    # Star-like objects: at most one system per empty hex
    if Utils.D6(3) == 18 and exists():
        kind = 'Black Hole' if Utils.D6(2) >= 11 else 'Neutron Star'
        survey.star_system = generate_dead_star_system(name, kind)
        survey.notes.append(f"{kind} (SI {EMPTY_HEX_OBJECTS['Neutron Star/Black Hole']['si']})")
    elif Utils.D6() == 6 and exists():
        survey.star_system = generate_dead_star_system(name, 'D')
        survey.notes.append(f"White dwarf (SI {EMPTY_HEX_OBJECTS['White Dwarf']['si']})")
    elif exists():
        survey.star_system = generate_brown_dwarf_system(name)
        survey.notes.append(f"Brown dwarf (SI {EMPTY_HEX_OBJECTS['Brown Dwarf']['si']})")

    # Rogue planets, regardless of any star-like object
    if exists():
        survey.rogue_worlds.append(generate_rogue_gas_giant('GL'))
    for _ in range(2):
        if exists():
            survey.rogue_worlds.append(generate_rogue_gas_giant('GM'))
    for _ in range(3):
        if exists():
            survey.rogue_worlds.append(generate_rogue_gas_giant('GS'))
    for _ in range(4):
        if exists():
            survey.rogue_worlds.append(generate_rogue_terrestrial(large=True))
    for _ in range(10):
        if exists():
            survey.rogue_worlds.append(generate_rogue_terrestrial(large=False))

    return survey


def populate_empty_hexes(sector: Sector, density_target: int = 4):
    """Surveys every hex of the sector without a charted system and records
    the non-empty findings in sector.deep_space (WBH pp.219-221)."""
    for col in range(1, sector.width + 1):
        for row in range(1, sector.height + 1):
            hex_coord = f"{col:02d}{row:02d}"
            if hex_coord in sector.systems:
                continue
            survey = generate_empty_hex(density_target,
                                        name=f"Deep Space {hex_coord}")
            if not survey.is_empty:
                survey.hex_coord = hex_coord
                sector.deep_space[hex_coord] = survey
    return sector.deep_space


# ------------------------------------------------------------------ nebulae

NEBULA_TYPES = {
    1: 'Planetary Nebula',
    2: 'Dark Nebula',
    3: 'Ionised Hydrogen Nebula',
    4: 'Ionised Hydrogen Nebula',
    5: 'Supernova Remnant',
    6: 'Supernova Remnant',
}


def generate_nebula(name: str = "Nebula") -> dict:
    """Random nebula generation (WBH pp.229-230). A planetary nebula carries
    a newly formed white dwarf at its centre (the 0.000 column of the aging
    table); a supernova remnant may hold a neutron star or black hole."""
    nebula_type = NEBULA_TYPES[Utils.D6()]
    result = {'name': name, 'type': nebula_type, 'hexes': 1,
              'central_object': None}

    if nebula_type == 'Planetary Nebula':
        result['hexes'] = 1 if Utils.D6() == 1 else 7  # single hex or a ring of six
        # A brand new white dwarf: the 0.000 column of the aging table
        result['central_object'] = generate_white_dwarf(age_gyr=0.0)
    elif nebula_type == 'Supernova Remnant':
        roll = Utils.D6()
        if roll <= 2:
            result['central_object'] = generate_neutron_star()
        elif roll == 3:
            result['central_object'] = generate_black_hole()
        # Otherwise the remnant object was ejected by an uneven explosion
    return result


NEBULA_JUMP_DM = "-1D to all Astrogation and Engineer (j-drive) checks, rolled per jump"


# ------------------------------------------------------------ star clusters

def generate_star_cluster_hex(name: str = "Star Cluster",
                              age_gyr: float = None) -> List[StellarSystem]:
    """An open star cluster hex (WBH p.231): 2D+5 systems, all the same age,
    normally 1D x 1D x 50 million years."""
    from .generator import generate_full_system
    if age_gyr is None:
        age_gyr = round(Utils.D6() * Utils.D6() * 0.05, 3)
    count = Utils.D6(2) + 5
    systems = []
    for i in range(count):
        system = generate_full_system(f"{name} {i + 1}", age_gyr=age_gyr)
        systems.append(system)
    return systems


# --------------------------------------------------------- artificial worlds

# Artificial World Types table (WBH p.232). A size code of None means the
# structure inherits its host world's Size code.
ARTIFICIAL_WORLD_TYPES = [
    {'name': 'Station Module', 'tl': 6, 'size_code': '0',
     'description': 'Short-term occupancy module'},
    {'name': 'Station Complex', 'tl': 7, 'size_code': '0',
     'description': 'Multi-module station'},
    {'name': 'Spin Station', 'tl': 7, 'size_code': '0',
     'description': 'Full or partial spin modules for artificial gravity'},
    {'name': 'Spin Habitat', 'tl': 8, 'size_code': '0',
     'description': 'Large colony-sized rotating habitat'},
    {'name': 'Grav Station', 'tl': 10, 'size_code': '0',
     'description': 'Artificial gravity, up to city-sized'},
    {'name': 'Small Tent World', 'tl': 12, 'size_code': None,
     'description': 'Paraterraforming on small (up to Size 2) worlds'},
    {'name': 'Tent World', 'tl': 13, 'size_code': None,
     'description': 'Paraterraforming on terrestrial-sized worlds'},
    {'name': 'Small Ring Moon', 'tl': 14, 'size_code': '0',
     'description': 'Orbital height ring around small (up to Size 2) worlds'},
    {'name': 'Tiered World', 'tl': 14, 'size_code': None,
     'description': 'Multiple levels of world-encompassing shells'},
    {'name': 'Ring Moon', 'tl': 16, 'size_code': '0',
     'description': 'Orbital height ring around terrestrial-sized worlds'},
    {'name': 'Small Orbital', 'tl': 18, 'size_code': 'X',
     'description': 'Free rotating ring up to 10,000km diameter (Halo Orbital)'},
    {'name': 'Orbital', 'tl': 22, 'size_code': 'X',
     'description': 'Free rotating ring up to 2,000,000km diameter (Banks Orbital)'},
    {'name': 'Rosette', 'tl': 24, 'size_code': None,
     'description': 'Multiple worlds in single orbit (all of same Size code)'},
    {'name': 'Artificial World', 'tl': 26, 'size_code': None,
     'description': 'Created planet-sized construct (Size varies)'},
    {'name': 'Small Ringworld', 'tl': 26, 'size_code': 'X',
     'description': 'Sun encompassing ring (red dwarf habitable zone only)'},
    {'name': 'Ringworld', 'tl': 27, 'size_code': 'X',
     'description': 'Sun encompassing ring (any main sequence star)'},
    {'name': 'Small Dyson Sphere', 'tl': 28, 'size_code': 'X',
     'description': 'Sun encompassing rigid sphere (red dwarf habitable zone only)'},
    {'name': 'Dyson Sphere', 'tl': 29, 'size_code': 'X',
     'description': 'Sun encompassing rigid sphere (any main sequence star)'},
]


def generate_artificial_world(max_tech_level: int = 15,
                              host_size_code: str = '5') -> PlanetaryBody:
    """An artificial structure the given Tech Level could have built
    (WBH pp.231-232)."""
    feasible = [t for t in ARTIFICIAL_WORLD_TYPES if t['tl'] <= max_tech_level]
    if not feasible:
        feasible = ARTIFICIAL_WORLD_TYPES[:1]
    chosen = random.choice(feasible)
    body = PlanetaryBody(name=chosen['name'], body_type='Artificial')
    body.size_code = chosen['size_code'] if chosen['size_code'] is not None else host_size_code
    body.notes.append(f"Artificial world (TL{chosen['tl']}): {chosen['description']}")
    return body


# ---------------------------------------------------------- jump restrictions

# Empty Hex Jump DMs (WBH p.223): the additional Astrogation check for an
# accurate jump to a specific deep-space location.
EMPTY_HEX_JUMP_DMS = {
    'White Dwarf': -2,
    'Brown Dwarf': -2,
    'Neutron Star': -3,
    'Pulsar': -3,
    'Black Hole': -3,
    'Gas Giant': -3,
    'Terrestrial': -4,
    'Asteroid': -6,
    'Comet': -6,
    'Station': -6,
    'Deep Space': -6,
}

PREPARED_JUMP_TEMPLATE_DM = 4


def jump_dm_for_target(target: str) -> int:
    """The target-type DM on the extra Astrogation check for a jump to an
    empty hex (WBH p.223)."""
    return EMPTY_HEX_JUMP_DMS.get(target, -6)


def jump_restrictions(system: StellarSystem) -> List[str]:
    """The jump caveats a system's stars impose (WBH pp.224-229): protostar
    and primordial debris, pulsar and black hole shadows, systems with no
    hydrogen-burning anchor."""
    notes = []
    kinds = [s.spectral_type for s in system.stars if not s.is_composite]
    normal = any(' ' in k for k in kinds if k)  # e.g. 'G2 V'
    if system.age_gyr and system.age_gyr < 0.01:
        notes.append("Protostar system: empty-hex jump procedure with DM-6 "
                     "and DM-1D to Astrogation; DM-4 to Engineer (j-drive) "
                     "in and out")
    elif system.age_gyr and system.age_gyr < 0.1:
        notes.append("Primordial system: DM-2 to Astrogation and "
                     "Engineer (j-drive)")
    if any(k in ('Pulsar', 'Black Hole') for k in kinds):
        notes.append("Pulsar/black hole jump shadow: DM-4 to all Astrogation "
                     "and Engineer (j-drive) checks to and from this system")
    if not normal and kinds:
        notes.append("No hydrogen-burning star: Empty Hex Jump DMs apply")
    return notes
