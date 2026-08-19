import random
from typing import Dict, Any, List
from .classes import StellarSystem, PlanetaryBody
from .utils import Utils

def generate_system_adventure_seeds(system: StellarSystem) -> Dict[str, Any]:
    """
    Generates adventure seeds, starport rumors, political faction tensions, 
    and environmental hazard tables according to WBH Ch. 15.
    """
    mainworld = system.mainworld
    
    rumors = []
    faction_events = []
    hazards = []
    plot_hooks = []
    
    if mainworld:
        tcodes = mainworld.trade_codes
        uwp = mainworld.uwp
        
        # 1. Trade Code Specific Rumors
        if "Ag" in tcodes:
            rumors.append("Local agricultural syndicates report bio-engineered crop blights spreading from off-world cargo drops.")
            rumors.append("A renegade hydro-farmer claims to have discovered unmapped subterranean aquifer reserves.")
        if "In" in tcodes:
            rumors.append("Heavy industrial automated plants have suffered unexplained cybernetic command overrides.")
            rumors.append("Corporate security forces are offering high bounties for retrieved prototype schematics.")
        if "Hi" in tcodes:
            rumors.append("A high-tech research lab leaked an experimental quantum encryption core on the black market.")
        if "De" in tcodes:
            rumors.append("Scouts reported seeing ancient pre-collapse water harvesters active in the deep wastes.")
        if "Va" in tcodes or "As" in tcodes:
            rumors.append("Belters claim a rogue uncatalogued nickel-iron asteroid contains high-grade radioactives.")
        if "Rich" in tcodes:
            rumors.append("An influential high-society dynasty is covertly hiring mercenary escorts for a secret expedition.")
        if "Po" in tcodes or "Ba" in tcodes:
            rumors.append("Local free-trade enclaves are arming against predatory pirate raids operating from an unmapped gas giant moon.")

        # Default rumors if few trade codes
        if len(rumors) < 2:
            rumors.append("Off-world free traders report unusual jump-space gravity shears along the main trade lane.")
            rumors.append("Starport customs officials are enforcing strict quarantine checks on all incoming bio-samples.")

        # 2. Faction Tensions & Political Events (WBH p. 192)
        pop_val = Utils.from_eHex(uwp.population)
        gov_val = Utils.from_eHex(uwp.government)
        law_val = Utils.from_eHex(uwp.law_level)
        
        if gov_val in [2, 7]: # Authoritarian / Strict
            faction_events.append("Underground insurgent cells are planning a coordinated strike against orbital customs relays.")
        elif gov_val in [4, 5]: # Representative / Corporate
            faction_events.append("Competing mega-corporate lobbyists are bribing local port authorities for exclusive docking rights.")
        elif gov_val == 0: # Anarchy
            faction_events.append("Local warlord clans are locked in a territorial war over the primary starport fuel depot.")
        else:
            faction_events.append("Political reform rallies are causing civil unrest in the starport downport sector.")

        if law_val >= 9:
            faction_events.append("Extreme law level enforcement: All off-world weapons and grav-vehicles are impounded upon landing.")

        # 3. Environmental Hazards (WBH Ch. 9 & 10)
        atm_val = Utils.from_eHex(uwp.atmosphere)
        temp_k = mainworld.mean_temperature
        
        if atm_val in [0, 1]:
            hazards.append("Vacuum / Trace Atmosphere: Suit puncture or airlock failure will cause rapid explosive decompression.")
        elif atm_val in [2, 3, 13, 14, 15]:
            hazards.append("Corrosive / Toxic Atmosphere: Standard suit filters degrade rapidly without specialized chemical seals.")
        elif atm_val in [10, 11, 12]:
            hazards.append("Dense / Exotic Atmosphere: High atmospheric pressure impairs mobility and increases grav-vehicle drag.")

        if temp_k < 230:
            hazards.append("Extreme Cryogenic Cold: Sub-zero temperatures freeze standard hydraulic fluids and drain power cells.")
        elif temp_k > 330:
            hazards.append("Thermal Heat Hazard: Extreme surface temperatures overload cooling suits within 2 hours of exposure.")

        if mainworld.life_details and "Extensive" in mainworld.life_details:
            hazards.append("Aggressive Local Biosphere: Venomous airborne micro-fauna require bio-hazard filtration.")

    # 4. Deep System Plot Hooks
    poi_worlds = [w for w in system.all_worlds if w.notes]
    if poi_worlds:
        plot_hooks.append(f"Anomalous Signal: Sensors detect emergency beacon bursts from {poi_worlds[0].designation}.")
    
    gas_giants = [w for w in system.all_worlds if w.body_type == 'Gas Giant']
    if gas_giants and gas_giants[0].satellites:
        moon = gas_giants[0].satellites[0]
        plot_hooks.append(f"Hidden Base: An unregistered corsair refueling cache has been spotted in the shadow of moon {moon.designation}.")

    if not plot_hooks:
        plot_hooks.append("Derelict Beacon: An automated scout probe in orbit holds encrypted navigation charts to an unmapped star system.")

    return {
        "starport_rumors": rumors[:3],
        "faction_events": faction_events,
        "environmental_hazards": hazards if hazards else ["Standard shirt-sleeve environment; no extreme physical hazards."],
        "plot_hooks": plot_hooks
    }
