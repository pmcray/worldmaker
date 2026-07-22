import random

# Central reference tables and rules from the World Builder's Handbook and Sector Construction Guide

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
        5: {'base': -0.001, 'roll': lambda: random.randint(1, 6) / 1000},
        6: {'base': -0.001, 'roll': lambda: random.randint(1, 6) / 1000},
        7: {'base': 0.00, 'roll': lambda: random.randint(1, 6) / 200},
        8: {'base': 0.00, 'roll': lambda: random.randint(1, 6) / 200},
        9: {'base': 0.03, 'roll': lambda: random.randint(1, 6) / 100},
        10: {'base': 0.05, 'roll': lambda: sum(random.randint(1, 6) for _ in range(2)) / 20},
        11: {'base': 0.05, 'roll': lambda: sum(random.randint(1, 6) for _ in range(2)) / 20},
        12: {'base': 0.30, 'roll': lambda: sum(random.randint(1, 6) for _ in range(2)) / 20},
    },
    'terrestrial_sizing': { # Page 54 
        1: lambda: random.randint(1, 6),
        2: lambda: random.randint(1, 6),
        3: lambda: sum(random.randint(1, 6) for _ in range(2)),
        4: lambda: sum(random.randint(1, 6) for _ in range(2)),
        5: lambda: sum(random.randint(1, 6) for _ in range(2)) + 3,
        6: lambda: sum(random.randint(1, 6) for _ in range(2)) + 3
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
        'GS': {'d_roll': lambda: random.randint(1, 3) + random.randint(1, 3), 'm_roll': lambda: 5 * (random.randint(1, 6) + 1)},
        'GM': {'d_roll': lambda: random.randint(1, 6) + 6, 'm_roll': lambda: 20 * (sum(random.randint(1, 6) for _ in range(3)) - 1)},
        'GL': {'d_roll': lambda: sum(random.randint(1, 6) for _ in range(2)) + 6, 'm_roll': lambda: random.randint(1, 3) * 50 * (sum(random.randint(1, 6) for _ in range(3)) + 4)}
    },
    'significant_moon_quantity': { # Page 55
        'planet_size_1_2': lambda: random.randint(1, 6) - 5,
        'planet_size_3_9': lambda: sum(random.randint(1, 6) for _ in range(2)) - 8,
        'planet_size_a_f': lambda: sum(random.randint(1, 6) for _ in range(2)) - 6,
        'small_gas_giant': lambda: sum(random.randint(1, 6) for _ in range(3)) - 7,
        'medium_large_gas_giant': lambda: sum(random.randint(1, 6) for _ in range(4)) - 6,
    },
    'trade_codes': [ # Page 186
        {'name': 'Agricultural', 'code': 'Ag', 'size': None, 'atm': range(4, 10), 'hyd': range(4, 9), 'pop': range(5, 8), 'gov': None, 'law': None, 'tl': None},
        {'name': 'Asteroid', 'code': 'As', 'size': [0], 'atm': [0], 'hyd': [0], 'pop': None, 'gov': None, 'law': None, 'tl': None},
        {'name': 'Barren', 'code': 'Ba', 'size': None, 'atm': None, 'hyd': None, 'pop': [0], 'gov': [0], 'law': [0], 'tl': None},
        {'name': 'Desert', 'code': 'De', 'size': None, 'atm': range(2, 10), 'hyd': [0], 'pop': None, 'gov': None, 'law': None, 'tl': None},
        {'name': 'Fluid Oceans', 'code': 'Fl', 'size': None, 'atm': [10, 11, 12, 13, 14, 15], 'hyd': range(1, 11), 'pop': None, 'gov': None, 'law': None, 'tl': None},
        {'name': 'Garden', 'code': 'Ga', 'size': range(6, 9), 'atm': [5, 6, 8], 'hyd': range(5, 8), 'pop': None, 'gov': None, 'law': None, 'tl': None},
        {'name': 'High Population', 'code': 'Hi', 'size': None, 'atm': None, 'hyd': None, 'pop': range(9, 16), 'gov': None, 'law': None, 'tl': None},
        {'name': 'High Tech', 'code': 'Ht', 'size': None, 'atm': None, 'hyd': None, 'pop': None, 'gov': None, 'law': None, 'tl': range(12, 34)},
        {'name': 'Ice-Capped', 'code': 'Ic', 'size': None, 'atm': [0, 1], 'hyd': range(1, 11), 'pop': None, 'gov': None, 'law': None, 'tl': None},
        {'name': 'Industrial', 'code': 'In', 'size': None, 'atm': [0, 1, 2, 4, 7, 9, 10, 11, 12], 'hyd': None, 'pop': range(9, 16), 'gov': None, 'law': None, 'tl': None},
        {'name': 'Low Population', 'code': 'Lo', 'size': None, 'atm': None, 'hyd': None, 'pop': range(1, 4), 'gov': None, 'law': None, 'tl': None},
        {'name': 'Low Tech', 'code': 'Lt', 'size': None, 'atm': None, 'hyd': None, 'pop': None, 'gov': None, 'law': None, 'tl': range(0, 6)},
        {'name': 'Non-Agricultural', 'code': 'Na', 'size': None, 'atm': range(0, 4), 'hyd': range(0, 4), 'pop': range(6, 16), 'gov': None, 'law': None, 'tl': None},
        {'name': 'Non-Industrial', 'code': 'Ni', 'size': None, 'atm': None, 'hyd': None, 'pop': range(4, 7), 'gov': None, 'law': None, 'tl': None},
        {'name': 'Poor', 'code': 'Po', 'size': None, 'atm': range(2, 6), 'hyd': range(0, 4), 'pop': None, 'gov': None, 'law': None, 'tl': None},
        {'name': 'Rich', 'code': 'Ri', 'size': None, 'atm': [6, 8], 'hyd': None, 'pop': range(6, 9), 'gov': range(4, 10), 'law': None, 'tl': None},
        {'name': 'Vacuum', 'code': 'Va', 'size': None, 'atm': [0], 'hyd': None, 'pop': None, 'gov': None, 'law': None, 'tl': None},
        {'name': 'Waterworld', 'code': 'Wa', 'size': None, 'atm': range(3, 10), 'hyd': [10], 'pop': None, 'gov': None, 'law': None, 'tl': None},
    ],
    'terrestrial_composition': { # Page 71
        'table': {
            2: {'comp': 'Exotic Ice', 'density': 0.03},
            3: {'comp': 'Mostly Ice', 'density': 0.18},
            4: {'comp': 'Mostly Ice', 'density': 0.18},
            5: {'comp': 'Mostly Ice', 'density': 0.18},
            6: {'comp': 'Mostly Rock', 'density': 0.50},
            7: {'comp': 'Rock and Metal', 'density': 0.82},
            8: {'comp': 'Rock and Metal', 'density': 0.82},
            9: {'comp': 'Rock and Metal', 'density': 0.82},
            10: {'comp': 'Rock and Metal', 'density': 0.82},
            11: {'comp': 'Rock and Metal', 'density': 0.82},
            12: {'comp': 'Mostly Metal', 'density': 1.15},
            13: {'comp': 'Mostly Metal', 'density': 1.15},
            14: {'comp': 'Mostly Metal', 'density': 1.15},
            15: {'comp': 'Compressed Metal', 'density': 1.50}
        }
    },
    'axial_tilt': { # Page 104
        2: lambda: random.randint(1, 6) / 50,
        3: lambda: random.randint(1, 6) / 50,
        4: lambda: random.randint(1, 6) / 50,
        5: lambda: random.randint(1, 6) / 5,
        6: lambda: random.randint(1, 6),
        7: lambda: random.randint(1, 6) + 6,
        8: lambda: random.randint(1, 6) + 6,
        9: lambda: (random.randint(1, 6) + 1) * 5,
        10: lambda: sum(random.randint(1, 6) for _ in range(2))
    }
}
