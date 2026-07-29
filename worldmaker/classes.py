from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple, Optional

@dataclass
class UWP:
    starport: str = "X"
    size: str = "0"
    atmosphere: str = "0"
    hydrographics: str = "0"
    population: str = "0"
    government: str = "0"
    law_level: str = "0"
    tech_level: str = "0"
    
    # Expanded 6-field technological matrix (WBH rules)
    tl_spaceflight: int = 0
    tl_energy: int = 0
    tl_transport: int = 0
    tl_medical: int = 0
    tl_environment: int = 0
    tl_personal: int = 0

    def __str__(self):
        return f"{self.starport}{self.size}{self.atmosphere}{self.hydrographics}{self.population}{self.government}{self.law_level}-{self.tech_level}"

@dataclass
class Satellite:
    designation: str = ""
    parent_body: Any = None # Forward reference to PlanetaryBody
    is_ring: bool = False
    size_code: str = ""
    orbit_pd: float = 0.0
    period_hours: float = 0.0
    notes: List[str] = field(default_factory=list)
    # Physical properties
    diameter_km: float = 0.0
    mass_terran: float = 0.0
    gravity: float = 0.0
    density: float = 0.0
    axial_tilt: float = 0.0
    rotation_period_hours: float = 0.0
    mean_temperature: float = 0.0
    surface_features: str = ""
    life_details: str = ""
    atmosphere_code: str = ""
    hydrographics_code: str = ""
    provisional_temp: str = ""
    uwp: UWP = field(default_factory=UWP)
    is_mainworld: bool = False
    trade_codes: List[str] = field(default_factory=list)

@dataclass
class CulturalProfile:
    diversity: int = 0
    xenophilia: int = 0
    uniqueness: int = 0
    symbology: int = 0
    cohesion: int = 0
    progressiveness: int = 0
    expansionism: int = 0
    militancy: int = 0

@dataclass
class Sophont:
    name: str = ""
    homeworld_hex: str = ""
    is_major: bool = False
    
    # Expanded biology and morphology (SCG pp. 50-60)
    morphology: str = ""          # Bilateral, Radial, etc.
    limbs: str = ""               # Number of arms/legs/tentacles
    sensory_organs: List[str] = field(default_factory=list)
    reproduction: str = ""         # Sexual, Asexual, Budding, etc.
    diet: str = ""                # Carnivore, Herbivore, Omnivore, etc.
    psychology: str = ""           # Social instinct, Aggression level
    evolutionary_track: str = ""   # Aquatic, Plains, Desert, etc.
    history_summary: str = ""

@dataclass
class Polity:
    name: str = ""
    capital_hex: str = ""
    allegiance_code: str = "Na"
    controlled_systems: List[str] = field(default_factory=list)
    polity_type: str = "Interstellar" # Pocket Empire, Major Race Polity, etc.
    defense_index: int = 0
    trade_routes: List[Tuple[str, str]] = field(default_factory=list)

@dataclass
class Wave:
    name: str = ""
    origin_hex: str = ""
    age_centuries: int = 0
    wave_type: str = "" # "thin" or "thick"
    propagation_rate: float = 0.0 # parsecs per century

@dataclass
class PlanetaryBody:
    name: str = ""
    designation: str = ""
    parent_star_group: str = "" # e.g., 'Aab', 'B', 'Cab'
    body_type: str = "" # Terrestrial, Gas Giant, Planetoid Belt
    orbit_num: float = 0.0
    orbit_au: float = 0.0
    eccentricity: float = 0.0
    inclination: float = 0.0
    period_years: float = 0.0
    size_code: str = ""
    diameter_km: float = 0.0
    density: float = 0.0
    gravity: float = 0.0
    mass_terran: float = 0.0
    axial_tilt: float = 0.0
    rotation_period_hours: float = 0.0
    mean_temperature: float = 0.0
    surface_features: str = ""
    life_details: str = ""
    satellites: List[Satellite] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    trade_codes: List[str] = field(default_factory=list)
    # WBH Physical parameters
    core_composition: str = ""
    escape_velocity_kms: float = 0.0
    gases_retained: List[str] = field(default_factory=list)
    climate_zone: str = ""
    resource_rating: int = 0
    biomass_rating: int = 0
    biocomplexity_rating: int = 0
    biomes: List[str] = field(default_factory=list)
    # Detailed properties for mainworld candidates
    atmosphere_code: str = ""
    hydrographics_code: str = ""
    provisional_temp: str = ""
    uwp: UWP = field(default_factory=UWP)
    cultural_profile: CulturalProfile = field(default_factory=CulturalProfile)
    is_mainworld: bool = False

@dataclass
class Star:
    designation: str = ""
    is_composite: bool = False
    components: List[str] = field(default_factory=list)
    spectral_type: str = ""
    mass: float = 0.0 # Solar masses
    diameter: float = 0.0 # Solar diameters
    luminosity: float = 0.0 # Solar luminosity
    temp_k: float = 0.0
    # Orbital info if secondary
    parent: Optional['Star'] = None
    orbit_class: str = "" # Close, Near, Far, Companion
    orbit_num: float = 0.0
    eccentricity: float = 0.0
    period_years: float = 0.0
    # World-building info
    hzco: float = 0.0
    mao: float = 0.0 # Minimum Allowable Orbit#
    available_orbits: List[Tuple[float, float]] = field(default_factory=list)
    orbiting_bodies: List[PlanetaryBody] = field(default_factory=list)

@dataclass
class StellarSystem:
    name: str = "Generated System"
    age_gyr: float = 0.0
    stars: List[Star] = field(default_factory=list)
    gas_giant_count: int = 0
    planetoid_belt_count: int = 0
    terrestrial_planet_count: int = 0
    empty_orbit_count: int = 0
    anomalous_planets: list = field(default_factory=list)
    total_worlds: int = 0
    baseline_number: int = 0
    baseline_orbit: float = 0.0
    spread: float = 0.0
    allegiance: str = "Na"
    bases: List[str] = field(default_factory=list)
    travel_zone: str = ""  # "" = Green, "A" = Amber, "R" = Red

    @property
    def primary_star(self):
        return self.stars[0] if self.stars else None
    
    @property
    def all_worlds(self):
        worlds = []
        for star in self.stars:
            if not star.is_composite:
                worlds.extend(star.orbiting_bodies)
        return worlds

@dataclass
class Sector:
    name: str = "Generated Sector"
    width: int = 8
    height: int = 10
    systems: Dict[str, StellarSystem] = field(default_factory=dict)
    native_sophonts: Dict[str, Sophont] = field(default_factory=dict)
    settlement_waves: List[Wave] = field(default_factory=list)
    routes: List[Tuple[str, str, str]] = field(default_factory=list) # (hex1, hex2, type)
    polities: List[Polity] = field(default_factory=list)
