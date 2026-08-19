from .classes import Sector, StellarSystem, Star, PlanetaryBody, Satellite, UWP, CulturalProfile, Sophont, Polity, Wave
from .utils import Utils
from .data import DATA
from .stellar import generate_primary_star, generate_stellar_system_stars, generate_world_name
from .system import (
    determine_world_counts,
    calculate_available_orbits,
    calculate_baseline_and_spread,
    handle_anomalies_and_empties,
    generate_orbital_slots,
    place_worlds
)
from .atmosphere import (
    generate_atmosphere_details,
    total_pressure,
    oxygen_fraction,
    scale_height,
    pressure_at_altitude,
    check_runaway_greenhouse
)
from .economics import generate_economics, calculate_wtn, calculate_importance
from .government import generate_government_details, generate_factions
from .population import (
    generate_population_details,
    calculate_pcr,
    calculate_urbanisation,
    minimum_sustainable_tl,
)
from .technology import generate_technology_profile, tlm
from .belts import detail_belt, detail_system_belts
from .worldmap import (
    generate_world_terrain,
    render_world_map_svg,
    terrain_summary,
    TERRAIN,
)
from .starport import (
    generate_starport_facilities,
    generate_military,
    detail_starport_and_military,
    STARPORT_FACILITIES,
)
from .geophysics import (
    detail_placed_worlds,
    generate_atmosphere,
    generate_hydrographics,
    generate_geophysics,
    generate_rotation_period,
    calculate_mean_temperature,
    generate_surface_features,
    generate_life,
    place_satellites,
    calculate_habitability_rating,
    calculate_hill_sphere_pd
)
from .society import (
    generate_mainworld_uwp,
    generate_trade_codes,
    generate_social_details,
    generate_expanded_tech_matrix,
    generate_cultural_profile
)
from .sophont import (
    get_major_race,
    generate_minor_race,
    generate_sophont_name,
    roll_d66_characteristic,
    MAJOR_RACES,
)
from .polity import (
    define_polities,
    define_foreven_polities,
    generate_polities,
    generate_bases,
    generate_travel_zones,
)
from .sector import (
    generate_sector,
    generate_full_sector,
    merge_subsectors,
    generate_sector_svg,
    generate_subsector_svg,
    calculate_xboat_routes,
    name_subsectors,
    subsector_letter,
)
from .exporters import create_system_dataframe, export_system_markdown, export_sector_sec_file
from .generator import generate_full_system, select_mainworld

# --------------------------------------------------------------------------
# Optional extras.
#
# These modules need heavier third-party packages - OpenCV, plotly,
# matplotlib, networkx, ipywidgets - that are not required to generate
# systems, sectors or the classic maps. They are resolved on first use so
# `import worldmaker` keeps working when those packages are absent.
# --------------------------------------------------------------------------
_OPTIONAL_EXPORTS = {
    'generate_planetary_maps': '.planet_mapper',
    'render_traveller_icosahedral_net': '.planet_projections',
    'plot_3d_planet_globe': '.planet_projections',
    'plot_system_orbit_diagram': '.visualization',
    'plot_system_3d_orbit_diagram': '.visualization_3d',
    'plot_subsector_trade_network': '.trade_network',
    'calculate_speculative_trade_run': '.trade_calculator',
    'export_campaign_briefing_html': '.pdf_exporter',
    'generate_system_adventure_seeds': '.adventure',
    'render_generator_dashboard': '.widgets',
    'render_subsector_dashboard': '.widgets',
    'export_system_html': '.exporters',
}


def __getattr__(name):
    """Resolves the optional extras on first access (PEP 562)."""
    module_name = _OPTIONAL_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import importlib
    try:
        module = importlib.import_module(module_name, __name__)
    except ImportError as exc:
        raise ImportError(
            f"{name}() needs an optional dependency that is not installed "
            f"({exc}). Install the extras with:  pip install "
            f"'worldmaker[extras]'  or see requirements-extras.txt"
        ) from exc
    return getattr(module, name)


def __dir__():
    return sorted(list(globals()) + list(_OPTIONAL_EXPORTS))
