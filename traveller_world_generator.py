#!/usr/bin/env python
# coding: utf-8

"""
Traveller World Generator (Refactored Package Wrapper)
Procedurally generates detailed planetary systems and sectors according to rules set forth in 
the Traveller World Builder's Handbook (WBH) and the Sector Construction Guide (SCG).
Delegates core logic to the modular 'worldmaker' package.
"""

import os
from worldmaker import (
    generate_sector,
    generate_sector_svg,
    generate_subsector_svg,
    generate_full_system,
    create_system_dataframe,
    export_system_markdown,
    export_sector_sec_file
)

if __name__ == '__main__':
    # --- EXECUTE SECTOR GENERATION ---
    print("Generating sector map (16 subsectors)...")
    subsectors = []
    for i in range(16):
        # Generate each subsector procedurally using the WBH/SCG hybrid engine
        subsectors.append(generate_sector())
        
    # Render combined sector vector map using correct flat-topped tiled coordinates
    svg_data = generate_sector_svg(subsectors)
    with open("sector_map.svg", "w") as f:
        f.write(svg_data)
    print("Full non-overlapping sector map generated as sector_map.svg")

    # Generate individual vintage-styled subsector maps (A to P)
    os.makedirs("subsectors", exist_ok=True)
    letters = [chr(ord('A') + i) for i in range(16)]
    for idx, subsector in enumerate(subsectors):
        letter = letters[idx]
        name = f"Subsector {letter}"
        subsector_svg = generate_subsector_svg(subsector, name=name)
        file_path = os.path.join("subsectors", f"subsector_{letter}.svg")
        with open(file_path, "w") as f:
            f.write(subsector_svg)
    print("Classic 1981 Traveller style subsector maps generated inside 'subsectors/' folder (subsector_A.svg to subsector_P.svg)")

    # Generate and print a sample detailed dossier for the first system in subsector 1
    sample_hex = list(subsectors[0].systems.keys())[0]
    sample_system = subsectors[0].systems[sample_hex]
    print(f"\nSuccessfully generated sample system: {sample_system.name} at Hex {sample_hex}")
    
    # Save a detailed text dossier of this system
    dossier_content = export_system_markdown(sample_system)
    with open("sample_system_dossier.md", "w") as f:
        f.write(dossier_content)
    print("Sample system WBH dossier exported to sample_system_dossier.md")
