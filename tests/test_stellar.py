import pytest
from worldmaker.stellar import generate_primary_star, generate_stellar_system_stars
from worldmaker.classes import StellarSystem, Star

def test_generate_primary_star():
    star = generate_primary_star()
    assert isinstance(star, Star)
    assert star.spectral_type != ""
    assert star.mass > 0
    assert star.luminosity >= 0
    assert star.hzco > 0
    assert star.mao > 0

def test_generate_stellar_system_stars():
    system = StellarSystem(name="Test System")
    generate_stellar_system_stars(system)
    assert len(system.stars) >= 1
    assert system.primary_star is not None
    assert system.primary_star.spectral_type != ""
