#!/usr/bin/env python
# coding: utf-8

# # Traveller World Generator

# ## I. Imports and Setup

# In[1]:


import random
import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple, Optional



# ## II. Core Utility Library

# In[2]:


class Utils:
    """Houses all common, low-level functions."""
    
    @staticmethod
    def D6(n=1): # 1D, 2D, etc.
        return sum(random.randint(1, 6) for _ in range(n))

    @staticmethod
    def D3():
        return random.randint(1, 3)
        
    @staticmethod
    def d10(): # Returns 0-9
        return random.randint(0, 9)

    @staticmethod
    def eHex(value):
        if 0 <= value <= 9:
            return str(value)
        ehex_map = {
            10: 'A', 11: 'B', 12: 'C', 13: 'D', 14: 'E', 15: 'F', 16: 'G',
            17: 'H', 18: 'J', 19: 'K', 20: 'L', 21: 'M', 22: 'N', 23: 'P',
            24: 'Q', 25: 'R', 26: 'S', 27: 'T', 28: 'U', 29: 'V', 30: 'W',
            31: 'X', 32: 'Y', 33: 'Z'
        }
        return ehex_map.get(value, str(value))

    ORBIT_TABLE = {
        0: {'dist': 0.0, 'diff': 0.4},
        1: {'dist': 0.4, 'diff': 0.3},
        2: {'dist': 0.7, 'diff': 0.3},
        3: {'dist': 1.0, 'diff': 0.6},
        4: {'dist': 1.6, 'diff': 1.2},
        5: {'dist': 2.8, 'diff': 2.4},
        6: {'dist': 5.2, 'diff': 4.8},
        7: {'dist': 10.0, 'diff': 10.0},
        8: {'dist': 20.0, 'diff': 20.0},
        9: {'dist': 40.0, 'diff': 37.0},
        10: {'dist': 77.0, 'diff': 77.0},
        11: {'dist': 154.0, 'diff': 154.0},
        12: {'dist': 308.0, 'diff': 307.0},
        13: {'dist': 615.0, 'diff': 615.0},
        14: {'dist': 1230.0, 'diff': 1270.0},
        15: {'dist': 2500.0, 'diff': 2400.0},
        16: {'dist': 4900.0, 'diff': 4900.0},
        17: {'dist': 9800.0, 'diff': 9700.0},
        18: {'dist': 19500.0, 'diff': 20000.0},
        19: {'dist': 39500.0, 'diff': 39200.0},
        20: {'dist': 78700.0, 'diff': 0.0} # End of table
    }

    @classmethod
    def orbit_to_au(cls, orbit_num: float) -> float:
        """Converts Traveller Orbit# to Astronomical Units (AU)."""
        if orbit_num < 0: return 0.0
        whole_orbit = math.floor(orbit_num)
        fractional_part = orbit_num - whole_orbit
        
        base_dist = cls.ORBIT_TABLE.get(whole_orbit, {}).get('dist', 0)
        diff = cls.ORBIT_TABLE.get(whole_orbit, {}).get('diff', 0)
        
        return base_dist + (diff * fractional_part)

    @classmethod
    def au_to_orbit(cls, au: float) -> float:
        """Converts AU to Traveller Orbit#."""
        if au <= 0: return 0.0
        
        full_orbit = 0
        for i in range(21):
            if au >= cls.ORBIT_TABLE[i]['dist']:
                full_orbit = i
            else:
                break

        base_dist = cls.ORBIT_TABLE[full_orbit]['dist']
        diff = cls.ORBIT_TABLE[full_orbit]['diff']
        if diff == 0: return float(full_orbit)

        fractional_part = (au - base_dist) / diff
        return full_orbit + fractional_part

    @staticmethod
    def calculate_hzco(luminosity: float) -> float:
        """Calculates the Habitable Zone Center Orbit# (HZCO) in AU."""
        hzco_au = math.sqrt(luminosity)
        return Utils.au_to_orbit(hzco_au)

    @staticmethod
    def from_eHex(ehex_char):
        if ehex_char.isdigit():
            return int(ehex_char)
        ehex_map = {
            'A': 10, 'B': 11, 'C': 12, 'D': 13, 'E': 14, 'F': 15, 'G': 16,
            'H': 17, 'J': 18, 'K': 19, 'L': 20, 'M': 21, 'N': 22, 'P': 23,
            'Q': 24, 'R': 25, 'S': 26, 'T': 27, 'U': 28, 'V': 29, 'W': 30,
            'X': 31, 'Y': 32, 'Z': 33
        }
        return ehex_map.get(ehex_char.upper(), 0)



# ## III. System Data Model Definition

# In[3]:


@dataclass
class Satellite:
    designation: str = ""
    parent_body: Any = None # Forward reference
    is_ring: bool = False
    size_code: str = ""
    orbit_pd: float = 0.0
    period_hours: float = 0.0
    notes: List[str] = field(default_factory=list)
    # Physical properties for moon candidates
    diameter_km: float = 0.0
    mass_terran: float = 0.0
    gravity: float = 0.0
    atmosphere_code: str = ""
    hydrographics_code: str = ""
    provisional_temp: str = ""

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

    def __str__(self):
        return f"{self.starport}{self.size}{self.atmosphere}{self.hydrographics}{self.population}{self.government}{self.law_level}-{self.tech_level}"

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
    physical_characteristics: List[str] = field(default_factory=list)
    cultural_profile: CulturalProfile = field(default_factory=CulturalProfile)
    # Add more sophont-specific fields as needed

@dataclass
class Polity:
    name: str = ""
    capital_hex: str = ""
    controlled_systems: List[str] = field(default_factory=list)
    # Add more polity-specific fields as needed

@dataclass
class Wave:
    name: str = ""
    origin_hex: str = ""
    age_centuries: int = 0
    wave_type: str = "" # "thin" or "thick"
    propagation_rate: float = 0.0 # parsecs per century
    # Add more wave-specific fields as needed

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
    mass_terran: float = 0.0
    mean_temperature: float = 0.0
    surface_features: str = ""
    life_details: str = ""
    satellites: List[Satellite] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
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
    # Orbital info if not primary
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



# ## IV. Data Tables from Handbook

# In[4]:


# Data Tables from Handbook
DATA = {
    'star_type_determination': { # Page 16
        'Type': {2: 'Special', 3: 'M', 4: 'M', 5: 'M', 6: 'M', 7: 'K', 8: 'K', 9: 'G', 10: 'G', 11: 'F', 12: 'Hot'},
        'Hot': {2: 'A', 3: 'A', 4: 'A', 5: 'A', 6: 'A', 7: 'A', 8: 'A', 9: 'A', 10: 'B', 11: 'B', 12: 'O'},
        'Special': {2: 'A', 3: 'Class VI', 4: 'Class VI', 5: 'Class VI', 6: 'Class IV', 7: 'Class IV', 8: 'Class IV', 9: 'Class III', 10: 'Class III', 11: 'Giants', 12: 'Giants'},
        'Unusual': {2: 'Peculiar', 3: 'Peculiar', 4: 'Class IV', 5: 'BD', 6: 'BD', 7: 'BD', 8: 'D', 9: 'D', 10: 'D', 11: 'Class III', 12: 'Giants'},
        'Giants': {2: 'Class III', 3: 'Class III', 4: 'Class III', 5: 'Class III', 6: 'Class III', 7: 'Class III', 8: 'Class II', 9: 'Class II', 10: 'Class II', 11: 'Class Ib', 12: 'Class Ia'},
        'Peculiar': {1: 'Black Hole', 2: 'Neutron Star', 3: 'Pulsar', 4: 'Protostar', 5: 'Nebula', 6: 'Star Cluster'}
    },
    'star_subtype': { # Page 17
        'Numeric': {2: 0, 3: 1, 4: 3, 5: 5, 6: 7, 7: 9, 8: 8, 9: 6, 10: 4, 11: 2, 12: 0},
        'M-type': {2: 8, 3: 6, 4: 5, 5: 4, 6: 0, 7: 2, 8: 1, 9: 3, 10: 5, 11: 7, 12: 9}
    },
    'star_mass': { # Page 18, using Solar Masses
        'Ia': {'O0': 200, 'O5': 80, 'B0': 60, 'B5': 30, 'A0': 20, 'A5': 15, 'F0': 13, 'F5': 12, 'G0': 12, 'G5': 13, 'K0': 14, 'K5': 18, 'M0': 20, 'M5': 25, 'M9': 30},
        'Ib': {'O0': 150, 'O5': 60, 'B0': 40, 'B5': 25, 'A0': 15, 'A5': 13, 'F0': 12, 'F5': 10, 'G0': 10, 'G5': 11, 'K0': 12, 'K5': 13, 'M0': 15, 'M5': 20, 'M9': 25},
        'II': {'O0': 130, 'O5': 40, 'B0': 30, 'B5': 20, 'A0': 14, 'A5': 11, 'F0': 10, 'F5': 8, 'G0': 8, 'G5': 10, 'K0': 10, 'K5': 12, 'M0': 14, 'M5': 16, 'M9': 18},
        'III': {'O0': 110, 'O5': 30, 'B0': 20, 'B5': 10, 'A0': 8, 'A5': 6, 'F0': 4, 'F5': 3, 'G0': 2.5, 'G5': 2.4, 'K0': 1.1, 'K5': 1.5, 'M0': 1.8, 'M5': 2.4, 'M9': 8},
        'IV': {'B0': 20, 'B5': 10, 'A0': 4, 'A5': 2.3, 'F0': 2, 'F5': 1.5, 'G0': 1.7, 'G5': 1.2, 'K0': 1.5},
        'V': {'O0': 90, 'O5': 60, 'B0': 18, 'B5': 5, 'A0': 2.2, 'A5': 1.8, 'F0': 1.5, 'F5': 1.3, 'G0': 1.1, 'G5': 0.9, 'K0': 0.8, 'K5': 0.7, 'M0': 0.5, 'M5': 0.16, 'M9': 0.08},
        'VI': {'O0': 2, 'O5': 1.5, 'B0': 0.5, 'B5': 0.4, 'G0': 0.8, 'G5': 0.7, 'K0': 0.6, 'K5': 0.5, 'M0': 0.4, 'M5': 0.12, 'M9': 0.075}
    },
    'star_temp': { # Page 18, in Kelvin
        'Ia': {'O0': 50000, 'O5': 40000, 'B0': 25000, 'B5': 14000, 'A0': 9500, 'A5': 8500, 'F0': 7500, 'F5': 6500, 'G0': 5500, 'G5': 4700, 'K0': 4000, 'K5': 3500, 'M0': 3200, 'M5': 3000, 'M9': 2800},
        'Ib': {'O0': 50000, 'O5': 40000, 'B0': 22000, 'B5': 13000, 'A0': 9200, 'A5': 8200, 'F0': 7200, 'F5': 6200, 'G0': 5300, 'G5': 4500, 'K0': 3800, 'K5': 3300, 'M0': 3000, 'M5': 2800, 'M9': 2600},
        'II': {'O0': 50000, 'O5': 38000, 'B0': 20000, 'B5': 12000, 'A0': 9000, 'A5': 8000, 'F0': 7000, 'F5': 6000, 'G0': 5100, 'G5': 4300, 'K0': 3600, 'K5': 3100, 'M0': 2800, 'M5': 2600, 'M9': 2400},
        'III': {'O0': 48000, 'O5': 36000, 'B0': 18000, 'B5': 11000, 'A0': 8500, 'A5': 7500, 'F0': 6500, 'F5': 5500, 'G0': 4800, 'G5': 4100, 'K0': 3400, 'K5': 3000, 'M0': 2600, 'M5': 2400, 'M9': 2200},
        'IV': {'B0': 28000, 'B5': 14000, 'A0': 9500, 'A5': 7800, 'F0': 7000, 'F5': 6300, 'G0': 5800, 'G5': 5500, 'K0': 5000},
        'V': {'O0': 50000, 'O5': 40000, 'B0': 30000, 'B5': 15000, 'A0': 10000, 'A5': 8000, 'F0': 7500, 'F5': 6500, 'G0': 6000, 'G5': 5600, 'K0': 5200, 'K5': 4400, 'M0': 3700, 'M5': 3000, 'M9': 2400},
        'VI': {'O0': 40000, 'O5': 30000, 'B0': 20000, 'B5': 12000, 'G0': 5800, 'G5': 5400, 'K0': 5000, 'K5': 4200, 'M0': 3500, 'M5': 2800, 'M9': 2200}
    },
    'non_primary_star_determination': { # Page 29
        2: {'Secondary': 'Other', 'Companion': 'Other', 'Post-Stellar': 'D*'},
        3: {'Secondary': 'Other', 'Companion': 'Other', 'Post-Stellar': 'D'},
        4: {'Secondary': 'Random', 'Companion': 'Random', 'Post-Stellar': 'D'},
        5: {'Secondary': 'Random', 'Companion': 'Random', 'Post-Stellar': 'D'},
        6: {'Secondary': 'Random', 'Companion': 'Lesser', 'Post-Stellar': 'D'},
        7: {'Secondary': 'Lesser', 'Companion': 'Lesser', 'Post-Stellar': 'D'},
        8: {'Secondary': 'Lesser', 'Companion': 'Sibling', 'Post-Stellar': 'BD'},
        9: {'Secondary': 'Sibling', 'Companion': 'Sibling', 'Post-Stellar': 'BD'},
        10: {'Secondary': 'Sibling', 'Companion': 'Twin', 'Post-Stellar': 'BD'},
        11: {'Secondary': 'Twin', 'Companion': 'Twin', 'Post-Stellar': 'BD'},
        12: {'Secondary': 'Twin', 'Companion': 'Twin', 'Post-Stellar': 'BD'}
    },
    'star_diameter': { # Page 19, in Solar Diameters
        'Ia': {'O0': 25, 'O5': 22, 'B0': 20, 'B5': 60, 'A0': 120, 'A5': 180, 'F0': 210, 'F5': 280, 'G0': 330, 'G5': 360, 'K0': 420, 'K5': 600, 'M0': 900, 'M5': 1200, 'M9': 1800},
        'Ib': {'O0': 24, 'O5': 20, 'B0': 14, 'B5': 25, 'A0': 50, 'A5': 75, 'F0': 85, 'F5': 115, 'G0': 135, 'G5': 150, 'K0': 180, 'K5': 260, 'M0': 380, 'M5': 600, 'M9': 800},
        'II': {'O0': 22, 'O5': 18, 'B0': 12, 'B5': 14, 'A0': 30, 'A5': 45, 'F0': 50, 'F5': 66, 'G0': 77, 'G5': 90, 'K0': 110, 'K5': 160, 'M0': 230, 'M5': 350, 'M9': 500},
        'III': {'O0': 21, 'O5': 15, 'B0': 10, 'B5': 6, 'A0': 5, 'A5': 5, 'F0': 5, 'F5': 5, 'G0': 10, 'G5': 15, 'K0': 20, 'K5': 40, 'M0': 60, 'M5': 100, 'M9': 200},
        'IV': {'B0': 8, 'B5': 5, 'A0': 4, 'A5': 3, 'F0': 3, 'F5': 2, 'G0': 3, 'G5': 4, 'K0': 6},
        'V': {'O0': 20, 'O5': 12, 'B0': 7, 'B5': 3.5, 'A0': 2.2, 'A5': 2.0, 'F0': 1.7, 'F5': 1.5, 'G0': 1.1, 'G5': 0.95, 'K0': 0.9, 'K5': 0.8, 'M0': 0.7, 'M5': 0.2, 'M9': 0.1},
        'VI': {'O0': 0.18, 'O5': 0.18, 'B0': 0.2, 'B5': 0.5, 'G0': 0.8, 'G5': 0.7, 'K0': 0.6, 'K5': 0.5, 'M0': 0.4, 'M5': 0.1, 'M9': 0.08}
    },
    'gas_giant_quantity': { # Page 37 
        'roll_map': {4: 1, 5: 2, 6: 2, 7: 3, 8: 3, 9: 4, 10: 4, 11: 4, 12: 5, 13: 6},
        'min_roll': 4, 'max_roll': 13
    },
    'planetoid_belt_quantity': { # Page 37 
        'roll_map': {6: 1, 7: 2, 8: 2, 9: 2, 10: 2, 11: 2, 12: 3},
        'min_roll': 6, 'max_roll': 12
    },
    'eccentricity_values': { # Page 27 
        5: {'base': -0.001, 'roll': lambda: Utils.D6() / 1000},
        7: {'base': 0.00, 'roll': lambda: Utils.D6() / 200},
        9: {'base': 0.03, 'roll': lambda: Utils.D6() / 100},
        10: {'base': 0.05, 'roll': lambda: Utils.D6(2) / 20},
        11: {'base': 0.05, 'roll': lambda: Utils.D6(2) / 20},
        12: {'base': 0.30, 'roll': lambda: Utils.D6(2) / 20},
    },
    'terrestrial_sizing': { # Page 54 
        1: lambda: Utils.D6(),
        2: lambda: Utils.D6(),
        3: lambda: Utils.D6(2),
        4: lambda: Utils.D6(2),
        5: lambda: Utils.D6(2) + 3,
        6: lambda: Utils.D6(2) + 3
    },
    'terrestrial_world_sizing': { # Page 54
        '1D_roll': {1: '1D', 2: '1D', 3: '2D', 4: '2D', 5: '2D+3', 6: '2D+3'},
        'size_ranges': {
            '1D': {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6},
            '2D': {2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 8, 9: 9, 10: 10, 11: 11, 12: 12},
            '2D+3': {5: 5, 6: 6, 7: 7, 8: 8, 9: 9, 10: 10, 11: 11, 12: 12, 13: 13, 14: 14, 15: 15}
        }
    },
    'gas_giant_sizing': { # Page 55 
        'GS': {'d_roll': lambda: Utils.D3() + Utils.D3(), 'm_roll': lambda: 5 * (Utils.D6() + 1)},
        'GM': {'d_roll': lambda: Utils.D6() + 6, 'm_roll': lambda: 20 * (Utils.D6(3) - 1)},
        'GL': {'d_roll': lambda: Utils.D6(2) + 6, 'm_roll': lambda: Utils.D3() * 50 * (Utils.D6(3) + 4)}
    },
    'significant_moon_quantity': { # Page 55
        'planet_size_1_2': lambda: Utils.D6() - 5,
        'planet_size_3_9': lambda: Utils.D6(2) - 8,
        'planet_size_a_f': lambda: Utils.D6(2) - 6,
        'small_gas_giant': lambda: Utils.D6(3) - 7,
        'medium_large_gas_giant': lambda: Utils.D6(4) - 6,
        'dms': {
            'orbit_less_than_1': -1,
            'adjacent_companion': -1,
            'adjacent_unavailability': -1,
            'adjacent_outermost': -1
        }
    }
}


# ## V. Generation Functions

# In[5]:


def generate_world_name():
    prefixes = ["Ard", "Bor", "Cor", "Den", "Eth", "Fen", "Gor", "Hen", "Ish", "Jen", "Kel", "Lor", "Mor", "Nor", "Orr", "Per", "Quor", "Ren", "Sor", "Tor", "Ur", "Ver", "Wor", "Xen", "Yor", "Zor"]
    suffixes = ["ia", "os", "a", "us", "is", "en", "or", "an", "el", "ar"]
    return random.choice(prefixes) + random.choice(suffixes)


def generate_world_name():
    prefixes = ["Ard", "Bor", "Cor", "Den", "Eth", "Fen", "Gor", "Hen", "Ish", "Jen", "Kel", "Lor", "Mor", "Nor", "Orr", "Per", "Quor", "Ren", "Sor", "Tor", "Ur", "Ver", "Wor", "Xen", "Yor", "Zor"]
    suffixes = ["ia", "os", "a", "us", "is", "en", "or", "an", "el", "ar"]
    return random.choice(prefixes) + random.choice(suffixes)


def _interpolate_stellar_data(spectral_str, class_v_data):
    """Helper to interpolate mass, temp, etc. between subtypes."""
    s_type = spectral_str[0]
    s_subtype = int(spectral_str[1])

    types = ['O', 'B', 'A', 'F', 'G', 'K', 'M']
    subtypes = [0, 5, 9] if s_type == 'M' else [0, 5]

    # Find bracketing subtypes
    lower_subtype = max([s for s in subtypes if s <= s_subtype])
    upper_subtype_list = [s for s in subtypes if s > s_subtype]
    upper_subtype = min(upper_subtype_list) if upper_subtype_list else -1

    if upper_subtype == -1: # At the end of a type (e.g. G9)
        current_type_index = types.index(s_type)
        if current_type_index + 1 >= len(types): return class_v_data[f"{s_type}{lower_subtype}"]
        next_type = types[current_type_index + 1]
        lower_key = f"{s_type}{lower_subtype}"
        upper_key = f"{next_type}0"
        span = 10 - lower_subtype
        pos = s_subtype - lower_subtype
    else:
        lower_key = f"{s_type}{lower_subtype}"
        upper_key = f"{s_type}{upper_subtype}"
        span = upper_subtype - lower_subtype
        pos = s_subtype - lower_subtype
    
    interp_ratio = pos / span if span > 0 else 0
    lower_val = class_v_data[lower_key]
    upper_val = class_v_data[upper_key]
    
    return lower_val + (upper_val - lower_val) * interp_ratio

def generate_primary_star(special_roll=None) -> Star:
    """Implements the primary star generation sequence."""
    primary = Star(designation="A")
    
    roll = special_roll if special_roll else Utils.D6(2)
    star_type_result = DATA['star_type_determination']['Type'].get(min(roll, 12))

    if star_type_result == 'Hot':
        hot_roll = Utils.D6(2)
        star_type_result = DATA['star_type_determination']['Hot'].get(hot_roll)
        primary.spectral_type = "V"
    elif star_type_result == 'Special':
        star_type_result = 'G' # Default to G-type for simplicity
        primary.spectral_type = "V"
    else:
        primary.spectral_type = "V"

    subtype_roll = Utils.D6(2)
    if star_type_result == 'M':
        subtype = DATA['star_subtype']['M-type'][subtype_roll]
    else:
        subtype = DATA['star_subtype']['Numeric'][subtype_roll]

    spectral_str = f"{star_type_result}{subtype}"
    primary.spectral_type = f"{spectral_str} {primary.spectral_type}"
    
    # Calculate physical properties
    lum_class = primary.spectral_type.split(' ')[1]
    primary.mass = _interpolate_stellar_data(spectral_str, DATA['star_mass'][lum_class])
    primary.temp_k = _interpolate_stellar_data(spectral_str, DATA['star_temp'][lum_class])
    primary.diameter = _interpolate_stellar_data(spectral_str, DATA['star_diameter'][lum_class])

    # Luminosity Formula from page 21
    temp_ratio = primary.temp_k / 5772
    primary.luminosity = (primary.diameter ** 2) * (temp_ratio ** 4)

    # HZCO and MAO
    primary.hzco = Utils.calculate_hzco(primary.luminosity)
    primary.mao = Utils.au_to_orbit(0.01 * primary.diameter) # Simplified Roche Limit
    
    return primary

def _determine_non_primary_star_type(parent_star: Star, orbit_class: str) -> dict:
    """Determines the type of a non-primary star based on its parent."""
    dm = 0
    if parent_star.spectral_type.split(' ')[1] in ['III', 'IV']: dm -=1

    roll = Utils.D6(2) + dm
    category = 'Companion' if orbit_class == 'Companion' else 'Secondary'
    result = DATA['non_primary_star_determination'][min(12, max(2,roll))][category]
    return {'type': result, 'roll': roll}

def generate_stellar_system_stars(system: StellarSystem):
    """Generates all stars for a system, including primary, secondaries, and companions."""
    primary = generate_primary_star()
    system.stars.append(primary)

    # Determine number and type of other stars
    star_presense_dm = 0
    if primary.spectral_type[0] in ['O', 'B', 'A', 'F']: star_presense_dm += 1
    if primary.spectral_type[0] == 'M': star_presense_dm -= 1

    # Close Star
    if Utils.D6(2) + star_presense_dm >= 10:
        close_star = Star(designation="B", parent=primary, orbit_class="Close")
        system.stars.append(close_star)

    # Near Star
    if Utils.D6(2) + star_presense_dm >= 10:
        near_star = Star(designation="C", parent=primary, orbit_class="Near")
        system.stars.append(near_star)

    # Far Star
    if Utils.D6(2) + star_presense_dm >= 10:
        far_star = Star(designation="D", parent=primary, orbit_class="Far")
        system.stars.append(far_star)

    # Companions
    for star in system.stars[:]: # Iterate over a copy
        companion_dm = 0
        if star.spectral_type and star.spectral_type[0] in ['O', 'B', 'A', 'F']: companion_dm += 1
        if star.spectral_type and star.spectral_type[0] == 'M': companion_dm -= 1
        if Utils.D6(2) + companion_dm >= 10:
            companion = Star(designation=f"{star.designation}b", parent=star, orbit_class="Companion")
            star.designation = f"{star.designation}a"
            system.stars.append(companion)

    # Set stellar properties for non-primary stars
    for star in system.stars:
        if star.mass == 0.0 and star.parent: # If not primary
            result = _determine_non_primary_star_type(star.parent, star.orbit_class)
            star_type_info = result['type']

            if star_type_info == 'Random':
                new_star = generate_primary_star(special_roll=result['roll'])
                if new_star.mass > star.parent.mass:
                    star_type_info = 'Lesser' # Treat as lesser if more massive
                else:
                    star.spectral_type = new_star.spectral_type
                    star.mass = new_star.mass
                    star.diameter = new_star.diameter
                    star.luminosity = new_star.luminosity
                    star.temp_k = new_star.temp_k
            
            if star_type_info == 'Lesser':
                parent_type = star.parent.spectral_type[0]
                types = ['O', 'B', 'A', 'F', 'G', 'K', 'M']
                current_index = types.index(parent_type)
                if current_index + 1 < len(types):
                    new_type = types[current_index+1]
                    subtype = Utils.d10()
                    star.spectral_type = f"{new_type}{subtype} V"
                else:
                    star.spectral_type = f"M{Utils.d10()} V"

            elif star_type_info == 'Sibling':
                parent_type = star.parent.spectral_type.split(' ')[0]
                parent_subtype = int(parent_type[1:])
                new_subtype = parent_subtype - Utils.D6()
                new_type = parent_type[0]
                if new_subtype < 0:
                    types = ['O', 'B', 'A', 'F', 'G', 'K', 'M']
                    current_index = types.index(new_type)
                    if current_index + 1 < len(types):
                        new_type = types[current_index + 1]
                        new_subtype += 10
                    else:
                        new_subtype = 0 # Clamp to M0
                star.spectral_type = f"{new_type}{new_subtype} V"

            elif star_type_info == 'Twin':
                star.spectral_type = star.parent.spectral_type
                star.mass = star.parent.mass * (1 - (Utils.D6()-1)/100)
                star.diameter = star.parent.diameter * (1 - (Utils.D6()-1)/100)

            if star.mass == 0.0: # If not set by Twin or Random
                if not star.spectral_type:
                    star.spectral_type = "M0 V" # Default for unhandled cases
                lum_class = star.spectral_type.split(' ')[1]
                spectral_str = star.spectral_type.split(' ')[0]
                star.mass = _interpolate_stellar_data(spectral_str, DATA['star_mass'][lum_class])
                star.temp_k = _interpolate_stellar_data(spectral_str, DATA['star_temp'][lum_class])
                star.diameter = _interpolate_stellar_data(spectral_str, DATA['star_diameter'][lum_class])

            if star.luminosity == 0.0:
                temp_ratio = star.temp_k / 5772
                star.luminosity = (star.diameter ** 2) * (temp_ratio ** 4)

    # Create composite star groups (e.g., Aab)
    for star in system.stars[:]:
        if star.orbit_class == "Companion" and star.parent:
            parent = star.parent
            composite_designation = parent.designation[:-1] + 'ab'
            if not any(s.designation == composite_designation for s in system.stars):
                composite = Star(
                    designation=composite_designation,
                    is_composite=True,
                    components=[parent.designation, star.designation],
                    mass=parent.mass + star.mass,
                    luminosity=parent.luminosity + star.luminosity,
                    spectral_type=parent.spectral_type # Primary's type used for composite
                )
                composite.hzco = Utils.calculate_hzco(composite.luminosity)
                composite.mao = 0.5 + star.eccentricity # Rule 2, pg 38
                system.stars.append(composite)

    # System Age
    lifespan = 10 / (system.primary_star.mass ** 2.5) if system.primary_star.mass > 0 else 10
    if lifespan > 13.8: # Use small star age formula
        system.age_gyr = Utils.D6() * 2 + Utils.D3() - 1
    else:
        system.age_gyr = lifespan * (Utils.d10() / 10.0)
    system.age_gyr = round(max(0.1, min(system.age_gyr, 13.5)), 3)

def determine_world_counts(system: StellarSystem):
    """Determines the number of Gas Giants, Planetoid Belts, and Terrestrial Planets."""
    
    # Helper to determine star characteristics for DMs
    is_class_v_star = system.primary_star.spectral_type.endswith(' V')
    is_brown_dwarf = system.primary_star.spectral_type.startswith('BD')
    is_post_stellar = system.primary_star.spectral_type.startswith('D') # White Dwarf
    is_protostar = system.primary_star.spectral_type.startswith(('T', 'P')) # T Tauri, Protostar (simplified)

    # Gas Giants 
    # Existence roll DMs (page 37) - None unless Special Circumstances (not implemented yet)
    if Utils.D6(2) <= 9: # Gas Giant Exists on 9- (2D roll)
        dm_quantity = 0
        if is_class_v_star and len(system.stars) == 1: dm_quantity += 1 # Single Class V star
        if is_brown_dwarf: dm_quantity -= 2
        if is_post_stellar: dm_quantity -= 2
        # Total number of post-stellar objects DM-1 per object (including primary star) - not fully implemented
        if len(system.stars) >= 4: dm_quantity -= 1 # System consists of four or more stars

        roll = Utils.D6(2) + dm_quantity
        roll = max(DATA['gas_giant_quantity']['min_roll'], min(roll, DATA['gas_giant_quantity']['max_roll']))
        system.gas_giant_count = DATA['gas_giant_quantity']['roll_map'][roll]

    # Planetoid Belts 
    # Existence roll DMs (page 37) - None unless Special Circumstances (not implemented yet)
    if Utils.D6(2) >= 8: # Planetoid Belt Exists on 8+ (2D roll)
        dm_quantity = 0
        if system.gas_giant_count > 0: dm_quantity += 1
        if is_protostar: dm_quantity += 3
        if is_post_stellar: dm_quantity += 1
        # Total number of post-stellar objects DM+1 per object (including primary star) - not fully implemented
        if len(system.stars) >= 2: dm_quantity += 1 # System consists of two or more stars

        roll = Utils.D6(2) + dm_quantity
        roll = max(DATA['planetoid_belt_quantity']['min_roll'], min(roll, DATA['planetoid_belt_quantity']['max_roll']))
        system.planetoid_belt_count = DATA['planetoid_belt_quantity']['roll_map'][roll]

    # Terrestrial Planets 
    dm_quantity = 0
    if is_post_stellar: dm_quantity -= 1 # DM-1 per post-stellar object (including primary star) - simplified for primary only
    
    roll = Utils.D6(2) - 2 + dm_quantity
    if roll < 3:
        system.terrestrial_planet_count = Utils.D3() + 2
    else:
        system.terrestrial_planet_count = roll + Utils.D3() - 1

    system.total_worlds = system.gas_giant_count + system.planetoid_belt_count + system.terrestrial_planet_count

def _calculate_hill_sphere_orbits(system: StellarSystem) -> List[Tuple[float, float]]:
    """Calculates available orbits using Hill Sphere calculations (physics model)."""
    # Step 1: Convert all Orbit# to AU (already done for star.orbit_au)

    # Step 2: Determine the Hill sphere for each star
    hill_spheres = {}
    for star in system.stars:
        if star.parent: # For secondary stars, AU is distance from primary
            au_distance = Utils.orbit_to_au(star.orbit_num)
            m = star.mass
            M = star.parent.mass # Simplified: parent's mass
            hill_radius_au = au_distance * (1 - star.eccentricity) * (m / (3 * M))**(1/3)
            hill_spheres[star.designation] = hill_radius_au
        else: # For primary star, AU is distance to closest secondary
            closest_secondary_au = float('inf')
            for other_star in system.stars:
                if other_star.parent == star:
                    closest_secondary_au = min(closest_secondary_au, Utils.orbit_to_au(other_star.orbit_num))
            if closest_secondary_au != float('inf'):
                m = star.mass
                M = system.stars[0].mass # Simplified: primary star's mass
                hill_radius_au = closest_secondary_au * (1 - star.eccentricity) * (m / (3 * M))**(1/3)
                hill_spheres[star.designation] = hill_radius_au
            else:
                hill_spheres[star.designation] = float('inf') # No secondaries, effectively infinite Hill Sphere

    # Step 3: Divide each Hill sphere result by 3 to get stability sphere
    stability_spheres_au = {s: hs / 3 for s, hs in hill_spheres.items()}

    # Step 4: Convert AU values of stability spheres to Orbit#
    stability_spheres_orbit = {s: Utils.au_to_orbit(ssa) for s, ssa in stability_spheres_au.items()}

    # Step 5: Determine stable orbits around multiple stars (simplified)
    # This is a very complex step in the handbook. For now, a simplified approach:
    # Combine all stability spheres and find the available gaps.
    
    forbidden_zones = []
    for star in system.stars:
        if star.designation in stability_spheres_orbit:
            orbit_val = stability_spheres_orbit[star.designation]
            # For simplicity, assume the stability sphere creates a forbidden zone around the star's orbit
            # The handbook rules are much more complex, involving interactions between multiple stars.
            # This is a placeholder for a more robust implementation.
            forbidden_zones.append((star.orbit_num - orbit_val, star.orbit_num + orbit_val))

    # Sort and merge overlapping forbidden zones
    forbidden_zones.sort()
    merged_zones = []
    if forbidden_zones:
        current_start, current_end = forbidden_zones[0]
        for next_start, next_end in forbidden_zones[1:]:
            if next_start <= current_end: # Overlap
                current_end = max(current_end, next_end)
            else:
                merged_zones.append((current_start, current_end))
                current_start, current_end = next_start, next_end
        merged_zones.append((current_start, current_end))

    available_orbits = []
    current_orbit = system.primary_star.mao # Start from primary's MAO

    for zone_start, zone_end in merged_zones:
        if current_orbit < zone_start:
            available_orbits.append((current_orbit, zone_start))
        current_orbit = max(current_orbit, zone_end)
    
    if current_orbit < 20.0:
        available_orbits.append((current_orbit, 20.0))

    return available_orbits

def calculate_available_orbits(system: StellarSystem, model='simple'):
    """Calculates the valid Orbit# ranges for planetary bodies."""
    primary_group = next((s for s in system.stars if not s.parent), None)
    if not primary_group: return

    if model == 'simple':
        forbidden_zones = []
        secondaries = [s for s in system.stars if s.parent and s.orbit_class != 'Companion']
        
        for star in secondaries:
            # Rule 5: Orbits# +1.00 from secondary star are unavailable
            exclusion_start = star.orbit_num - 1.0
            exclusion_end = star.orbit_num + 1.0

            # Rule 6: If eccentricity > 0.2, add one more Orbit# on either side
            if star.eccentricity > 0.2: 
                exclusion_start -= 1.0
                exclusion_end += 1.0
            
            # Rule 7: If eccentricity > 0.5, add another Orbit# on either side (only for Close/Near)
            if star.eccentricity > 0.5 and star.orbit_class in ['Close', 'Near']:
                exclusion_start -= 1.0
                exclusion_end += 1.0
            
            forbidden_zones.append((exclusion_start, exclusion_end))
        
        # Sort and merge overlapping forbidden zones
        forbidden_zones.sort()
        merged_zones = []
        if forbidden_zones:
            current_start, current_end = forbidden_zones[0]
            for next_start, next_end in forbidden_zones[1:]:
                if next_start <= current_end: # Overlap
                    current_end = max(current_end, next_end)
                else:
                    merged_zones.append((current_start, current_end))
                    current_start, current_end = next_start, next_end
            merged_zones.append((current_start, current_end))

        available = []
        current_orbit = primary_group.mao

        for zone_start, zone_end in merged_zones:
            if current_orbit < zone_start:
                available.append((current_orbit, zone_start))
            current_orbit = max(current_orbit, zone_end)
        
        if current_orbit < 20.0:
            available.append((current_orbit, 20.0))
        
        primary_group.available_orbits = available

    elif model == 'physics':
        primary_group.available_orbits = _calculate_hill_sphere_orbits(system)

def calculate_baseline_and_spread(system: StellarSystem):
    """Determines the system's baseline number, baseline orbit, and orbital spread."""
    primary_group = next((s for s in system.stars if not s.parent), None)
    if not primary_group: return

    # Helper to determine star characteristics for DMs
    has_companion = any(s.orbit_class == 'Companion' for s in system.stars)
    is_class_ia_ib_ii = primary_group.spectral_type.endswith((' Ia', ' Ib', ' II'))
    is_class_iii = primary_group.spectral_type.endswith(' III')
    is_class_iv = primary_group.spectral_type.endswith(' IV')
    is_class_vi = primary_group.spectral_type.endswith(' VI')
    is_post_stellar = primary_group.spectral_type.startswith('D') # White Dwarf

    # Baseline Number 
    dm = 0
    if has_companion: dm -= 2
    if is_class_ia_ib_ii: dm += 3
    elif is_class_iii: dm += 2
    elif is_class_iv: dm += 1
    elif is_class_vi: dm -= 1
    if is_post_stellar: dm -= 2

    if system.total_worlds < 6: dm -= 4
    elif system.total_worlds <= 9: dm -= 3
    elif system.total_worlds <= 12: dm -= 2
    elif system.total_worlds <= 15: dm -= 1
    elif system.total_worlds >= 18 and system.total_worlds <= 20: dm += 1
    elif system.total_worlds > 20: dm += 2

    for star in system.stars:
        if star != primary_group and not star.is_composite: # For each secondary star
            dm -= 1

    system.baseline_number = Utils.D6(2) + dm

    # Baseline Orbit 
    if 1 <= system.baseline_number <= system.total_worlds: # Temperate system 
        variance = (Utils.D6(2) - 7) / 10.0
        system.baseline_orbit = primary_group.hzco + variance
    elif system.baseline_number < 1: # Cold system 
        variance = (Utils.D6(2) - 2) / 10.0
        system.baseline_orbit = primary_group.hzco - system.baseline_number + variance
    else: # Hot system 
        variance = (Utils.D6(2) - 7) / 5.0
        system.baseline_orbit = primary_group.hzco - (system.baseline_number - system.total_worlds) + variance

    # Ensure baseline orbit is in an available zone (page 46)
    is_available = any(start <= system.baseline_orbit <= end for start, end in primary_group.available_orbits)
    if not is_available:
        # Place the baseline orbit at the nearest available Orbit# with 2D-7 / 10 Orbit# variance
        closest_dist = float('inf')
        new_orbit = system.baseline_orbit
        variance_roll = (Utils.D6(2) - 7) / 10.0

        for start, end in primary_group.available_orbits:
            if system.baseline_orbit < start: # If baseline is before an available zone
                dist_to_start = start - system.baseline_orbit
                if dist_to_start < closest_dist:
                    closest_dist = dist_to_start
                    new_orbit = start + variance_roll # Move into the zone
            elif system.baseline_orbit > end: # If baseline is after an available zone
                dist_to_end = system.baseline_orbit - end
                if dist_to_end < closest_dist:
                    closest_dist = dist_to_end
                    new_orbit = end + variance_roll # Move into the zone
            else: # If baseline is within an available zone, no adjustment needed
                new_orbit = system.baseline_orbit
                break
        system.baseline_orbit = new_orbit

    # System Spread 
    baseline_num_for_calc = max(1, system.baseline_number)
    numerator = system.baseline_orbit - primary_group.mao
    if numerator <= 0 or baseline_num_for_calc == 0:
        system.spread = 0.5 # Default fallback
    else:
        system.spread = numerator / baseline_num_for_calc

def handle_anomalies_and_empties(system: StellarSystem):
    """Determines number of empty and anomalous orbits."""
    # Empty Orbits (page 48)
    empty_roll = Utils.D6(2)
    if empty_roll == 10: system.empty_orbit_count = 1
    elif empty_roll == 11: system.empty_orbit_count = 2
    elif empty_roll == 12: system.empty_orbit_count = 3
    else: system.empty_orbit_count = 0

    # Anomalous Orbits (page 50)
    anomalous_roll = Utils.D6(2)
    num_anomalous = 0
    if anomalous_roll == 10: num_anomalous = 1
    elif anomalous_roll == 11: num_anomalous = 2
    elif anomalous_roll == 12: num_anomalous = 3

    for _ in range(num_anomalous):
        anomaly_type_roll = Utils.D6(2)
        anomaly_type = 'random' # Default
        if anomaly_type_roll <= 7: anomaly_type = 'random'
        elif anomaly_type_roll == 8: anomaly_type = 'eccentric'
        elif anomaly_type_roll == 9: anomaly_type = 'inclined'
        elif anomaly_type_roll >= 10 and anomaly_type_roll <= 11: anomaly_type = 'retrograde'
        elif anomaly_type_roll == 12: anomaly_type = 'trojan'
        
        system.anomalous_planets.append({'type': anomaly_type})
        system.terrestrial_planet_count += 1
        system.total_worlds += 1

def generate_orbital_slots(system: StellarSystem) -> List[dict]:
    """Generates the final list of all orbital slots for the system."""
    primary_group = next((s for s in system.stars if not s.parent), None)
    if not primary_group: return []
    
    total_slots_needed = system.total_worlds + system.empty_orbit_count
    
    slots = []
    current_orbit = primary_group.mao

    # Generate regular slots
    for i in range(total_slots_needed - len(system.anomalous_planets)):
        if i + 1 == system.baseline_number:
            current_orbit = system.baseline_orbit
        else:
            current_orbit += system.spread
        
        # Check if in forbidden zone
        for start, end in primary_group.available_orbits:
            if current_orbit > end and start > (current_orbit - system.spread):
                 current_orbit = start + (current_orbit - end) # Jump over gap
                 break

        slots.append({'orbit_num': round(current_orbit, 2), 'type': 'regular'})
        
    # Add anomalous slots
    for anomaly in system.anomalous_planets:
        # Place randomly within an available orbit range
        if primary_group.available_orbits:
            zone = random.choice(primary_group.available_orbits)
            ano_orbit = random.uniform(zone[0], zone[1])
            slots.append({'orbit_num': round(ano_orbit, 2), 'type': 'anomalous', 'anomaly': anomaly})
    
    return sorted(slots, key=lambda x: x['orbit_num'])

def place_worlds(system: StellarSystem, orbital_slots: List[dict]):
    """Places worlds into the generated orbital slots."""
    slots_map = {i: {'slot': s, 'body': None} for i, s in enumerate(orbital_slots)}
    
    placements = []
    # Mainworld placement is handled later in Expanded Method, so skip for now.
    placements.extend([{'type': 'Empty', 'count': system.empty_orbit_count}])
    placements.extend([{'type': 'Gas Giant', 'count': system.gas_giant_count}])
    placements.extend([{'type': 'Planetoid Belt', 'count': system.planetoid_belt_count}])
    
    num_slots = len(slots_map)
    available_slots_indices = list(range(num_slots))
    random.shuffle(available_slots_indices) # Randomize initial selection
    
    # Keep track of mainworld for the Gas Giant/Mainworld rule
    mainworld_slot_idx = -1
    # For now, assuming mainworld is a terrestrial planet and will be placed last.
    # A more robust implementation would place it first if using Continuation Method.

    for item in placements:
        count_to_place = item['count']
        placed_count = 0
        while placed_count < count_to_place and available_slots_indices:
            slot_idx = available_slots_indices.pop(0) # Take the first available slot
            
            # Collision handling: if slot is already occupied, move to next. (Simplified: just pick another)
            # The handbook implies moving to the *next* sequential slot, but for random placement, re-picking is simpler.
            if slots_map[slot_idx]['body'] is not None:
                available_slots_indices.append(slot_idx) # Put it back and try another
                continue

            if slots_map[slot_idx]['slot']['type'] == 'anomalous' and item['type'] == 'Empty':
                 # Re-roll if trying to place Empty in anomalous slot (simplified: skip and try next)
                 available_slots_indices.append(slot_idx) # Put it back and try another
                 continue 
            
            slots_map[slot_idx]['body'] = item['type']
            placed_count += 1

            # Gas Giant/Mainworld Rule (page 51) - Simplified: if a Gas Giant is placed, and there's a mainworld, 
            # the mainworld becomes a moon and a terrestrial planet is added. 
            # This rule is complex as it implies a pre-existing mainworld. For Expanded Method, mainworld is not yet determined.
            # For now, we'll add a note if a Gas Giant is placed in a potential mainworld orbit.
            if item['type'] == 'Gas Giant' and mainworld_slot_idx != -1 and slot_idx == mainworld_slot_idx:
                # This logic needs to be refined when mainworld placement is fully implemented.
                pass

    # Fill remaining with terrestrial planets 
    for slot_idx in available_slots_indices:
        slots_map[slot_idx]['body'] = 'Terrestrial'
        
    # Create PlanetaryBody objects
    primary_group = next((s for s in system.stars if not s.parent), None)
    for i in range(num_slots):
        slot_info = slots_map[i]
        if slot_info['body'] == 'Empty': continue
        
        body = PlanetaryBody(
            name=generate_world_name(),
            parent_star_group=primary_group.designation,
            body_type=slot_info['body'],
            orbit_num=slot_info['slot']['orbit_num']
        )
        if slot_info['slot'].get('anomaly'):
            body.notes.append(f"Anomalous Orbit: {slot_info['slot']['anomaly']['type']}")
        
        # Finalize orbital params
        body.orbit_au = Utils.orbit_to_au(body.orbit_num)
        
        # Eccentricity (page 52)
        # For each placed world (excluding planetoid belts), a roll is made on the 'Eccentricity Values' table
        if body.body_type != 'Planetoid Belt':
            ecc_roll = Utils.D6(2)
            if slot_info['slot'].get('anomaly'):
                anomaly_type = slot_info['slot']['anomaly']['type']
                if anomaly_type == 'eccentric':
                    ecc_roll += 4 # Large DM
                elif anomaly_type == 'retrograde':
                    body.notes.append("Retrograde Orbit")
                elif anomaly_type == 'inclined':
                    body.inclination = (Utils.D6(2) * 5) + Utils.D6() # Random inclination
                    body.notes.append(f"Inclined Orbit: {body.inclination} degrees")
                elif anomaly_type == 'trojan':
                    body.notes.append("Trojan Orbit")

            ecc_data = DATA['eccentricity_values'].get(min(12, max(5, ecc_roll)))
            if ecc_data:
                base_ecc = ecc_data['base']
                roll_ecc = ecc_data['roll']()
                body.eccentricity = round(max(0.0, min(0.999, base_ecc + roll_ecc)), 3)

        # Orbital Period (page 53)
        # Scenario 1: A planet orbiting a single star (current implementation)
        # Scenario 2: A planet orbiting a group of stars (sum of interior masses)
        # Scenario 3: A massive planet orbiting a star (planet's own mass included)
        
        total_mass_for_period = primary_group.mass

        # Scenario 2: Planet orbiting a group of stars
        # If the body orbits a composite star group, sum the masses of its components
        if primary_group.is_composite:
            total_mass_for_period = sum(s.mass for s in system.stars if s.designation in primary_group.components)
        
        # Scenario 3: Massive planet orbiting a star (simplified: if it's a Gas Giant)
        if body.body_type == 'Gas Giant':
            # For now, we use a simplified mass for gas giants. A full implementation would have a more accurate mass.
            # Assuming 1 Solar Mass = 1047.56 Jupiter Masses, and a typical Gas Giant is 1-10 Jupiter Masses.
            # So, a Gas Giant mass is roughly 0.001 to 0.01 Solar Masses. We'll use a placeholder.
            gas_giant_solar_mass = 0.005 # Placeholder for average gas giant mass in Solar Masses
            total_mass_for_period += gas_giant_solar_mass

        body.period_years = math.sqrt(body.orbit_au**3 / total_mass_for_period)
        
        primary_group.orbiting_bodies.append(body)

def detail_placed_worlds(system: StellarSystem):
    """Generates size and satellite details for all placed worlds."""
    for world in system.all_worlds:
        if world.body_type == 'Terrestrial':
            # Terrestrial World Sizing (page 54)
            roll_1d = Utils.D6()
            roll_type = DATA['terrestrial_world_sizing']['1D_roll'][roll_1d]
            
            if roll_type == '1D':
                size_roll = DATA['terrestrial_world_sizing']['size_ranges']['1D'][Utils.D6()]
            elif roll_type == '2D':
                size_roll = DATA['terrestrial_world_sizing']['size_ranges']['2D'][Utils.D6(2)]
            else: # 2D+3
                size_roll = DATA['terrestrial_world_sizing']['size_ranges']['2D+3'][Utils.D6(2) + 3]
            world.size_code = Utils.eHex(size_roll)
        
        elif world.body_type == 'Gas Giant':
            category_roll = Utils.D6()
            if category_roll <= 2: category = 'GS'
            elif category_roll <= 4: category = 'GM'
            else: category = 'GL'
            
            d_roll = DATA['gas_giant_sizing'][category]['d_roll']()
            world.diameter_km = d_roll * 12800 # Using Size 8 as base (placeholder)
            world.mass_terran = DATA['gas_giant_sizing'][category]['m_roll']()
            world.size_code = f"{category}{Utils.eHex(d_roll)}"
        
        elif world.body_type == 'Planetoid Belt':
            world.size_code = '0'
            
        # Generate Satellites (page 55)
        num_moons = 0
        dm_moons = 0

        # Apply DMs for moon quantity (page 55)
        if world.orbit_num < 1.0: dm_moons += DATA['significant_moon_quantity']['dms']['orbit_less_than_1']
        # Simplified: More DMs would be applied based on adjacency to companion, unavailability zones, etc.

        if world.body_type == 'Terrestrial':
            size_val = int(world.size_code, 16) if world.size_code in 'ABCDEF' else int(world.size_code)
            if size_val <= 2: # Planet Size 1-2
                num_moons = max(0, DATA['significant_moon_quantity']['planet_size_1_2']() + dm_moons)
            elif size_val <= 9: # Planet Size 3-9
                num_moons = max(0, DATA['significant_moon_quantity']['planet_size_3_9']() + dm_moons)
            else: # Planet Size A-F
                num_moons = max(0, DATA['significant_moon_quantity']['planet_size_a_f']() + dm_moons)
        elif 'G' in world.size_code:
            if 'GS' in world.size_code: # Small Gas Giant
                num_moons = max(0, DATA['significant_moon_quantity']['small_gas_giant']() + dm_moons)
            else: # Medium or Large Gas Giant
                num_moons = max(0, DATA['significant_moon_quantity']['medium_large_gas_giant']() + dm_moons)
        
        for i in range(num_moons):
            sat = Satellite(parent_body=world)
            # Satellite Size/Type (page 56)
            size_roll = Utils.D6()
            if size_roll <= 3: sat.size_code = 'S'
            elif size_roll <= 5:
                r_roll = Utils.D3() - 1
                sat.size_code = 'R' if r_roll == 0 else str(r_roll)
                sat.is_ring = (r_roll == 0)
            else: # 1D roll of 6
                if world.body_type == 'Terrestrial':
                    # Terrestrial: Size-1 -1D (simplified)
                    size_val = int(world.size_code, 16) if world.size_code in 'ABCDEF' else int(world.size_code)
                    sat_size = max(0, size_val - 1 - Utils.D6())
                    sat.size_code = Utils.eHex(sat_size)
                elif 'G' in world.size_code:
                    # Gas Giant: Special (simplified)
                    sat_size = Utils.D6() # Placeholder for special gas giant moon sizing
                    sat.size_code = Utils.eHex(sat_size)
            world.satellites.append(sat)

def flag_points_of_interest(system: StellarSystem):
    """Analyzes the generated system to flag narratively interesting features."""
    primary_group = next((s for s in system.stars if not s.parent), None)
    if not primary_group: return

    hz_min = primary_group.hzco - 1.0
    hz_max = primary_group.hzco + 1.0

    for world in system.all_worlds:
        if world.notes and 'Anomalous' in world.notes[0]:
            world.notes.append("Point of Interest: Anomalous orbit.")
            
        for satellite in world.satellites:
            is_large_moon = False
            try:
                if satellite.size_code.isdigit() and int(satellite.size_code) >= 4:
                    is_large_moon = True
            except ValueError:
                pass # Not a digit size code
            
            if is_large_moon and hz_min <= world.orbit_num <= hz_max:
                satellite.notes.append("Point of Interest: Large moon in Habitable Zone. Mainworld Candidate.")
                world.notes.append(f"Candidate moon {satellite.designation}")

def _to_roman_numeral(num: int) -> str:
    """Converts an integer to a Roman numeral string."""
    if num <= 0: return str(num)

    roman_map = {
        1000: 'M', 900: 'CM', 500: 'D', 400: 'CD', 100: 'C', 90: 'XC',
        50: 'L', 40: 'XL', 10: 'X', 9: 'IX', 5: 'V', 4: 'IV', 1: 'I'
    }
    roman_numeral = ""
    for value, numeral in roman_map.items():
        while num >= value:
            roman_numeral += numeral
            num -= value
    return roman_numeral

def assign_final_designations(system: StellarSystem):
    """Assigns standard Traveller designations to all bodies."""
    for star_group in system.stars:
        if star_group.is_composite: continue
        
        planet_counter = 1
        belt_counter = 1
        star_group.orbiting_bodies.sort(key=lambda x: x.orbit_num)
        
        for world in star_group.orbiting_bodies:
            if world.body_type == 'Planetoid Belt':
                world.designation = f"{star_group.designation} P{_to_roman_numeral(belt_counter)}"
                belt_counter += 1
            elif world.body_type in ['Terrestrial', 'Gas Giant']:
                world.designation = f"{star_group.designation} {_to_roman_numeral(planet_counter)}"
                planet_counter += 1
                
            # Designate moons
            moon_char_code = ord('a')
            for satellite in world.satellites:
                satellite.designation = f"{world.designation} {chr(moon_char_code)}"
                moon_char_code += 1

def generate_short_profile(system: StellarSystem) -> str:
    """Generates a concise system summary in G-P-T-N-S format (page 58)."""
    g = system.gas_giant_count
    p = system.planetoid_belt_count
    t = system.terrestrial_planet_count
    n = system.baseline_number
    s = round(system.spread, 1)
    return f"{g}-{p}-{t}-{n}-{s}"

def generate_long_profile(system: StellarSystem) -> str:
    """Generates a detailed system summary showing world types in orbital sequence (page 58)."""
    profile_parts = []
    for star_group in system.stars:
        if star_group.is_composite: continue
        
        star_profile = f"{star_group.designation}-"
        world_types = []
        for world in star_group.orbiting_bodies:
            if world.body_type == 'Terrestrial':
                world_types.append('T')
            elif world.body_type == 'Gas Giant':
                world_types.append('G')
            elif world.body_type == 'Planetoid Belt':
                world_types.append('P')
            elif world.body_type == 'Empty':
                world_types.append('E') # Represent empty orbits
        star_profile += '-'.join(world_types)
        profile_parts.append(star_profile)
    return ':'.join(profile_parts)

def generate_full_system(name="Random System") -> StellarSystem:
    """Main function to orchestrate the entire generation process."""
    # Init
    system = StellarSystem(name=name)
    
    # Phase 1: Stellar Generation
    generate_stellar_system_stars(system)
    
    # Phase 2: System Architecture & Population
    determine_world_counts(system)
    calculate_available_orbits(system, model='physics')
    calculate_baseline_and_spread(system)
    handle_anomalies_and_empties(system)
    
    # Generate slot architecture
    orbital_slots = generate_orbital_slots(system)
    
    # Phase 3: World Placement
    place_worlds(system, orbital_slots)
    
    # Phase 4: Detailing
    detail_placed_worlds(system)
    for world in system.all_worlds:
        if world.body_type == 'Terrestrial':
            # Simplified atmosphere and hydrographics for now
            size_val = Utils.from_eHex(world.size_code)
            if not world.atmosphere_code:
                atm_val = generate_atmosphere(size_val)
                world.atmosphere_code = Utils.eHex(atm_val)
            else:
                atm_val = Utils.from_eHex(world.atmosphere_code)

            if not world.hydrographics_code:
                hydro_val = generate_hydrographics(size_val, atm_val)
                world.hydrographics_code = Utils.eHex(hydro_val)

            world.mean_temperature = calculate_mean_temperature(world, system)
            world.surface_features = generate_surface_features(world)
            world.life_details = generate_life(world)
    assign_final_designations(system) # Moved here as it needs sizes for moon counts
    
    # Analysis
    flag_points_of_interest(system)

    return system

def generate_atmosphere(size: int) -> int:
    """Generates atmosphere code."""
    if size == 0:
        return 0
    return max(0, Utils.D6(2) - 7 + size)

def generate_hydrographics(size: int, atmosphere: int) -> int:
    """Generates hydrographics code."""
    if size <= 1:
        return 0
    hydro = Utils.D6(2) - 7 + atmosphere
    if atmosphere <= 1 or atmosphere >= 10:
        hydro -= 4
    return max(0, min(10, hydro))

def generate_population(dm: int = 0) -> int:
    """Generates population code with an optional DM."""
    return max(0, Utils.D6(2) - 2 + dm)

def generate_government(population: int) -> int:
    """Generates government code."""
    if population == 0:
        return 0
    return max(0, Utils.D6(2) - 7 + population)

def generate_law_level(government: int) -> int:
    """Generates law level code."""
    if government == 0:
        return 0
    return max(0, Utils.D6(2) - 7 + government)

def generate_starport(population: int) -> str:
    """Generates starport code."""
    roll = Utils.D6(2)
    if population >= 10:
        roll += 2
    elif population >= 8:
        roll += 1
    elif population <= 4:
        roll -= 1
    elif population <= 2:
        roll -= 2
    
    if roll <= 2:
        return 'X'
    elif roll <= 4:
        return 'E'
    elif roll <= 6:
        return 'D'
    elif roll <= 8:
        return 'C'
    elif roll <= 10:
        return 'B'
    else:
        return 'A'

def generate_tech_level(starport: str, size: int, atmosphere: int, hydrographics: int, population: int) -> int:
    """Generates tech level code."""
    roll = Utils.D6(1)
    dm = 0
    if starport == 'A':
        dm += 6
    elif starport == 'B':
        dm += 4
    elif starport == 'C':
        dm += 2
    elif starport == 'X':
        dm -= 4
    
    if size <= 1:
        dm += 2
    elif size <= 4:
        dm += 1
        
    if atmosphere <= 3 or atmosphere >= 10:
        dm += 1
        
    if hydrographics == 0 or hydrographics == 9:
        dm += 1
    elif hydrographics == 10:
        dm += 2
        
    if 1 <= population <= 5 or population == 8:
        dm += 1
    elif population == 9:
        dm += 2
    elif population == 10:
        dm += 4
        
    return max(0, roll + dm)

def generate_mainworld_uwp(population_dm: int = 0) -> UWP:
    """Generates a full UWP for a mainworld."""
    uwp = UWP()
    
    size_roll = Utils.D6(2) - 2
    uwp.size = Utils.eHex(size_roll)
    
    atmosphere_val = generate_atmosphere(size_roll)
    uwp.atmosphere = Utils.eHex(atmosphere_val)
    
    hydrographics_val = generate_hydrographics(size_roll, atmosphere_val)
    uwp.hydrographics = Utils.eHex(hydrographics_val)
    
    population_val = generate_population(population_dm)
    uwp.population = Utils.eHex(population_val)
    
    government_val = generate_government(population_val)
    uwp.government = Utils.eHex(government_val)
    
    law_level_val = generate_law_level(government_val)
    uwp.law_level = Utils.eHex(law_level_val)
    
    starport_val = generate_starport(population_val)
    uwp.starport = starport_val
    
    tech_level_val = generate_tech_level(starport_val, size_roll, atmosphere_val, hydrographics_val, population_val)
    uwp.tech_level = Utils.eHex(tech_level_val)
    
    return uwp

def calculate_mean_temperature(world: PlanetaryBody, system: StellarSystem) -> float:
    """Calculates the mean temperature of a world."""
    # Albedo calculation (simplified from handbook)
    albedo = 0.3
    if world.hydrographics_code.isdigit():
        hydro_val = int(world.hydrographics_code, 16)
        if hydro_val > 5:
            albedo = 0.2
        if hydro_val < 2:
            albedo = 0.4

    # Greenhouse factor calculation (simplified from handbook)
    greenhouse_factor = 0.0
    if world.atmosphere_code.isdigit():
        atm_val = int(world.atmosphere_code, 16)
        if atm_val in [4, 5, 6, 7, 8, 9]:
            greenhouse_factor = 0.1 * atm_val
    
    # Get luminosity of parent star(s)
    parent_star_group = next((s for s in system.stars if s.designation == world.parent_star_group), None)
    if not parent_star_group:
        return 0.0
    
    luminosity = parent_star_group.luminosity
    distance = world.orbit_au

    if distance == 0:
        return 0.0

    temperature = 279 * (luminosity * (1 - albedo) * (1 + greenhouse_factor) / distance**2)**0.25
    return temperature

def generate_surface_features(world: PlanetaryBody) -> str:
    """Generates a description of the world's surface features."""
    if not world.hydrographics_code.isalnum():
        return "No hydrographics data."

    hydro_val = Utils.from_eHex(world.hydrographics_code)
    
    if hydro_val == 0:
        return "No surface water, desert world."
    elif hydro_val == 10:
        return "Water world, almost entirely covered in water."

    # Simplified logic from the handbook
    surface_dist_roll = Utils.D6(2) - 2
    
    if hydro_val > 5: # Ocean world
        if surface_dist_roll < 3:
            return f"{hydro_val*10}% water coverage. Many small continents and islands."
        elif surface_dist_roll < 7:
            return f"{hydro_val*10}% water coverage. Several large continents."
        else:
            return f"{hydro_val*10}% water coverage. One super-continent."
    else: # Land world
        if surface_dist_roll < 3:
            return f"{hydro_val*10}% water coverage. Many small seas and large lakes."
        elif surface_dist_roll < 7:
            return f"{hydro_val*10}% water coverage. Several large oceans."
        else:
            return f"{hydro_val*10}% water coverage. One super-ocean."

def generate_life(world: PlanetaryBody) -> str:
    """Generates a description of the world's life."""
    if not world.atmosphere_code.isalnum() or not world.hydrographics_code.isalnum():
        return "No life data."

    atm_val = Utils.from_eHex(world.atmosphere_code)
    hydro_val = Utils.from_eHex(world.hydrographics_code)

    if atm_val < 4 or atm_val > 9:
        return "No significant native life."

    biomass_rating = Utils.D6(2)
    biocomplexity_rating = Utils.D6(2) - 7 + biomass_rating

    return f"Biomass Rating: {biomass_rating}, Biocomplexity Rating: {biocomplexity_rating}"



def hex_to_coords(hex_coord: str) -> Tuple[int, int]:
    """Converts a hex coordinate string (e.g., '0101') to (col, row) integers."""
    col = int(hex_coord[:2])
    row = int(hex_coord[2:])
    return col, row

def hex_distance(hex1: str, hex2: str) -> float:
    """Calculates the Euclidean distance between two hex coordinates."""
    col1, row1 = hex_to_coords(hex1)
    col2, row2 = hex_to_coords(hex2)
    # Simple Euclidean distance for now, could be refined for hex grids
    return math.sqrt((col1 - col2)**2 + (row1 - row2)**2)

def calculate_population_dm(hex_coord: str, sector: Sector) -> int:
    """Calculates the population DM for a given hex based on native sophonts and settlement waves."""
    population_dm = 0

    # Apply DM for native sophonts (+6 for homeworlds)
    if hex_coord in sector.native_sophonts:
        population_dm += 6

    # Apply DM for settlement waves
    for wave in sector.settlement_waves:
        distance = hex_distance(hex_coord, wave.origin_hex)
        if distance <= (wave.propagation_rate * wave.age_centuries):
            if wave.wave_type == "thin":
                population_dm += (-5 + wave.age_centuries) # DM-5 + 1 per century
            elif wave.wave_type == "thick":
                population_dm += (-3 + wave.age_centuries) # DM-3 + 1 per century

    return population_dm

def define_settlement_waves(sector: Sector):
    """Defines settlement waves for the sector."""
    # Simplified for now, could be expanded with more complex logic
    wave1 = Wave(
        name="First Wave",
        origin_hex="0101",
        age_centuries=10,
        wave_type="thick",
        propagation_rate=1.0
    )
    sector.settlement_waves.append(wave1)

def place_native_sophonts(sector: Sector):
    """Places native sophonts in the sector."""
    # Simplified for now, could be expanded with more complex logic
    sophont1 = Sophont(
        name="Aslan",
        homeworld_hex="0805",
    )
    sector.native_sophonts[sophont1.homeworld_hex] = sophont1

def generate_sector(width=8, height=10):
    """Generates a sector of mainworlds."""
    sector = Sector(width=width, height=height)
    #print(f"Generating {sector.name} ({width}x{height})")
    
    # Phase 2.1: Population Patterns - Place native sophonts and define settlement waves
    define_settlement_waves(sector)
    place_native_sophonts(sector)

    for col in range(1, width + 1):
        for row in range(1, height + 1):
            hex_coord = f"{col:02d}{row:02d}"
            
            population_dm = calculate_population_dm(hex_coord, sector)

            if Utils.D6() >= 4:
                system = generate_full_system(name=f"System {hex_coord}")
                # Simplified mainworld selection
                habitable_candidates = []
                for world in system.all_worlds:
                    if world.body_type == 'Terrestrial':
                        if system.primary_star and system.primary_star.hzco -1.5 < world.orbit_num < system.primary_star.hzco + 1.5:
                                habitable_candidates.append(world)
                if habitable_candidates:
                    mainworld = random.choice(habitable_candidates)
                    mainworld.is_mainworld = True
                    mainworld.uwp = generate_mainworld_uwp(population_dm=population_dm)
                    #print(f"  {hex_coord}: System Present - Mainworld UWP: {mainworld.uwp}")
                sector.systems[hex_coord] = system
    return sector

def generate_sector_svg(subsectors):
    """Generates an SVG image of the full sector map."""
    hex_radius = 20
    hex_width = hex_radius * 2
    hex_height = math.sqrt(3) * hex_radius
    
    sector_cols = 32
    sector_rows = 40

    img_width = int(sector_cols * hex_width * 0.75 + hex_width * 0.25)
    img_height = int(sector_rows * hex_height + hex_height / 2)

    svg = f'''<svg width="{img_width}" height="{img_height}" xmlns="http://www.w3.org/2000/svg">
<style>
    .hex {{
        stroke: #888;
        stroke-width: 0.5;
        fill: #fff;
    }}
    .hex_text {{
        font-family: "Courier New", Courier, monospace;
        font-size: 7px;
        text-anchor: middle;
        dominant-baseline: middle;
    }}
</style>
'''

    for subsector_row in range(4):
        for subsector_col in range(4):
            subsector_index = subsector_row * 4 + subsector_col
            if subsector_index >= len(subsectors):
                continue
            subsector = subsectors[subsector_index]
            for row in range(subsector.height):
                for col in range(subsector.width):
                    hex_col = subsector_col * 8 + col
                    hex_row = subsector_row * 10 + row
                    hex_coord = f"{hex_col + 1:02d}{hex_row + 1:02d}"
                    
                    x = hex_col * hex_width * 0.75 + hex_radius
                    y = hex_row * hex_height + hex_height / 2
                    if hex_col % 2 == 1:
                        y += hex_height / 2

                    points = []
                    for i in range(6):
                        angle = math.pi / 3 * i + math.pi / 6
                        px = x + hex_radius * math.cos(angle)
                        py = y + hex_radius * math.sin(angle)
                        points.append(f"{px},{py}")
                    
                    svg += f'<polygon class="hex" points="{" ".join(points)}"/>\n'

                    system_hex_coord = f"{col+1:02d}{row+1:02d}"
                    system = subsector.systems.get(system_hex_coord)
                    if system:
                        mainworld = next((w for w in system.all_worlds if w.is_mainworld), None)
                        if mainworld:
                            svg += f'<text x="{x}" y="{y-5}" class="hex_text">{hex_coord}</text>\n'
                            svg += f'<text x="{x}" y="{y+5}" class="hex_text">{mainworld.uwp}</text>\n'

    svg += '</svg>'
    return svg



# ## VI. Main Execution Block

# In[6]:


from IPython.display import SVG, display
subsectors = []
for i in range(16):
    subsectors.append(generate_sector())
    
svg_data = generate_sector_svg(subsectors)
with open("sector_map.svg", "w") as f:
    f.write(svg_data)
print("Full sector map generated as sector_map.svg")

display(SVG(svg_data))

for i, subsector in enumerate(subsectors):
    print(f'--- Subsector {i+1} ---')
    for hex_coord, system in subsector.systems.items():
        print(f'-- System: {hex_coord} --')
        for world in system.all_worlds:
            print(f'Name: {world.name}, Designation: {world.designation}, Type: {world.body_type}, UWP: {world.uwp}')

