import random
import math
from typing import List, Dict, Any, Tuple, Optional

from .classes import Star, PlanetaryBody, StellarSystem
from .utils import Utils
from .data import DATA
from .stellar import generate_world_name

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
        if len(system.stars) >= 2: dm_quantity += 1 # System consists of two or more stars

        roll = Utils.D6(2) + dm_quantity
        roll = max(DATA['planetoid_belt_quantity']['min_roll'], min(roll, DATA['planetoid_belt_quantity']['max_roll']))
        system.planetoid_belt_count = DATA['planetoid_belt_quantity']['roll_map'][roll]

    # Terrestrial Planets 
    dm_quantity = 0
    if is_post_stellar: dm_quantity -= 1 # DM-1 per post-stellar object (including primary star)
    
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
    forbidden_zones = []
    for star in system.stars:
        if star.designation in stability_spheres_orbit:
            orbit_val = stability_spheres_orbit[star.designation]
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
            
            # Rule 7: If eccentricity > 0.5, add another Orbit# on either side
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
        # Place the baseline orbit at the nearest available Orbit# with variance
        closest_dist = float('inf')
        new_orbit = system.baseline_orbit
        variance_roll = (Utils.D6(2) - 7) / 10.0

        for start, end in primary_group.available_orbits:
            if system.baseline_orbit < start:
                dist_to_start = start - system.baseline_orbit
                if dist_to_start < closest_dist:
                    closest_dist = dist_to_start
                    new_orbit = start + variance_roll
            elif system.baseline_orbit > end:
                dist_to_end = system.baseline_orbit - end
                if dist_to_end < closest_dist:
                    closest_dist = dist_to_end
                    new_orbit = end + variance_roll
            else:
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
    empty_roll = Utils.D6(2)
    if empty_roll == 10: system.empty_orbit_count = 1
    elif empty_roll == 11: system.empty_orbit_count = 2
    elif empty_roll == 12: system.empty_orbit_count = 3
    else: system.empty_orbit_count = 0

    anomalous_roll = Utils.D6(2)
    num_anomalous = 0
    if anomalous_roll == 10: num_anomalous = 1
    elif anomalous_roll == 11: num_anomalous = 2
    elif anomalous_roll == 12: num_anomalous = 3

    for _ in range(num_anomalous):
        anomaly_type_roll = Utils.D6(2)
        anomaly_type = 'random'
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
        if primary_group.available_orbits:
            zone = random.choice(primary_group.available_orbits)
            ano_orbit = random.uniform(zone[0], zone[1])
            slots.append({'orbit_num': round(ano_orbit, 2), 'type': 'anomalous', 'anomaly': anomaly})
    
    return sorted(slots, key=lambda x: x['orbit_num'])

def place_worlds(system: StellarSystem, orbital_slots: List[dict]):
    """Places worlds into the generated orbital slots."""
    slots_map = {i: {'slot': s, 'body': None} for i, s in enumerate(orbital_slots)}
    
    placements = []
    placements.extend([{'type': 'Empty', 'count': system.empty_orbit_count}])
    placements.extend([{'type': 'Gas Giant', 'count': system.gas_giant_count}])
    placements.extend([{'type': 'Planetoid Belt', 'count': system.planetoid_belt_count}])
    
    num_slots = len(slots_map)
    available_slots_indices = list(range(num_slots))
    random.shuffle(available_slots_indices)
    
    mainworld_slot_idx = -1

    for item in placements:
        count_to_place = item['count']
        placed_count = 0
        while placed_count < count_to_place and available_slots_indices:
            slot_idx = available_slots_indices.pop(0)
            
            if slots_map[slot_idx]['body'] is not None:
                available_slots_indices.append(slot_idx)
                continue

            if slots_map[slot_idx]['slot']['type'] == 'anomalous' and item['type'] == 'Empty':
                 available_slots_indices.append(slot_idx)
                 continue 
            
            slots_map[slot_idx]['body'] = item['type']
            placed_count += 1

            if item['type'] == 'Gas Giant' and mainworld_slot_idx != -1 and slot_idx == mainworld_slot_idx:
                pass

    for slot_idx in available_slots_indices:
        slots_map[slot_idx]['body'] = 'Terrestrial'
        
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
        
        body.orbit_au = Utils.orbit_to_au(body.orbit_num)
        
        if body.body_type != 'Planetoid Belt':
            ecc_roll = Utils.D6(2)
            if slot_info['slot'].get('anomaly'):
                anomaly_type = slot_info['slot']['anomaly']['type']
                if anomaly_type == 'eccentric':
                    ecc_roll += 4
                elif anomaly_type == 'retrograde':
                    body.notes.append("Retrograde Orbit")
                elif anomaly_type == 'inclined':
                    body.inclination = (Utils.D6(2) * 5) + Utils.D6()
                    body.notes.append(f"Inclined Orbit: {body.inclination} degrees")
                elif anomaly_type == 'trojan':
                    body.notes.append("Trojan Orbit")

            ecc_data = DATA['eccentricity_values'].get(min(12, max(5, ecc_roll)))
            if ecc_data:
                base_ecc = ecc_data['base']
                roll_ecc = ecc_data['roll']()
                body.eccentricity = round(max(0.0, min(0.999, base_ecc + roll_ecc)), 3)

        total_mass_for_period = primary_group.mass

        if primary_group.is_composite:
            total_mass_for_period = sum(s.mass for s in system.stars if s.designation in primary_group.components)
        
        if body.body_type == 'Gas Giant':
            gas_giant_solar_mass = 0.005 # average gas giant mass
            total_mass_for_period += gas_giant_solar_mass

        body.period_years = math.sqrt(body.orbit_au**3 / total_mass_for_period)
        
        primary_group.orbiting_bodies.append(body)
