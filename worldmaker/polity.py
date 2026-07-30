import random
from typing import List, Dict, Any, Tuple, Optional

from .classes import Polity, Sector, UWP, StellarSystem
from .utils import Utils

def define_polities(sector: Sector):
    """Defines major interstellar polities and pocket empires in Foreven-like space."""
    # 1. Zhodani Consulate (Coreward / Spinward)
    zhodani = Polity(
        name="Zhodani Consulate", 
        capital_hex="0101", 
        allegiance_code="Zh",
        polity_type="Major Race Polity",
        defense_index=9
    )
    # Define Zhodani territory (top-left quadrant)
    for col in range(1, 9): 
        for row in range(1, 5): 
            hex_coord = f"{col:02d}{row:02d}"
            zhodani.controlled_systems.append(hex_coord)
    
    # 2. Avalar Consulate (Rimward / Spinward - Pocket Empire)
    avalar = Polity(
        name="Avalar Consulate", 
        capital_hex="1636", 
        allegiance_code="Av",
        polity_type="Pocket Empire",
        defense_index=5
    )
    avalar_systems = ["1636", "1534", "1734", "1635", "1535", "1735", "1637"]
    avalar.controlled_systems.extend(avalar_systems)

    # 3. Third Imperium (Trailing / Rimward)
    imperium = Polity(
        name="Third Imperium", 
        capital_hex="3240", 
        allegiance_code="Im",
        polity_type="Major Race Polity",
        defense_index=10
    )
    # Define Imperial territory (bottom-right corner)
    for col in range(25, 33):
        for row in range(35, 41):
            hex_coord = f"{col:02d}{row:02d}"
            imperium.controlled_systems.append(hex_coord)

    polities = [zhodani, avalar, imperium]
    sector.polities = polities

    # Assign polities to the sector systems
    for polity in polities:
        for hex_coord in polity.controlled_systems:
            if hex_coord in sector.systems:
                sector.systems[hex_coord].allegiance = polity.allegiance_code

def generate_travel_zones(sector: Sector):
    """Assigns Amber/Red Travel Zones using the SCG p.27 rules of thumb:
    Exotic/Corrosive/Insidious atmospheres and worlds whose Government +
    Law Level total 20+ are Amber candidates, as are Balkanised worlds
    with ongoing conflicts. Red Zones are rare interdictions."""
    for hex_coord, system in sector.systems.items():
        mainworld = system.mainworld
        if not mainworld:
            continue

        uwp = mainworld.uwp
        atm = Utils.from_eHex(uwp.atmosphere)
        gov = Utils.from_eHex(uwp.government)
        law = Utils.from_eHex(uwp.law_level)
        pop = Utils.from_eHex(uwp.population)

        zone = ""
        if atm in (10, 11, 12) and Utils.D6(2) >= 9:  # Exotic/Corrosive/Insidious, hazardous cases
            zone = "A"
        elif gov + law >= 20:
            zone = "A"
        elif gov == 7 and Utils.D6(2) >= 10:  # Balkanised, ongoing conflict
            zone = "A"

        # Rare interdictions: hazardous Amber worlds and empty interdicted
        # worlds escalate to Red on boxcars.
        if zone == "A" and Utils.D6(2) == 12:
            zone = "R"
        elif pop == 0 and Utils.D6(2) == 12:
            zone = "R"

        system.travel_zone = zone

def generate_bases(sector: Sector):
    """Generates bases for systems based on Starport, Allegiance, and defense indicators (SCG rules)."""
    for hex_coord, system in sector.systems.items():
        mainworld = system.mainworld
        if not mainworld: continue
        
        uwp = mainworld.uwp
        port = uwp.starport
        allegiance = system.allegiance
        
        bases = []
        
        # Imperial / Generic Rules
        if allegiance in ["Im", "Av", "Na", "Cs"]:
            if port == 'A':
                if Utils.D6(2) >= 8: bases.append("Naval")
                if Utils.D6(2) >= 10: bases.append("Scout")
                if Utils.D6(2) >= 8: bases.append("Tas")
            elif port == 'B':
                if Utils.D6(2) >= 8: bases.append("Naval")
                if Utils.D6(2) >= 8: bases.append("Scout")
                if Utils.D6(2) >= 12: bases.append("Pirate")
            elif port == 'C':
                if Utils.D6(2) >= 8: bases.append("Scout")
                if Utils.D6(2) >= 10: bases.append("Pirate")
            elif port == 'D':
                if Utils.D6(2) >= 7: bases.append("Scout")
                if Utils.D6(2) >= 12: bases.append("Pirate")
            elif port == 'E':
                if Utils.D6(2) >= 12: bases.append("Pirate")
        
        # Zhodani Rules (Guide p. 63)
        elif allegiance == "Zh":
            if port == 'A':
                if Utils.D6(2) >= 8: bases.append("Zhodani Naval")
                if Utils.D6(2) >= 10: bases.append("Zhodani Base")
            elif port == 'B':
                if Utils.D6(2) >= 8: bases.append("Zhodani Naval")
        
        system.bases = bases
