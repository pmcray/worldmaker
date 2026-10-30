import pytest

pytest.importorskip("cv2", reason="optional dependency for planet mapping")

import pytest
import numpy as np
from worldmaker import (
    generate_full_system,
    generate_planetary_maps,
    render_traveller_icosahedral_net,
    plot_3d_planet_globe
)

def test_planet_mapper():
    system = generate_full_system(name="Aethelgard System")
    mainworld = next((w for w in system.all_worlds if w.is_mainworld), None)
    assert mainworld is not None
    
    maps_data = generate_planetary_maps(mainworld, width=256, height=128)
    assert "surface_texture" in maps_data
    assert "heightmap" in maps_data
    assert "land_mask" in maps_data
    assert "hydro_fraction" in maps_data
    
    texture = maps_data["surface_texture"]
    assert isinstance(texture, np.ndarray)
    assert texture.shape == (128, 256, 3)

def test_traveller_icosahedral_net():
    system = generate_full_system(name="Aethelgard System")
    mainworld = next((w for w in system.all_worlds if w.is_mainworld), None)
    maps_data = generate_planetary_maps(mainworld, width=256, height=128)
    
    ico_net = render_traveller_icosahedral_net(maps_data["surface_texture"], S=100)
    assert isinstance(ico_net, np.ndarray)
    assert ico_net.shape[0] > 0
    assert ico_net.shape[1] > 0

def test_3d_planet_globe():
    system = generate_full_system(name="Aethelgard System")
    mainworld = next((w for w in system.all_worlds if w.is_mainworld), None)
    maps_data = generate_planetary_maps(mainworld, width=256, height=128)
    
    fig_globe = plot_3d_planet_globe(maps_data["surface_texture"], world_name=mainworld.name)
    assert fig_globe is not None
    assert len(fig_globe.data) > 0
