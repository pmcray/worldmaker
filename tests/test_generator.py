import pytest
from worldmaker.generator import generate_full_system, generate_short_profile, generate_long_profile
from worldmaker.sector import generate_sector, generate_sector_svg, generate_subsector_svg
from worldmaker.exporters import export_system_markdown, create_system_dataframe

def test_generate_full_system():
    system = generate_full_system(name="Sol Invictus")
    assert system.name == "Sol Invictus"
    assert len(system.all_worlds) > 0
    
    short_prof = generate_short_profile(system)
    long_prof = generate_long_profile(system)
    assert len(short_prof) > 0
    assert len(long_prof) > 0
    
    df = create_system_dataframe(system)
    assert not df.empty
    
    md = export_system_markdown(system)
    assert "Sol Invictus" in md

def test_generate_sector():
    subsector = generate_sector()
    assert len(subsector.systems) > 0
    
    svg = generate_sector_svg([subsector])
    assert "<svg" in svg
    
    subsector_svg = generate_subsector_svg(subsector, name="Test Subsector")
    assert "<svg" in subsector_svg
