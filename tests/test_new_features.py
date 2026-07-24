import pytest
from worldmaker import (
    generate_full_system,
    generate_sector,
    generate_system_adventure_seeds,
    plot_system_3d_orbit_diagram,
    plot_subsector_trade_network,
    calculate_speculative_trade_run,
    export_campaign_briefing_html
)

def test_adventure_seeds():
    system = generate_full_system(name="Rumor System")
    seeds = generate_system_adventure_seeds(system)
    assert "starport_rumors" in seeds
    assert len(seeds["starport_rumors"]) > 0
    assert "plot_hooks" in seeds

def test_3d_visualization():
    system = generate_full_system(name="3D System")
    fig = plot_system_3d_orbit_diagram(system)
    assert fig is not None
    assert len(fig.data) > 0

def test_trade_network():
    subsector = generate_sector(width=8, height=10)
    fig = plot_subsector_trade_network(subsector)
    assert fig is not None
    assert len(fig.data) > 0

def test_trade_calculator():
    subsector = generate_sector(width=8, height=10)
    systems = list(subsector.systems.values())
    if len(systems) >= 2:
        res = calculate_speculative_trade_run(systems[0], systems[1])
        assert "distance_parsecs" in res
        assert "recommended_cargo" in res

def test_campaign_briefing_exporter():
    subsector = generate_sector(width=8, height=10)
    briefing = export_campaign_briefing_html(subsector, title="Test Sector Briefing")
    assert "<!DOCTYPE html>" in briefing
    assert "Test Sector Briefing" in briefing
