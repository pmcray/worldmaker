__version__ = "0.1.0"

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
    enforce_sustainable_tech_level,
)
from .technology import generate_technology_profile, tlm
from .belts import detail_belt, detail_system_belts
from .secondary import (
    generate_secondary_populations,
    max_secondary_population,
    secondary_population_code,
    settlement_candidates,
    settlement_appeal,
    can_be_inhabited,
)
from .scenarios import (
    worst_case_temperatures,
    seasonal_temperature,
    seasonal_axial_tilt_factor,
    latitude_zone,
    latitude_temperature,
    latitude_temperature_profile,
    time_of_day_temperature,
    hourly_rotation_factor,
    sunlight_portion,
    sunlight_hours,
    twilight_rotation_factor,
    altitude_temperature,
    star_temperature_contributions,
    add_temperatures,
    gas_giant_inherent_temperature,
    detail_temperature_scenarios,
)
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
    get_catalogued_race,
    generate_minor_race,
    generate_sophont_name,
    roll_d66_characteristic,
    MAJOR_RACES,
    CATALOGUED_RACES,
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
    route_style_for,
    ROUTE_STYLES,
    name_subsectors,
    subsector_letter,
)
from .special import (
    generate_white_dwarf,
    generate_neutron_star,
    generate_black_hole,
    generate_brown_dwarf,
    brown_dwarf_type,
    generate_dead_star_system,
    generate_brown_dwarf_system,
    generate_protostar_system,
    generate_primordial_system,
    is_primordial_host,
    generate_rogue_gas_giant,
    generate_rogue_terrestrial,
    generate_rogue_small_body,
    generate_empty_hex,
    populate_empty_hexes,
    generate_nebula,
    generate_star_cluster_hex,
    generate_artificial_world,
    jump_dm_for_target,
    jump_restrictions,
    EmptyHexSurvey,
    EMPTY_HEX_OBJECTS,
    ARTIFICIAL_WORLD_TYPES,
    BROWN_DWARF_TYPES,
    WHITE_DWARF_AGING,
)
from .canon import (
    CanonicalWorld,
    CanonicalSector,
    parse_travellermap_tab,
    fetch_canonical_sector,
    load_canonical_sector,
    scg_foreven,
    scg_foreven_full,
    merge_canon,
    apply_canon,
    canonical_polities,
    apply_canonical_world,
    expand_polity_from_capital,
    place_canonical_sophonts,
    establish_canon_polities,
    NON_ALIGNED_CODES,
    cache_dir,
    ALLEGIANCE_NAMES,
    SCG_FOREVEN,
    SCG_FOREVEN_FULL,
    SCG_AVALAR,
    SCG_TLESHO_UNION,
    SCG_NATIVE_SOPHONTS,
    SCG_SCATTERED_SETTLEMENTS,
    SCG_BARREN,
    SCG_ZHODANI_WAYPOINTS,
    SCG_IMPERIAL_CAGE,
    SCG_FOREVEN_TECH_CEILINGS,
)
from .universe import (
    Universe,
    Anomaly,
    TimelineEvent,
    create_universe,
    generate_universe_sector,
    build_default_timeline,
    UNIVERSE_PRESETS,
    DENSITY_TARGETS,
    TECHNOLOGY_LEVELS,
    TRAJECTORIES,
    SOPHONT_PREVALENCE,
    THEMES,
    ANOMALY_KINDS,
)
from .t5 import (
    export_sector_t5_column,
    export_sector_t5_tab,
    parse_t5_column,
    t5_row,
    T5_FIELDS,
)
from .nations import (
    Nation,
    generate_nations,
    describe_nations,
    nations_per_faction,
    total_nation_count,
    assign_territories,
    land_cells,
)
from .cultures import (
    CultureTemplate,
    CULTURE_TEMPLATES,
    FAMILIES,
    TRAIT_KEYS,
    culture_from_template,
    culture_for_template,
    procedural_culture,
    suggest_template,
    apply_template_palette,
    templates_in_family,
    templates_for_tech_level,
    describe_palette,
    culture_profile_string,
)
from .findworld import (
    WorldProfile,
    Match,
    find_worlds,
    best_world,
    score_world,
    describe_matches,
    in_habitable_zone,
    make_proprietary,
    impose_profile,
    make_erith,
    PROFILES,
    ERITH,
    GARDEN_WORLD,
    REFUELLING_STOP,
)
from .notable import (
    Notable,
    find_notable,
    find_exotic_systems,
    notability,
    describe_notable,
)
from .exporters import (
    create_system_dataframe,
    create_sector_dataframe,
    export_system_markdown,
    export_sector_sec_file,
)
from .generator import generate_full_system, select_mainworld
from .planet import (
    TERRA,
    SphereNoise,
    earthlike_score,
    find_earthlike_candidate,
    generate_planet_surface,
    classify_surface_terrain,
    icosahedron_faces,
    render_orbital_view,
    render_orbital_sequence,
    render_icosahedral_net_svg,
    render_dodecahedral_net,
    render_planet_package,
    save_png,
)

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
