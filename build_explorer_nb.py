"""Builds Traveller_Sector_Explorer.ipynb.

Kept as a script so the notebook can be regenerated from source rather than
hand-edited as JSON.
"""
import json

import colab_cells

cells = []


def md(text):
    cells.append({"cell_type": "markdown", "id": f"cell-{len(cells):02d}",
                  "metadata": {},
                  "source": text.strip("\n").splitlines(keepends=True)})


def code(text):
    cells.append({"cell_type": "code", "id": f"cell-{len(cells):02d}",
                  "execution_count": None,
                  "metadata": {}, "outputs": [],
                  "source": text.strip("\n").splitlines(keepends=True)})


md("""
# Traveller Sector Explorer

Generates a sector and lets you look round it: the maps, every system with
its secondary worlds, the candidates for Erith, and the places worth a
Referee's attention.

Run the cells in order. Everything after the generation cell reads the
sector that cell built, so you can re-run any of them freely.

**Requirements**: `pip install -r requirements.txt`. For the dropdown
pickers also `pip install ipywidgets` — without it the same views are
available as plain function calls, which every cell shows. On Google Colab
nothing needs installing by hand: the next cell does it.
""")

# ---------------------------------------------------------------- setup
md("""
## 1. Settings

Change these and re-run from here. The seed makes a sector reproducible:
the same seed always gives the same sector.
""")

code("""
SEED          = 1105          # any integer; change for a different sector
SECTOR_NAME   = "Foreven Reach"
WIDTH, HEIGHT = 32, 40        # a full sector; try 8, 10 for one subsector

# Canon: None, or a sector name published on travellermap.com such as
# "Foreven". Canonical star positions, borders and named worlds are then
# honoured and everything else generated around them.
CANON_SECTOR  = None
CANON_MODE    = "pin"         # "pin" | "seed" | "positions"

# Optional: a universe preset shapes density, technology and sophonts.
# One of None, "charted_space", "frontier", "pocket_empires",
# "fallen_empire", "deep_rift".
UNIVERSE_PRESET = None
""")

code("""
import random
import worldmaker as wm
from IPython.display import SVG, Markdown, display

try:
    import ipywidgets as widgets
    HAVE_WIDGETS = True
except ImportError:
    HAVE_WIDGETS = False
    print("ipywidgets not installed - the pickers fall back to function "
          "calls. pip install ipywidgets to enable them.")

print("worldmaker ready")
""")

# ------------------------------------------------------------ generation
md("""
## 2. Generate the sector

A full 32x40 sector is around 600 systems and takes a few seconds. Each
system is generated in full — stars, orbits, every world's physical and
social characteristics, secondary populations, and the nations of any
balkanised world.
""")

code("""
random.seed(SEED)

canon = None
if CANON_SECTOR:
    canon = wm.fetch_canonical_sector(CANON_SECTOR)
    if CANON_SECTOR.lower().startswith("foreven"):
        canon = wm.merge_canon(canon, wm.scg_foreven(), name=CANON_SECTOR)
    print(canon.summary())
    print()

universe = (wm.create_universe(SECTOR_NAME, preset=UNIVERSE_PRESET)
            if UNIVERSE_PRESET else None)

sector = wm.generate_full_sector(
    SECTOR_NAME, width=WIDTH, height=HEIGHT,
    universe=universe, canon=canon, canon_mode=CANON_MODE)

inhabited = sum(1 for s in sector.systems.values()
                for b in s.all_bodies
                if getattr(b, 'is_secondary_world', False))

print(f"{len(sector.systems)} systems, {len(sector.polities)} polities, "
      f"{len(sector.native_sophonts)} sophont homeworlds")
print(f"{inhabited} inhabited secondary worlds beyond the mainworlds")
for p in sector.polities:
    print(f"  {p.allegiance_code:6s} {p.name:32s} "
          f"{len(p.controlled_systems):4d} worlds")
""")

# ------------------------------------------------------------- the maps
md("""
## 3. The sector map

Classic Traveller idiom: starport letters, world discs, base glyphs,
travel-zone rings, dashed polity borders and each polity's own courier
network.
""")

code("""
display(SVG(wm.generate_sector_svg(sector)))
""")

md("""
## 4. Subsector maps

Pick a subsector A–P. Without ipywidgets, call `show_subsector("F")`.
""")

code("""
def show_subsector(letter="A"):
    \"\"\"Renders one subsector at Supplement-page scale.\"\"\"
    letter = letter.upper()
    index = ord(letter) - ord('A')
    if not 0 <= index < 16:
        print("Subsectors are lettered A to P.")
        return
    col = (index % 4) * 8 + 1
    row = (index // 4) * 10 + 1
    name = sector.subsector_names.get(letter, f"Subsector {letter}")
    count = sum(1 for h in sector.systems
                if col <= int(h[:2]) < col + 8 and row <= int(h[2:]) < row + 10)
    display(Markdown(f"**Subsector {letter}: {name}** — {count} systems"))
    display(SVG(wm.generate_subsector_svg(
        sector, name, origin_col=col, origin_row=row)))


if HAVE_WIDGETS and WIDTH == 32:
    widgets.interact(show_subsector,
                     letter=widgets.Dropdown(
                         options=[chr(ord('A') + i) for i in range(16)],
                         value='A', description='Subsector'))
else:
    show_subsector("A")
""")

# ----------------------------------------------------------- the table
md("""
## 5. Every system at a glance

One row per system. `Inhabited` counts the mainworld plus any secondary
worlds with populations of their own — a figure the UWP never shows.

The result is an ordinary pandas DataFrame, so sort and filter it however
you like: `df.sort_values("Pop", ascending=False).head(20)`, or
`df[df["Zone"] == "R"]` for the interdicted systems.
""")

code("""
df = wm.create_sector_dataframe(sector)
print(f"{len(df)} systems")
df.head(25)
""")

code("""
# A few useful views
display(Markdown("**Highest population**"))
display(df.sort_values("Pop", ascending=False).head(8))

display(Markdown("**Systems with inhabited secondary worlds**"))
display(df[df["Inhabited"] > 1].sort_values("Inhabited", ascending=False).head(8))

display(Markdown("**Interdicted and restricted systems**"))
display(df[df["Zone"] != ""][["Hex", "Name", "UWP", "Zone", "Allegiance"]].head(8))
""")

# -------------------------------------------------------- system detail
md("""
## 6. One system in full

Everything the generator knows about a system: its stars, its mainworld's
social profile, the nations of a balkanised world, and every secondary
world with its own population.

Pick a hex from the dropdown, or call `show_system("1515")`.
""")

code("""
def show_system(hex_coord):
    \"\"\"The full profile of one system, including its secondary worlds.\"\"\"
    system = sector.systems.get(hex_coord)
    if system is None:
        print(f"No system at {hex_coord}.")
        return
    mw = system.mainworld
    out = [f"# {mw.name or system.name}  ({hex_coord})", ""]

    out.append(f"**UWP** `{mw.uwp}`  &nbsp; **Trade codes** "
               f"{', '.join(mw.trade_codes) or '-'}")
    zone = {'A': 'Amber', 'R': 'Red'}.get(system.travel_zone, 'Green')
    out.append(f"**Allegiance** {system.allegiance} &nbsp; **Zone** {zone} "
               f"&nbsp; **Bases** {', '.join(system.bases) or 'none'}")
    out.append(f"**System age** {system.age_gyr} Gyr &nbsp; "
               f"**Gas giants** {system.gas_giant_count} &nbsp; "
               f"**Belts** {system.planetoid_belt_count}")
    out.append("")

    out.append("## Stars")
    for star in system.stars:
        if star.is_composite:
            continue
        out.append(f"- **{star.designation}** {star.spectral_type} — "
                   f"mass {star.mass:.3f}, luminosity {star.luminosity:.4f}, "
                   f"habitable zone at Orbit# {star.hzco:.2f}")
    out.append("")

    out.append("## Mainworld")
    out.append(f"- Physical: size {mw.size_code}, "
               f"{int(mw.diameter_km or 0):,} km, gravity {mw.gravity}g, "
               f"{mw.mean_temperature}K ({mw.climate_zone})")
    out.append(f"- Atmosphere: {mw.atmosphere_name} "
               f"{mw.atmos_pressure_bar} bar, ppO2 {mw.partial_pressure_oxygen}")
    out.append(f"- Habitability {mw.habitability_rating}, "
               f"resources {mw.resource_rating}, life `{mw.native_lifeform_profile}`")
    if mw.total_population:
        out.append(f"- Population {mw.total_population:,} "
                   f"(profile {mw.population_profile}), "
                   f"{mw.urbanisation_pct}% urban")
        out.append(f"- Government: {mw.government_type} "
                   f"({mw.government_profile}); law {mw.law_profile}")
        out.append(f"- Technology {mw.technology_profile}; "
                   f"economics {mw.economic_extension}, WTN {mw.wtn}")
    if mw.major_cities:
        out.append("- Major cities: " + ", ".join(
            f"{c['name']} ({c['population']:,})" for c in mw.major_cities[:6]))
    for note in mw.notes[:6]:
        out.append(f"- *{note}*")
    out.append("")

    nations = getattr(mw, 'nations', None) or []
    if nations:
        out.append(f"## Nations ({getattr(mw, 'nation_count', len(nations))} "
                   f"sovereign states, {len(nations)} detailed)")
        for n in nations:
            seat = " — holds the starport" if n.holds_starport else ""
            culture = f", {n.culture_template}" if n.culture_template else ""
            out.append(f"- **{n.name}**{seat}: {n.government_type}, "
                       f"law {wm.Utils.eHex(n.law_level)}, "
                       f"TL {wm.Utils.eHex(n.tech_level)}, "
                       f"{n.population:,} people, {n.land_share}% of the "
                       f"land{culture}")
        out.append("")

    secondaries = [b for b in system.all_bodies
                   if getattr(b, 'is_secondary_world', False)]
    if secondaries:
        out.append("## Secondary worlds")
        for b in secondaries:
            kind = "colony" if b.affiliated else "independent"
            out.append(f"- **{b.designation}** `{b.uwp}` — {kind}, "
                       f"{b.total_population:,} people, "
                       f"{b.government_type}, TL {b.uwp.tech_level}")
        out.append("")
    else:
        out.append("*No inhabited secondary worlds.*")
        out.append("")

    others = [b for b in system.all_worlds
              if not b.is_mainworld and not getattr(b, 'is_secondary_world', False)]
    if others:
        out.append("## Other bodies")
        for b in others:
            moons = len([s for s in b.satellites if not s.is_ring])
            rings = " + rings" if any(s.is_ring for s in b.satellites) else ""
            moon_note = f", {moons} significant moons{rings}" if moons or rings else ""
            out.append(f"- {b.designation} — {b.body_type}, size {b.size_code}, "
                       f"Orbit# {b.orbit_num}{moon_note}")

    score, reasons = wm.notability(mw, system, sector, hex_coord)
    if reasons:
        out.append("")
        out.append("## Why this system is notable")
        for reason in reasons:
            out.append(f"- {reason}")

    display(Markdown("\\n".join(out)))


hexes = sorted(sector.systems)
if HAVE_WIDGETS:
    widgets.interact(show_system,
                     hex_coord=widgets.Dropdown(options=hexes,
                                                value=hexes[0],
                                                description='System'))
else:
    show_system(hexes[0])
""")

# ------------------------------------------------------ Erith candidates
md("""
## 7. Candidates for Erith

A very Earth-like world: Terra's own size, atmosphere and hydrographics,
balkanised, pre-industrial, in the habitable zone of an F, G or K star and
outside Zhodani space.

Scoring weights the physical characteristics hardest — a world of the right
size, air and water with the wrong Law Level is a far better answer than the
reverse — and Law and Tech are allowed a notch either way. Secondary worlds
are searched alongside mainworlds, so the answer may well be a moon.
""")

code("""
candidates = wm.find_worlds(sector, wm.ERITH, limit=12)
print(wm.describe_matches(candidates, wm.ERITH))
""")

code("""
import pandas as pd

rows = []
for m in candidates:
    b = m.body
    rows.append({
        "Hex": m.hex, "Name": m.name, "UWP": m.uwp,
        "Score %": m.score,
        "Role": "mainworld" if m.is_mainworld else "secondary",
        "Star": m.star.spectral_type,
        "Temp K": b.mean_temperature,
        "Hab": b.habitability_rating,
        "Allegiance": m.system.allegiance,
        "Moon": getattr(b, 'parent_body', None) is not None,
    })
pd.DataFrame(rows)
""")

md("""
### Making one of them Erith

An exact Erith is rare by chance, because generation ties Tech Level to
starport and population. `make_erith` takes the closest candidate, makes it
match exactly, rebuilds its nations, gives them a culture palette and
records the family holding the freehold.

On a balkanised world the freehold does not abolish the states: title and
ground disagree, which is the point.
""")

code("""
erith = wm.make_erith(sector, culture_family="terrestrial")

if erith is None:
    print("No world in this sector passes the Erith filters. "
          "Try another seed.")
else:
    w = erith.body
    print(f"Erith is at {erith.hex}: {w.uwp}  ({erith.score}% match)")
    print(f"  star        {erith.star.spectral_type}, "
          f"habitable zone at Orbit# {erith.star.hzco:.2f}")
    print(f"  temperature {w.mean_temperature} K, "
          f"habitability {w.habitability_rating}")
    print(f"  a moon      {getattr(w, 'parent_body', None) is not None}")
    print(f"  proprietor  {w.proprietor['owner']}")
    print()
    print(wm.describe_nations(w))
""")

code("""
# Erith's surface, with its terrain
if erith is not None:
    display(SVG(wm.render_world_map_svg(erith.body)))
""")

# ------------------------------------------------------- notable worlds
md("""
## 8. The worlds worth looking at

Several hundred systems and several thousand bodies, almost all of it
unremarkable rock. These cells surface the places that would change what
happens at the table, and say why each was flagged.
""")

code("""
print(wm.describe_notable(
    wm.find_notable(sector, limit=12, kind='mainworld'),
    "Most notable mainworlds"))
""")

code("""
print(wm.describe_notable(
    wm.find_notable(sector, limit=12, kind='secondary'),
    "Most notable secondary worlds"))
""")

md("""
### Exotic stellar systems

Dead stars are genuinely rare as primaries — about one system in a thousand
— so a sector may hold none at all. What surfaces here is usually giants,
subdwarfs and multiple-star systems.

The *World Builder's Handbook* is explicit about where the dwarfs actually
are: they "occupy 'empty' hexes" and are absent from commercial charts. The
next cell surveys that deep space.
""")

code("""
print(wm.describe_notable(wm.find_exotic_systems(sector, limit=12),
                          "Most exotic stellar systems"))
""")

code("""
# Survey the empty hexes for the objects that never reach a commercial
# chart: white and brown dwarfs, the odd neutron star, and rogue planets.
# On a full sector this takes a little while.
SURVEY_HEXES = 200      # raise for a fuller survey, or None for all of them

import itertools

empty = [f"{c:02d}{r:02d}"
         for c in range(1, sector.width + 1)
         for r in range(1, sector.height + 1)
         if f"{c:02d}{r:02d}" not in sector.systems]
if SURVEY_HEXES:
    empty = empty[:SURVEY_HEXES]

found = []
for hex_coord in empty:
    survey = wm.generate_empty_hex(name=f"Deep Space {hex_coord}")
    if survey.star_system is not None:
        survey.hex_coord = hex_coord
        sector.deep_space[hex_coord] = survey
        found.append((hex_coord, survey))

print(f"surveyed {len(empty)} empty hexes; "
      f"{len(found)} hold a star-like object\\n")
for hex_coord, survey in found[:15]:
    star = survey.star_system.primary_star
    rogues = len(survey.rogue_worlds)
    print(f"  {hex_coord}  {star.spectral_type:14s} "
          f"mass {star.mass:6.3f}  "
          f"{len(survey.star_system.all_worlds):2d} worlds, "
          f"{rogues} rogue bodies")
""")

# -------------------------------------------------------------- exports
md("""
## 9. Write it all out

The sector data in Traveller5 Second Survey format (which travellermap.com
reads), plus the maps.
""")

code("""
from pathlib import Path

out = Path("output") / SECTOR_NAME.replace(" ", "_")
out.mkdir(parents=True, exist_ok=True)

(out / "sector.sec").write_text(wm.export_sector_sec_file(sector))
(out / "sector.tab").write_text(wm.export_sector_t5_tab(sector))
(out / "sector_map.svg").write_text(wm.generate_sector_svg(sector))
wm.create_sector_dataframe(sector).to_csv(out / "systems.csv", index=False)

for i in range(16):
    letter = chr(ord('A') + i)
    col, row = (i % 4) * 8 + 1, (i // 4) * 10 + 1
    if col > sector.width or row > sector.height:
        continue
    name = sector.subsector_names.get(letter, f"Subsector {letter}")
    (out / f"subsector_{letter}.svg").write_text(
        wm.generate_subsector_svg(sector, name, origin_col=col, origin_row=row))

if erith is not None:
    (out / "erith_map.svg").write_text(wm.render_world_map_svg(erith.body))
    (out / "erith.md").write_text(wm.describe_nations(erith.body))

print("written to", out.resolve())
for path in sorted(out.iterdir()):
    print("  ", path.name)
""")

notebook = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python",
                       "name": "python3"},
        "language_info": {"name": "python", "version": "3.11"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

PATH = "Traveller_Sector_Explorer.ipynb"

with open(PATH, "w") as handle:
    json.dump(notebook, handle, indent=1)

# The badge, the Colab bootstrap and the download cell, so the rebuilt
# notebook still runs on Colab.
total = colab_cells.ensure(PATH, download=colab_cells.EXPLORER_DOWNLOAD)

print(f"wrote {PATH} with {total} cells")
