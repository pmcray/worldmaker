"""Tests for the modular Foreven 1105 scenario system, settlement waves,
and always-on Earth/Solar System analogue identification."""

import worldmaker as wm


def test_default_foreven_scenario_is_strict_1105_canon():
    """Out-of-the-box ForevenScenario() must represent the absolute minimum
    Strict 1105 Canon (FFE 2008 Reserve + Classic Traveller citations)."""
    cfg = wm.ForevenScenario()
    assert cfg.current_year == 1105
    assert cfg.canonical_positions_358 is True
    assert cfg.zhodani_consulate_border is True
    assert cfg.subsector_naming_mode == "ffe_4"
    assert cfg.strict_1105_worlds is True
    assert cfg.classic_named_systems is True
    assert cfg.am5_droyne_worlds is True
    assert cfg.parthinia_issugur is True
    assert cfg.canonical_corporations is True

    # Deuterocanonical, SCG, third-party, and custom factions are off by default
    assert cfg.imperial_lines_anchors is False
    assert cfg.rimward_polity_mode == "none"
    assert cfg.mnemosyne_principality is False
    assert cfg.scg_tlesho_union is False
    assert cfg.scg_native_sophonts is False
    assert cfg.scg_ancients_ruins is False
    assert cfg.scg_scattered_settlements is False
    assert cfg.scg_barren_anomaly is False
    assert cfg.scg_strategic_bases is False
    assert cfg.zhodani_base_reidain is False
    assert cfg.jbe_foreven_worlds is False
    assert cfg.mongoose_1e_reidain_salient is False
    assert cfg.custom_heptamorphs is False
    assert cfg.custom_uplifted_cats is False
    assert cfg.custom_halfling_shires is False
    assert cfg.christen_erith is False


def test_strict_1105_canon_overlay_contents():
    canon = wm.build_foreven_canon(wm.ForevenScenario())
    assert len(canon.hexes) == 358
    groups = canon.allegiance_groups()
    assert len(groups["ZhIN"]) == 142
    assert set(canon.subsector_names.keys()) == {"D", "H", "L", "P"}
    assert canon.subsector_names["D"] == "Massina"
    assert canon.subsector_names["H"] == "Fessor"
    assert canon.subsector_names["L"] == "Reidain"
    assert canon.subsector_names["P"] == "Urnian"

    # Statted canonical worlds
    assert canon.worlds["1212"].name == "Zdovesil"
    assert canon.worlds["1212"].uwp == "A65588A-9"
    assert canon.worlds["3229"].name == "Alenzar"
    assert canon.worlds["3229"].uwp == "C000414-9"
    assert canon.worlds["3230"].name == "Raschev"
    assert canon.worlds["3230"].uwp == "C8697C4-6"

    # Classic named unstatted systems
    assert canon.worlds["1618"].name == "Tlebria"
    assert canon.worlds["2211"].name == "Purfyr"
    assert canon.worlds["2415"].name == "Cocta"
    assert canon.worlds["2415"].annotation_only is True

    # Alien Module 5 Droyne & Parthinia Issugur
    assert canon.worlds["0513"].sophont == "Droyne"
    assert canon.worlds["3003"].sophont == "Droyne"
    assert canon.worlds["3018"].name == "Parthinia"
    assert canon.worlds["3018"].sophont == "Issugur"

    # Canonical corporations
    corp_names = {c["name"] for c in canon.corporations}
    assert corp_names == {"Iadria Vlovl", "Priantqlovr Drafr", "InStarSpec"}

    # Deuterocanonical worlds are NOT pinned in Strict 1105
    assert not canon.worlds["2523"].has_name  # Hollis
    assert not canon.worlds["1636"].has_name  # Avalar


def test_generate_foreven_1105_strict_and_analogues():
    sector = wm.generate_foreven_1105(seed=1105)
    assert len(sector.systems) == 358
    assert sector.subsector_names == {
        "D": "Massina",
        "H": "Fessor",
        "L": "Reidain",
        "P": "Urnian",
    }
    assert sector.systems["1212"].mainworld.name == "Zdovesil"
    assert str(sector.systems["1212"].mainworld.uwp) == "A65588A-9"
    assert sector.systems["3229"].mainworld.name == "Alenzar"
    assert any(w.name == "Chamax" for w in sector.systems["3229"].all_worlds)
    assert sector.systems["1618"].mainworld.name == "Tlebria"
    assert "Iadria Vlovl" in sector.systems["1618"].corporations
    assert sector.systems["2211"].mainworld.name == "Purfyr"
    assert sector.native_sophonts["0513"].name == "Droyne"
    assert sector.native_sophonts["3003"].name == "Droyne"
    assert sector.native_sophonts["3018"].name == "Issugur"

    # Earth-like, Solar System-like, and Solar analogue evaluations always run
    assert sector.erith_hex in sector.systems
    assert len(sector.earth_analogues) == 10
    assert sector.solar_system_analogue_hex in sector.systems
    assert len(sector.solar_system_analogues) == 10
    assert sector.solar_analogue_hex in sector.systems
    assert len(sector.solar_analogues) == 10
    # In Strict 1105 (christen_erith=False), the top Earth analogue is not renamed to 'Erith'
    assert sector.systems[sector.erith_hex].mainworld.name != "Erith"


def test_deuterocanonical_and_community_toggles():
    cfg = wm.ForevenScenario.from_preset(
        "community_synthesis_1105",
        hollis_babylon5_mode=True,
        include_cocta_2415=True,
    )
    canon = wm.build_foreven_canon(cfg)
    assert len(canon.hexes) == 359  # 358 + Cocta (2415)
    assert canon.subsector_names["A"] == "Shivva"
    assert canon.subsector_names["C"] == "Shial"
    assert canon.subsector_names["L"] == "Reidain"

    # Hollis in Babylon-5 Scout-only diplomatic mode
    assert canon.worlds["2523"].name == "Hollis"
    assert canon.worlds["2523"].uwp == "B370642-B"
    assert canon.worlds["2523"].bases == "S"

    # Die Weltbund (1105 neutral Confederation of Worlds)
    assert canon.worlds["1636"].name == "Avalar"
    assert canon.worlds["1636"].allegiance == "Wb"
    assert len(canon.allegiance_groups()["Wb"]) == 27

    # Mnemosyne Principality
    assert canon.worlds["0734"].name == "Mnemosyne"
    assert canon.worlds["0734"].allegiance == "Mn"

    # Zhodani Base Reidain (2925) & Kamrathi League
    assert canon.worlds["2925"].name == "Reidain"
    assert canon.worlds["2925"].uwp == "C9EA97B-D"
    assert len(canon.allegiance_groups()["Km"]) == 4

    # JBE Cornathian Empire & Warpride
    assert canon.worlds["2715"].name == "Cornathia"
    assert canon.worlds["2715"].allegiance == "Co"
    assert "Warpride" in canon.worlds["2136"].name


def test_settlement_wave_mechanics_and_exports():
    sector = wm.generate_foreven_1105(
        seed=1105,
        preset="deuterocanon_1105",
    )
    assert len(sector.settlement_waves) == 5

    # Coreward Zhodani heartland (Zdovesil 1212) has Thick Mature wave (+1 DM)
    zdo_strata = sector.systems["1212"].settlement_strata
    assert any(st["wave_id"] == "zhodani_coreward_thick" and st["wave_dm"] == 1 for st in zdo_strata)

    # Massina (3003) has both Imperial Trailing Thin Wave and Zhodani Post-FFW II Thin Wave
    m_strata = sector.systems["3003"].settlement_strata
    wave_ids = {st["wave_id"] for st in m_strata}
    assert {"imperial_trailing_thin", "zhodani_frontier_thin"} <= wave_ids

    # DataFrames & SVG map
    wdf = wm.create_settlement_waves_dataframe(sector)
    assert len(wdf) == 5
    sdf = wm.create_settlement_strata_dataframe(sector)
    assert len(sdf) == 358
    adf = wm.create_analogues_dataframes(sector)
    assert set(adf.keys()) == {"earth_analogues", "solar_system_analogues", "solar_analogues"}
    svg = wm.generate_settlement_wave_svg(sector)
    assert svg.startswith("<svg") and svg.endswith("</svg>")
    summary_md = wm.describe_sector_analogues(sector)
    assert "Most Earth-like World" in summary_md
    assert "Most Solar System-like Architecture" in summary_md
