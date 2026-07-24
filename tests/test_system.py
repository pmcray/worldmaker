import pytest
from worldmaker.classes import StellarSystem
from worldmaker.stellar import generate_stellar_system_stars
from worldmaker.system import (
    determine_world_counts,
    calculate_available_orbits,
    calculate_baseline_and_spread,
    handle_anomalies_and_empties,
    generate_orbital_slots,
    place_worlds
)

def test_system_pipeline():
    system = StellarSystem(name="Test System")
    generate_stellar_system_stars(system)
    determine_world_counts(system)
    
    # Test both stability models
    orbits_simple = calculate_available_orbits(system, model='simple')
    orbits_physics = calculate_available_orbits(system, model='physics')
    assert len(orbits_simple) > 0
    assert len(orbits_physics) > 0

    calculate_baseline_and_spread(system)
    assert system.baseline_number > 0
    assert system.spread > 0

    handle_anomalies_and_empties(system)
    slots = generate_orbital_slots(system)
    assert len(slots) > 0

    place_worlds(system, slots)
    assert len(system.all_worlds) > 0
