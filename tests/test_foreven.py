import pytest
from worldmaker import (
    generate_foreven_sector,
    generate_sector_svg,
    generate_subsector_svg,
    export_sector_sec_file,
    export_foreven_gazetteer_markdown,
    FOREVEN_RESERVE_HEXES,
    FOREVEN_ZHODANI_HEXES,
    FOREVEN_SUBSECTORS,
    FOREVEN_FIXED_SYSTEMS,
    SUBSECTOR_J_BARREN_ANOMALY,
    evaluate_planetary_age_habitability,
    find_solar_analogues,
    find_solar_system_analogues,
    find_earth_analogues,
)


@pytest.fixture(scope="module")
def foreven_data():
    sector, subsectors = generate_foreven_sector(seed=1107)
    return sector, subsectors


def test_foreven_canonical_hex_positions_and_subsectors(foreven_data):
    sector, subsectors = foreven_data
    assert len(sector.systems) == 358
    assert set(sector.systems.keys()) == set(FOREVEN_RESERVE_HEXES)
    assert len(subsectors) == 16

    # Check FFE Reserve canonical subsector names
    assert sector.subsector_names["D"] == "Massina"
    assert sector.subsector_names["H"] == "Fessor"
    assert sector.subsector_names["L"] == "Reidain"
    assert sector.subsector_names["P"] == "Urnian"

    # Total systems across the 16 subsectors must equal 358
    assert sum(len(sub.systems) for sub in subsectors) == 358


def test_foreven_canonical_worlds_and_polities(foreven_data):
    sector, _ = foreven_data

    # Key canonical anchors
    zdovesil = sector.systems["1212"]
    assert zdovesil.name == "Zdovesil"
    assert zdovesil.allegiance == "Zh"

    tlebria = sector.systems["1618"]
    assert tlebria.name == "Tlebria"
    assert tlebria.allegiance == "Zh"

    hollis = sector.systems["2523"]
    assert hollis.name == "Hollis"
    assert hollis.allegiance == "Cs"
    assert "Naval" in hollis.bases and "Scout" in hollis.bases

    alenzar = sector.systems["3229"]
    assert alenzar.name == "Alenzar"
    assert alenzar.allegiance == "Cs"

    raschev = sector.systems["3230"]
    assert raschev.name == "Raschev"
    assert raschev.allegiance == "Cs"

    parthinia = sector.systems["3018"]
    assert parthinia.name == "Parthinia"
    assert parthinia.allegiance == "Hl"

    avalar = sector.systems["1636"]
    assert avalar.name == "Avalar"
    assert avalar.allegiance == "Av"

    # Verify all 27 Avalar Consulate systems
    av_systems = [h for h, s in sector.systems.items() if s.allegiance == "Av"]
    assert len(av_systems) == 27

    # Verify Heptarchy of Septima (7 systems at war with Avalar)
    he_systems = [h for h, s in sector.systems.items() if s.allegiance == "He"]
    assert len(he_systems) == 7
    assert "1628" in he_systems
    assert sector.systems["1628"].name == "Septima Prime"
    assert sector.systems["1628"].travel_zone == "R"

    # Verify Chatelaine of Bastet (5 uplifted Terran feline systems)
    fe_systems = [h for h, s in sector.systems.items() if s.allegiance == "Fe"]
    assert len(fe_systems) == 5
    assert "0131" in fe_systems
    assert sector.systems["0131"].name == "Bastet"

    # Verify Periannath Shires & Issugur Commonwealth (4 halfling systems)
    hl_systems = [h for h, s in sector.systems.items() if s.allegiance == "Hl"]
    assert len(hl_systems) == 4
    assert "2835" in hl_systems
    assert sector.systems["2835"].name == "The Shire"

    # Verify Tlinzha Union (4 two-headed octopod systems)
    tl_systems = [h for h, s in sector.systems.items() if s.allegiance == "Tl"]
    assert len(tl_systems) == 4
    assert "0720" in tl_systems
    assert sector.systems["0720"].name == "Tlesho"


def test_subsector_j_barren_anomaly_and_erith(foreven_data):
    sector, _ = foreven_data

    # Every Subsector J Barren Anomaly world must have population 0
    for hex_coord in SUBSECTOR_J_BARREN_ANOMALY:
        sys = sector.systems[hex_coord]
        mw = next(w for w in sys.all_worlds if w.is_mainworld)
        assert mw.uwp.population == "0"
        assert sys.travel_zone == "A"

    # Erith must be identified and have Earth-like physical parameters (Size 8, Atm 6, Hyd 7)
    assert sector.erith_hex is not None
    erith_sys = sector.systems[sector.erith_hex]
    assert erith_sys.name == "Erith"
    erith_mw = next(w for w in erith_sys.all_worlds if w.is_mainworld)
    assert erith_mw.name == "Erith"
    assert erith_mw.uwp.size == "8"
    assert erith_mw.uwp.atmosphere == "6"
    assert erith_mw.uwp.hydrographics == "7"


def test_wbh_secondary_worlds_and_exporters(foreven_data):
    sector, subsectors = foreven_data

    # Ensure systems have full WBH stars and secondary worlds
    total_worlds = sum(len(s.all_worlds) for s in sector.systems.values())
    assert total_worlds > 1500

    # Test SVG cartography and text exporters (including strict XML well-formedness)
    import xml.etree.ElementTree as ET
    svg = generate_sector_svg(subsectors, full_sector=sector)
    assert "<svg" in svg and "Avalar" in svg and "Zdovesil" in svg
    ET.fromstring(svg)

    for idx, sub in enumerate(subsectors):
        letter = chr(ord("A") + idx)
        sub_svg = generate_subsector_svg(
            sub,
            name=f"Subsector {letter}: {FOREVEN_SUBSECTORS[letter]}",
            subsector_col=idx % 4,
            subsector_row=idx // 4,
        )
        assert "<svg" in sub_svg
        ET.fromstring(sub_svg)

    sec_text = export_sector_sec_file(sector)
    assert "Zdovesil" in sec_text and "Avalar" in sec_text and "Septima Prime" in sec_text

    gaz_md = export_foreven_gazetteer_markdown(sector)
    assert "Heptarchy of Septima" in gaz_md
    assert "Chatelaine of Bastet" in gaz_md
    assert "Issugur / Periannath" in gaz_md
    assert "Erith" in gaz_md
    assert "Closest Solar Analogue Stars" in gaz_md
    assert "Closest Solar System Architectural Analogues" in gaz_md


def test_solar_and_solar_system_analogues_and_age_metallicity(foreven_data):
    sector, _ = foreven_data

    # 1. Every system and star has metallicity [Fe/H] populated
    for sys in sector.systems.values():
        assert -1.5 <= sys.metallicity_feh <= 0.5
        for star in sys.stars:
            assert star.metallicity_feh == sys.metallicity_feh

    # 2. Geological / evolutionary age habitability windows
    hadean = evaluate_planetary_age_habitability(0.3, 1.0)
    assert hadean["in_earth_age_window"] is False
    assert "Hadean" in hadean["epoch"]

    proterozoic = evaluate_planetary_age_habitability(3.8, 1.0)
    assert proterozoic["in_earth_age_window"] is False
    assert "Proterozoic" in proterozoic["epoch"]

    phanerozoic = evaluate_planetary_age_habitability(4.57, 1.0)
    assert phanerozoic["in_earth_age_window"] is True
    assert "Phanerozoic" in phanerozoic["epoch"]

    super_greenhouse = evaluate_planetary_age_habitability(5.5, 1.0)
    assert super_greenhouse["in_earth_age_window"] is False
    assert "Post-Phanerozoic" in super_greenhouse["epoch"]

    # 3. Closest Solar Analogue in Foreven (Hex 2304 Shtebr 2304: single G6 V, 4.13 Gyr, [Fe/H] = -0.11)
    assert sector.solar_analogue_hex == "2304"
    top_solar = sector.solar_analogues[0]
    assert top_solar["hex_coord"] == "2304"
    assert top_solar["spectral_type"] == "G6 V"
    assert top_solar["multiplicity"] == 1
    assert top_solar["in_earth_age_window"] is True
    assert abs(top_solar["metallicity_feh"]) <= 0.15

    # 4. Closest Solar System Architectural Analogues (inner terrestrials, 0 inner gas giants, outer gas giants)
    assert sector.solar_system_analogue_hex in ("0202", "0227")
    top_ss = sector.solar_system_analogues[0]
    assert top_ss["hex_coord"] == "0202"
    assert top_ss["primary_star"] == "F7 V"
    assert top_ss["inner_terrestrial_count"] == 6
    assert top_ss["inner_gas_giant_count"] == 0
    assert top_ss["outer_gas_giant_count"] == 2

    second_ss = sector.solar_system_analogues[1]
    assert second_ss["hex_coord"] == "0227"
    assert second_ss["primary_star"] == "G3 V"
    assert second_ss["inner_terrestrial_count"] == 2
    assert second_ss["inner_gas_giant_count"] == 0
    assert second_ss["outer_gas_giant_count"] == 3

    third_ss = sector.solar_system_analogues[2]
    assert third_ss["hex_coord"] == "3014"
    assert third_ss["primary_star"] == "F5 V"
    assert third_ss["inner_terrestrial_count"] == 5
    assert third_ss["inner_gas_giant_count"] == 0
    assert third_ss["outer_gas_giant_count"] == 1

    # 5. Age & Metallicity-coupled Earth analogues
    earth_list = find_earth_analogues(sector, top_n=5, include_age_and_metallicity=True)
    assert len(earth_list) == 5

