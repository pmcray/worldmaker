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
    
    # 6-field technological matrix (this project's own construct, not a WBH
    # procedure - see generate_expanded_tech_matrix)
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
    name: str = ""
    designation: str = ""
    parent_body: Any = None # Forward reference to PlanetaryBody
    is_ring: bool = False
    size_code: str = ""
    orbit_pd: float = 0.0
    period_hours: float = 0.0
    eccentricity: float = 0.0
    retrograde: bool = False
    ring_width_pd: float = 0.0
    habitability_rating: int = 0
    # A significant moon can be the system mainworld, so it carries the same
    # physical and biological characteristics as a planet.
    core_composition: str = ""
    escape_velocity_kms: float = 0.0
    gases_retained: List[str] = field(default_factory=list)
    climate_zone: str = ""
    resource_rating: int = 0
    biomass_rating: int = 0
    biocomplexity_rating: int = 0
    biomes: List[str] = field(default_factory=list)
    cultural_profile: Any = None
    # Native lifeform ratings (WBH pp.127-131)
    biodiversity_rating: int = 0
    compatibility_rating: int = 0
    native_lifeform_profile: str = ""
    native_sophont: bool = False
    extinct_sophont: bool = False
    # Planetoid belt profile (WBH pp.72-75)
    belt_span: float = 0.0
    belt_composition: Dict[str, int] = field(default_factory=dict)
    belt_bulk: int = 0
    belt_profile: str = ""
    size_1_bodies: int = 0
    size_s_bodies: int = 0
    # Detailed temperature and seismology (WBH pp.107-128)
    albedo: float = 0.0
    greenhouse_factor: float = 0.0
    high_temperature: float = 0.0
    low_temperature: float = 0.0
    axial_tilt_factor: float = 0.0
    rotation_factor: float = 0.0
    geographic_factor: float = 0.0
    variance_factors: float = 0.0
    atmospheric_factor: float = 0.0
    luminosity_modifier: float = 0.0
    residual_seismic_stress: float = 0.0
    surface_tide_metres: float = 0.0
    tidal_stress_factor: float = 0.0
    tidal_heating_factor: float = 0.0
    total_seismic_stress: float = 0.0
    tectonic_plates: int = 0
    seismic_activity: str = ""
    # Temperature scenarios (WBH pp.114-124)
    worst_case_high: float = 0.0
    worst_case_low: float = 0.0
    latitude_temperatures: Dict[int, float] = field(default_factory=dict)
    # Expanded atmosphere characteristics (WBH pp.78-98)
    atmosphere_name: str = ""
    atmos_pressure_bar: float = 0.0
    oxygen_fraction: float = 0.0
    partial_pressure_oxygen: float = 0.0
    scale_height_km: float = 0.0
    atmosphere_composition: str = ""
    atmosphere_subtype: str = ""
    atmosphere_taint: Optional[Dict[str, str]] = None
    survival_gear: str = ""
    minimum_safe_altitude_km: float = 0.0
    safe_altitude_below_mean_km: float = 0.0
    low_oxygen: bool = False
    # Secondary world populations (WBH p.155)
    is_secondary_world: bool = False
    affiliated: bool = False
    # Nations on a balkanised world (WBH pp.155-156)
    nations: List[Any] = field(default_factory=list)
    nation_count: int = 0
    # Privately held worlds (see findworld.make_proprietary)
    proprietor: Optional[Dict[str, Any]] = None
    # Population detail (WBH pp.148-156)
    pcr: int = 0
    pcr_description: str = ""
    urbanisation_pct: int = 0
    urban_population: int = 0
    major_cities: List[Dict[str, Any]] = field(default_factory=list)
    population_profile: str = ""
    minimum_sustainable_tl: int = 0
    # Technology profile (WBH pp.173-180)
    tech_high: int = 0
    tech_low: int = 0
    tech_energy: int = 0
    tech_electronics: int = 0
    tech_manufacturing: int = 0
    tech_medical: int = 0
    tech_environmental: int = 0
    tech_land: int = 0
    tech_sea: int = 0
    tech_air: int = 0
    tech_space: int = 0
    tech_personal: int = 0
    tech_heavy: int = 0
    tech_novelty: int = 0
    technology_profile: str = ""
    # Starport facilities and military (WBH pp.193-208)
    starport_facilities: Dict[str, Any] = field(default_factory=dict)
    military_branches: Dict[str, int] = field(default_factory=dict)
    military_budget_pct: float = 0.0
    military_budget: float = 0.0
    state_of_readiness: str = ""
    military_profile: str = ""
    # Economic extension (WBH pp.185-199)
    importance: int = 0
    resources: int = 0
    labour: int = 0
    infrastructure: int = 0
    efficiency: int = 0
    resource_units: int = 0
    wtn: int = 0
    population_digit: int = 0
    total_population: int = 0
    gwp_per_capita: float = 0.0
    gwp: float = 0.0
    inequality_rating: int = 0
    development_score: float = 0.0
    tariff_rate: float = 0.0
    economic_extension: str = ""
    # Government and law detail (WBH pp.156-172)
    government_type: str = ""
    government_structure: str = ""
    government_profile: str = ""
    centralisation: str = ""
    primary_authority: str = ""
    factions: List[Dict[str, Any]] = field(default_factory=list)
    justice_primary: str = ""
    justice_secondary: str = ""
    justice_profile: str = ""
    law_uniformity: str = ""
    law_profile: str = ""
    law_weapons: int = 0
    law_economic: int = 0
    law_criminal: int = 0
    law_private: int = 0
    law_personal_rights: int = 0
    presumption_of_innocence: bool = False
    death_penalty: bool = False

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
    # Sophont Physical Characteristics D66 results (SCG pp.52-54)
    symmetry: str = ""
    limb_count: str = ""
    manipulators: str = ""
    environment: str = ""
    behaviour: str = ""
    gender: str = ""
    characteristic_rolls: Dict[str, Any] = field(default_factory=dict)
    characteristic_dms: Dict[str, int] = field(default_factory=dict)

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
    age_centuries: float = 0
    wave_type: str = "" # "thin" or "thick"
    propagation_rate: float = 0.0 # parsecs per century
    # Extended historical & directional fields (SCG pp. 22-27)
    wave_id: str = ""
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    entry_edge: Optional[str] = None # None | "coreward" | "rimward" | "spinward" | "trailing"
    max_radius: Optional[int] = None # Optional cap on propagation distance in parsecs
    subsectors: Optional[List[str]] = None # Optional subsector corridor filter (e.g. ["A", "B", "C"])
    culture_sphere: str = ""         # e.g. "Zhodani", "Imperial (Vilani/Solomani)"
    allegiance_imprint: str = ""     # Optional allegiance hint (e.g. "ZhIN", "CsIm", "Na")
    epoch_label: str = ""            # e.g. "Epoch II (-4000 to -1000)"
    description: str = ""            # Historical narrative of this wave
    distance_decay: bool = False     # When True, local_age = age_centuries - distance / propagation_rate
    enabled: bool = True

    @property
    def velocity_parsecs_per_century(self) -> float:
        return self.propagation_rate

    def distance_to(self, hex_coord: str, width: int = 32, height: int = 40) -> int:
        """Distance in parsecs from the wave's entry edge or point origin."""
        col, row = int(hex_coord[:2]), int(hex_coord[2:])
        if self.entry_edge == "coreward":
            return max(0, row - 1)
        if self.entry_edge == "rimward":
            return max(0, height - row)
        if self.entry_edge == "spinward":
            return max(0, col - 1)
        if self.entry_edge == "trailing":
            return max(0, width - col)
        if not self.origin_hex:
            return 0
        c2, r2 = int(self.origin_hex[:2]), int(self.origin_hex[2:])
        x1 = col
        z1 = row - (col + (col % 2)) // 2
        y1 = -x1 - z1
        x2 = c2
        z2 = r2 - (c2 + (c2 % 2)) // 2
        y2 = -x2 - z2
        return max(abs(x1 - x2), abs(y1 - y2), abs(z1 - z2))

    def reaches(self, hex_coord: str, width: int = 32, height: int = 40) -> bool:
        """Whether this settlement wave has reached `hex_coord`."""
        if not self.enabled:
            return False
        if self.subsectors:
            col, row = int(hex_coord[:2]), int(hex_coord[2:])
            sub_idx = ((row - 1) // 10) * 4 + ((col - 1) // 8)
            sub_letter = chr(ord("A") + sub_idx) if 0 <= sub_idx < 16 else "?"
            if sub_letter not in self.subsectors:
                return False
        dist = self.distance_to(hex_coord, width, height)
        if self.max_radius is not None and dist > self.max_radius:
            return False
        return dist <= (self.propagation_rate * self.age_centuries)

    def local_age_centuries(self, hex_coord: str, width: int = 32, height: int = 40) -> float:
        """How many centuries ago the wave arrived at `hex_coord`."""
        if not self.distance_decay or self.propagation_rate <= 0:
            return float(self.age_centuries)
        dist = self.distance_to(hex_coord, width, height)
        return max(0.0, float(self.age_centuries) - (dist / self.propagation_rate))

    def arrival_year(self, hex_coord: str, current_year: int = 1105,
                     width: int = 32, height: int = 40) -> int:
        """Estimated Imperial year this wave reached `hex_coord`."""
        base_start = (self.start_year if self.start_year is not None
                      else int(round(current_year - self.age_centuries * 100)))
        if self.distance_decay and self.propagation_rate > 0:
            dist = self.distance_to(hex_coord, width, height)
            arr = int(round(base_start + (dist / self.propagation_rate) * 100))
            if self.end_year is not None:
                arr = min(arr, self.end_year)
            return min(arr, current_year)
        return base_start

    def population_dm_at(self, hex_coord: str, width: int = 32,
                         height: int = 40) -> Optional[int]:
        """SCG p.22 population DM at `hex_coord` (thin: -5 + 1/century;
        thick: -3 + 1/century; capped at 0), or None if the wave has not
        reached `hex_coord`."""
        if not self.reaches(hex_coord, width, height):
            return None
        age = self.local_age_centuries(hex_coord, width, height)
        if self.wave_type == "thin":
            return min(0, int(-5 + int(age)))
        if self.wave_type == "thick":
            cap = 1 if self.distance_decay else 0
            return min(cap, int(-3 + int(age)))
        return 0

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
    habitability_rating: int = 0
    hill_sphere_pd: float = 0.0
    hill_sphere_moon_limit_pd: float = 0.0
    ring_profile: str = ""
    # Native lifeform ratings (WBH pp.127-131)
    biodiversity_rating: int = 0
    compatibility_rating: int = 0
    native_lifeform_profile: str = ""
    native_sophont: bool = False
    extinct_sophont: bool = False
    # Planetoid belt profile (WBH pp.72-75)
    belt_span: float = 0.0
    belt_composition: Dict[str, int] = field(default_factory=dict)
    belt_bulk: int = 0
    belt_profile: str = ""
    size_1_bodies: int = 0
    size_s_bodies: int = 0
    # Detailed temperature and seismology (WBH pp.107-128)
    albedo: float = 0.0
    greenhouse_factor: float = 0.0
    high_temperature: float = 0.0
    low_temperature: float = 0.0
    axial_tilt_factor: float = 0.0
    rotation_factor: float = 0.0
    geographic_factor: float = 0.0
    variance_factors: float = 0.0
    atmospheric_factor: float = 0.0
    luminosity_modifier: float = 0.0
    residual_seismic_stress: float = 0.0
    surface_tide_metres: float = 0.0
    tidal_stress_factor: float = 0.0
    tidal_heating_factor: float = 0.0
    total_seismic_stress: float = 0.0
    tectonic_plates: int = 0
    seismic_activity: str = ""
    # Temperature scenarios (WBH pp.114-124)
    worst_case_high: float = 0.0
    worst_case_low: float = 0.0
    latitude_temperatures: Dict[int, float] = field(default_factory=dict)
    # Expanded atmosphere characteristics (WBH pp.78-98)
    atmosphere_name: str = ""
    atmos_pressure_bar: float = 0.0
    oxygen_fraction: float = 0.0
    partial_pressure_oxygen: float = 0.0
    scale_height_km: float = 0.0
    atmosphere_composition: str = ""
    atmosphere_subtype: str = ""
    atmosphere_taint: Optional[Dict[str, str]] = None
    survival_gear: str = ""
    minimum_safe_altitude_km: float = 0.0
    safe_altitude_below_mean_km: float = 0.0
    low_oxygen: bool = False
    # Secondary world populations (WBH p.155)
    is_secondary_world: bool = False
    affiliated: bool = False
    # Nations on a balkanised world (WBH pp.155-156)
    nations: List[Any] = field(default_factory=list)
    nation_count: int = 0
    # Privately held worlds (see findworld.make_proprietary)
    proprietor: Optional[Dict[str, Any]] = None
    # Population detail (WBH pp.148-156)
    pcr: int = 0
    pcr_description: str = ""
    urbanisation_pct: int = 0
    urban_population: int = 0
    major_cities: List[Dict[str, Any]] = field(default_factory=list)
    population_profile: str = ""
    minimum_sustainable_tl: int = 0
    # Technology profile (WBH pp.173-180)
    tech_high: int = 0
    tech_low: int = 0
    tech_energy: int = 0
    tech_electronics: int = 0
    tech_manufacturing: int = 0
    tech_medical: int = 0
    tech_environmental: int = 0
    tech_land: int = 0
    tech_sea: int = 0
    tech_air: int = 0
    tech_space: int = 0
    tech_personal: int = 0
    tech_heavy: int = 0
    tech_novelty: int = 0
    technology_profile: str = ""
    # Starport facilities and military (WBH pp.193-208)
    starport_facilities: Dict[str, Any] = field(default_factory=dict)
    military_branches: Dict[str, int] = field(default_factory=dict)
    military_budget_pct: float = 0.0
    military_budget: float = 0.0
    state_of_readiness: str = ""
    military_profile: str = ""
    # Economic extension (WBH pp.185-199)
    importance: int = 0
    resources: int = 0
    labour: int = 0
    infrastructure: int = 0
    efficiency: int = 0
    resource_units: int = 0
    wtn: int = 0
    population_digit: int = 0
    total_population: int = 0
    gwp_per_capita: float = 0.0
    gwp: float = 0.0
    inequality_rating: int = 0
    development_score: float = 0.0
    tariff_rate: float = 0.0
    economic_extension: str = ""
    # Government and law detail (WBH pp.156-172)
    government_type: str = ""
    government_structure: str = ""
    government_profile: str = ""
    centralisation: str = ""
    primary_authority: str = ""
    factions: List[Dict[str, Any]] = field(default_factory=list)
    justice_primary: str = ""
    justice_secondary: str = ""
    justice_profile: str = ""
    law_uniformity: str = ""
    law_profile: str = ""
    law_weapons: int = 0
    law_economic: int = 0
    law_criminal: int = 0
    law_private: int = 0
    law_personal_rights: int = 0
    presumption_of_innocence: bool = False
    death_penalty: bool = False

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
    metallicity_feh: float = 0.0 # [Fe/H] in dex (Sol = 0.00)
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
    metallicity_feh: float = 0.0 # [Fe/H] in dex (Sol = 0.00)
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
    hex_coord: str = ""
    subsector_code: str = ""
    subsector_name: str = ""
    travel_zone: str = ""  # "" = Green, "A" = Amber, "R" = Red
    has_highport: bool = False
    settlement_epoch: str = ""
    settlement_wave: str = ""
    settlement_strata: List[Dict[str, Any]] = field(default_factory=list)
    population_dm: int = 0
    historical_notes: List[str] = field(default_factory=list)
    corporations: List[str] = field(default_factory=list)
    pbg: str = ""

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

    @property
    def all_bodies(self):
        """Every world in the system plus every satellite, since a significant
        moon can itself be the mainworld (WBH p.133)."""
        bodies = []
        for world in self.all_worlds:
            bodies.append(world)
            bodies.extend(world.satellites)
        return bodies

    @property
    def mainworld(self):
        """The system's mainworld, whether it is a planet or a moon."""
        return next((b for b in self.all_bodies if b.is_mainworld), None)

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
    subsector_names: Dict[str, str] = field(default_factory=dict)
    # Empty-hex surveys (WBH pp.219-223): hex -> EmptyHexSurvey
    deep_space: Dict[str, Any] = field(default_factory=dict)
    # Worlds served by a courier network based outside this sector:
    # (hex, route style)
    off_sector_routes: List[Tuple[str, str]] = field(default_factory=list)
    macro_history: List[Dict[str, Any]] = field(default_factory=list)
    erith_hex: str = ""
    solar_analogue_hex: str = ""
    solar_system_analogue_hex: str = ""
    solar_analogues: List[Dict[str, Any]] = field(default_factory=list)
    solar_system_analogues: List[Dict[str, Any]] = field(default_factory=list)
    earth_analogues: List[Dict[str, Any]] = field(default_factory=list)
    corporations: List[Dict[str, Any]] = field(default_factory=list)
    scenario_config: Optional[Any] = None
