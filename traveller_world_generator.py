#!/usr/bin/env python
# coding: utf-8

"""
Traveller World Generator — Foreven Sector (Iakr, Year 1107) Edition
Procedurally and deterministically generates the complete 358-system Foreven Sector
according to the canonical FFE Foreven Sector Reserve, the Mongoose Traveller
Sector Construction Guide (SCG), and the World Builder's Handbook (WBH), complete
with secondary worlds, moons, five-epoch macro-history, and Referee's Preserve lore.
"""

import os
from worldmaker import (
    generate_foreven_sector,
    generate_sector_svg,
    generate_subsector_svg,
    export_system_markdown,
    export_sector_sec_file,
    export_foreven_gazetteer_markdown,
    FOREVEN_SUBSECTORS,
)

if __name__ == '__main__':
    print("Generating canonical + Referee's Preserve Foreven Sector (Year 1107, 16 subsectors, 358 systems)...")
    foreven_sector, subsectors = generate_foreven_sector(seed=1107)

    # 1. Render combined 32x40 sector vector map
    svg_data = generate_sector_svg(subsectors, full_sector=foreven_sector)
    with open("sector_map.svg", "w") as f:
        f.write(svg_data)
    print(f"Full Foreven sector map generated as sector_map.svg ({len(foreven_sector.systems)} systems)")

    # 2. Generate individual vintage-styled subsector maps (A to P)
    os.makedirs("subsectors", exist_ok=True)
    letters = [chr(ord('A') + i) for i in range(16)]
    for idx, subsector in enumerate(subsectors):
        letter = letters[idx]
        sub_col = idx % 4
        sub_row = idx // 4
        sub_name = f"Subsector {letter}: {FOREVEN_SUBSECTORS[letter]}"
        subsector_svg = generate_subsector_svg(
            subsector,
            name=sub_name,
            subsector_col=sub_col,
            subsector_row=sub_row,
        )
        file_path = os.path.join("subsectors", f"subsector_{letter}.svg")
        with open(file_path, "w") as f:
            f.write(subsector_svg)
    print("Classic 1981 Traveller style subsector maps generated inside 'subsectors/' (subsector_A.svg to subsector_P.svg)")

    # 3. Export standard .sec file and comprehensive Foreven Sector Gazetteer
    sec_content = export_sector_sec_file(foreven_sector)
    with open("foreven_sector.sec", "w") as f:
        f.write(sec_content)
    print("Exported standard Traveller sector data to foreven_sector.sec")

    gazetteer_md = export_foreven_gazetteer_markdown(foreven_sector)
    with open("foreven_gazetteer.md", "w") as f:
        f.write(gazetteer_md)
    print("Exported Foreven Sector Gazetteer & Macro-History to foreven_gazetteer.md")

    # 4. Export full WBH system dossier for Erith (plus Solar/Solar System analogues, Avalar, and Septima Prime)
    erith_hex = foreven_sector.erith_hex
    erith_system = foreven_sector.systems[erith_hex]
    print(f"\nMost Earth-like planet christened 'Erith' at Hex {erith_hex} (Subsector {erith_system.subsector_code}: {erith_system.subsector_name})")

    if foreven_sector.solar_analogues:
        top_sol = foreven_sector.solar_analogues[0]
        print(
            f"Closest Solar Analogue star at Hex {top_sol['hex_coord']} ({top_sol['name']}): "
            f"{top_sol['spectral_type']} ({top_sol['mass']} M_sun, {top_sol['luminosity']} L_sun, {top_sol['temp_k']} K), "
            f"Age {top_sol['age_gyr']} Gyr, [Fe/H] = {top_sol['metallicity_feh']:+.2f} dex"
        )
    if foreven_sector.solar_system_analogues:
        top_ss = foreven_sector.solar_system_analogues[0]
        print(
            f"Closest Solar System architectural analogue at Hex {top_ss['hex_coord']} ({top_ss['name']}): "
            f"{top_ss['primary_star']} primary, {top_ss['inner_terrestrial_count']} inner terrestrials, "
            f"{top_ss['outer_gas_giant_count']} outer gas giants, {top_ss['planetoid_belt_count']} belts"
        )

    dossier_parts = [
        export_system_markdown(erith_system),
        "\n---\n",
        export_system_markdown(foreven_sector.systems["1636"]),
        "\n---\n",
        export_system_markdown(foreven_sector.systems["1628"]),
        "\n---\n",
        export_system_markdown(foreven_sector.systems["0131"]),
        "\n---\n",
        export_system_markdown(foreven_sector.systems["2835"]),
    ]
    with open("sample_system_dossier.md", "w") as f:
        f.write("\n".join(dossier_parts))
    print("Exported WBH multi-world dossiers (Erith, Avalar, Septima Prime, Bastet, The Shire) to sample_system_dossier.md")
