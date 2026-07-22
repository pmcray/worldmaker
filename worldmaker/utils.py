import random
import math

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

    @staticmethod
    def from_eHex(ehex_char):
        if not ehex_char:
            return 0
        if isinstance(ehex_char, int):
            return ehex_char
        ehex_char = str(ehex_char)
        if ehex_char.isdigit():
            return int(ehex_char)
        ehex_map = {
            'A': 10, 'B': 11, 'C': 12, 'D': 13, 'E': 14, 'F': 15, 'G': 16,
            'H': 17, 'J': 18, 'K': 19, 'L': 20, 'M': 21, 'N': 22, 'P': 23,
            'Q': 24, 'R': 25, 'S': 26, 'T': 27, 'U': 28, 'V': 29, 'W': 30,
            'X': 31, 'Y': 32, 'Z': 33
        }
        return ehex_map.get(ehex_char.upper(), 0)

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
