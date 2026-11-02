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

**On Google Colab there is nothing to install by hand.** The next cell
fetches the package into the Colab runtime, and Colab already has pandas
and ipywidgets. Just run the cells in order.

**Locally**, `requirements.txt` lives in the root of the repository, beside
this notebook: clone the repository and run `pip install -r
requirements.txt` from that directory. It includes `ipywidgets`, which the
dropdown pickers need; without it the same views are available as plain
function calls, which every cell shows.
""")

# ---------------------------------------------------------------- setup
md("""
## 1. Settings & Foreven 1105 Scenario Toggles

Out of the box, this notebook defaults to the **absolute minimum: Strict 1105 Canon**
for the **Foreven Sector** (*Iakr* in Zhodani), based on the Far Future Enterprises
(2008) *Foreven Sector Reserve* and Classic Traveller primary sources:
- **358 canonical star positions** and the **142-hex Zhodani Consulate border** (`ZhIN`, *Preqlianz of Iadr Nsobl*).
- **Only the 4 canonical FFE subsector names**: `D: Massina`, `H: Fessor`, `L: Reidain`, `P: Urnian`.
- **The 3 canonical statted worlds**: `Zdovesil (1212)`, `Alenzar (3229)` (plus secondary planet *Chamax* with STL subterrene ruins and Chamax bugs from *Double Adventure 5*), and `Raschev (3230)`.
- **The 3 Classic Traveller named unstatted systems**: `Tlebria (1618)` (*Book 7: Merchant Prince*), `Purfyr (2211)` (*JTAS #16*), and `Cocta (2415)` (*JTAS #2* citation).
- **Canonical Minor Races & Aliens**: Two *Alien Module 5* Droyne worlds (`0513` in Pieplow, `3003` in Massina) and `Parthinia (3018)` (*Alien Realms* "The Deep Metal", homeworld of the *Issugur* minor human race).
- **Canonical Corporations**: `Iadria Vlovl` (1618 Tlebria), `Priantqlovr Drafr` (1212 Zdovesil), and `InStarSpec` (3229 Alenzar).

Every deuterocanonical (*Imperial Lines #1*, *Die Weltbund*, *Mnemosyne Principality*),
*Sector Construction Guide* (SCG 2022), third-party (*Zhodani Base / Reidain*, *JBE Foreven Worlds*),
and custom *Referee's Preserve* faction (`Heptamorphs`, `Uplifted Terran Cats`, `Halfling Shires`, `Christen Erith`)
is **off by default** and individually toggleable below.

Regardless of which scenario toggles are active, **every run always identifies and ranks**:
1. **The most Earth-like worlds** (Coupled Earth Similarity Index + stellar age/metallicity).
2. **The most Solar System-like planetary architectures** (inner rocky planets, no hot Jupiters, outer gas giants, belts).
3. **The closest Solar analogue stars** (G2V benchmark).
""")

code("""
SEED               = 1105          # any integer; change for a different sector
USE_FOREVEN_1105   = True          # True: modular Foreven 1105 generator; False: generic sector
CANON_MODE         = "pin"         # "pin" | "seed" | "positions"

# Quick Preset: None (use individual toggles below), or one of:
#   "strict_1105"             (Default: FFE 2008 Reserve + Classic Traveller only)
#   "deuterocanon_1105"       (Strict 1105 + Imperial Lines #1 + 1105 Die Weltbund + Mnemosyne)
#   "scg_worked_1105"         (Strict 1105 + full Mongoose 2022 Sector Construction Guide example)
#   "community_synthesis_1105"(Deuterocanon 1105 + Zhodani Base Reidain/Kamrathi + JBE Cornathia)
#   "referee_preserve_1107"   (Full SCG + Heptamorphs, Uplifted Cats, Halfling Shires & Erith in 1107)
FOREVEN_PRESET     = None

# --- Era & Base Survey Grid ---
CURRENT_YEAR               = 1105
CANONICAL_POSITIONS_358    = True
ZHODANI_CONSULATE_BORDER   = True
# Subsector naming: "ffe_4" (Strict 1105: only D, H, L, P), "imperial_lines_16", "zhodani_base_16", "custom_16"
SUBSECTOR_NAMING_MODE      = "ffe_4"

# --- Tier 1: Strict 1105 Canon (ON by default) ---
STRICT_1105_WORLDS         = True   # Zdovesil (1212), Alenzar (3229) + Chamax, Raschev (3230)
CLASSIC_NAMED_SYSTEMS      = True   # Tlebria (1618), Purfyr (2211), Cocta (2415 citation)
INCLUDE_COCTA_2415         = False  # If True, places a 359th star at 2415 for Cocta
AM5_DROYNE_WORLDS          = True   # Alien Module 5 Droyne at 0513 & 3003
PARTHINIA_ISSUGUR          = True   # Alien Realms (1986) Parthinia (3018) Issugur minor human race
CANONICAL_CORPORATIONS     = True   # Iadria Vlovl, Priantqlovr Drafr, InStarSpec

# --- Tier 2: Deuterocanonical Layers (OFF by default) ---
IMPERIAL_LINES_ANCHORS     = False  # Hollis (2523), Avalar (1636), Gatina, Sturray, Ranther
HOLLIS_BABYLON5_MODE       = False  # Downgrades Hollis (2523) to Scout-only diplomatic station
# Rimward polity mode: "none" (Strict 1105), "weltbund_1105" (Rancke/JBE neutral Confederation),
#                      "avalar_il1" (procedural Avalar), "avalar_scg_27" (all 27 SCG Avalar worlds)
RIMWARD_POLITY_MODE        = "none"
MNEMOSYNE_PRINCIPALITY     = False  # Multi-system pocket empire ('Mn') in Subsectors M/N

# --- Tier 3: Sector Construction Guide (SCG 2022) Layers (OFF by default) ---
SCG_TLESHO_UNION           = False  # 4-system Tlinzha octopod polity (0720, 0819, 0820, 0919)
SCG_NATIVE_SOPHONTS        = False  # 7 SCG native sophont homeworlds (p.24)
SCG_ANCIENTS_RUINS         = False  # 4 SCG Ancients ruins sites (1726, 2615, 2740, 3006)
SCG_SCATTERED_SETTLEMENTS  = False  # 10 SCG scattered settlements (pp.25-26)
SCG_BARREN_ANOMALY         = False  # 14 SCG barren systems in Subsector J & C (p.8 Decision #5)
SCG_STRATEGIC_BASES        = False  # Zhodani route waypoints, Imperial Droyne Cage, TL ceilings

# --- Tier 4: Third-Party & Community Layers (OFF by default) ---
ZHODANI_BASE_REIDAIN       = False  # BeRKA/Dylan Lee/GypsyComet Reidain (2925) + Kamrathi League
JBE_FOREVEN_WORLDS         = False  # JBE Cornathian Empire in Fessor + Warpride (2136)
MONGOOSE_1E_REIDAIN_SALIENT= False  # 2008 Mongoose 1e Zhodani salient into Reidain

# --- Tier 5: Settlement Wave Modeling (SCG pp. 22-27) ---
ENABLE_SETTLEMENT_WAVES    = True
WAVE_ZHODANI_THICK         = True   # Coreward Zhodani thick wave (-5000 to -1000, Subsectors A/B/C/E/F)
WAVE_IMPERIAL_THIN         = True   # Trailing Imperial thin wave (50 to 589, Subsectors D/H/L/P)
WAVE_ZHODANI_THIN          = True   # Post-FFW II Zhodani thin wave (600 to 700, Subsectors D/E/F/G)
WAVE_RIMWARD_HUB           = False  # Radial wave from Avalar 1636 (auto-enabled if Avalar/Weltbund active)
WAVE_PSIONIC_REFUGEES      = False  # Post-800 Psionic Suppressions wave into Rimward/Frontier

# --- Tier 6: Procedural & Custom Referee's Preserve Toggles (OFF by default) ---
ALLOW_RANDOM_SOPHONTS      = False
ALLOW_PROCEDURAL_POLITIES  = False
CUSTOM_HEPTAMORPHS         = False  # Heptarchy of Septima ('He') around 1628
CUSTOM_UPLIFTED_CATS       = False  # Chatelaine of Bastet ('Fe') around 0131
CUSTOM_HALFLING_SHIRES     = False  # Periannath Shires ('Hl') around 2835 & 3018
CHRISTEN_ERITH             = False  # Rename the #1 Earth analogue to 'Erith'

# Generic non-Foreven fallback settings (used only when USE_FOREVEN_1105 = False)
SECTOR_NAME      = "Foreven"
WIDTH, HEIGHT    = 32, 40
UNIVERSE_PRESET  = None
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

Builds the `ForevenScenario` from your toggles (or preset), constructs the
canonical overlay and settlement waves, and generates all 358 systems (plus
their secondary worlds, moons, trade routes, historical settlement strata,
and Earth/Solar System analogue rankings).
""")

code("""
if USE_FOREVEN_1105:
    if FOREVEN_PRESET:
        scenario = wm.ForevenScenario.from_preset(FOREVEN_PRESET)
    else:
        scenario = wm.ForevenScenario(
            current_year=CURRENT_YEAR,
            canonical_positions_358=CANONICAL_POSITIONS_358,
            zhodani_consulate_border=ZHODANI_CONSULATE_BORDER,
            subsector_naming_mode=SUBSECTOR_NAMING_MODE,
            strict_1105_worlds=STRICT_1105_WORLDS,
            classic_named_systems=CLASSIC_NAMED_SYSTEMS,
            include_cocta_2415=INCLUDE_COCTA_2415,
            am5_droyne_worlds=AM5_DROYNE_WORLDS,
            parthinia_issugur=PARTHINIA_ISSUGUR,
            canonical_corporations=CANONICAL_CORPORATIONS,
            imperial_lines_anchors=IMPERIAL_LINES_ANCHORS,
            hollis_babylon5_mode=HOLLIS_BABYLON5_MODE,
            rimward_polity_mode=RIMWARD_POLITY_MODE,
            mnemosyne_principality=MNEMOSYNE_PRINCIPALITY,
            scg_tlesho_union=SCG_TLESHO_UNION,
            scg_native_sophonts=SCG_NATIVE_SOPHONTS,
            scg_ancients_ruins=SCG_ANCIENTS_RUINS,
            scg_scattered_settlements=SCG_SCATTERED_SETTLEMENTS,
            scg_barren_anomaly=SCG_BARREN_ANOMALY,
            scg_strategic_bases=SCG_STRATEGIC_BASES,
            zhodani_base_reidain=ZHODANI_BASE_REIDAIN,
            jbe_foreven_worlds=JBE_FOREVEN_WORLDS,
            mongoose_1e_reidain_salient=MONGOOSE_1E_REIDAIN_SALIENT,
            enable_settlement_waves=ENABLE_SETTLEMENT_WAVES,
            wave_zhodani_thick=WAVE_ZHODANI_THICK,
            wave_imperial_thin=WAVE_IMPERIAL_THIN,
            wave_zhodani_thin=WAVE_ZHODANI_THIN,
            wave_rimward_hub=WAVE_RIMWARD_HUB,
            wave_psionic_refugees=WAVE_PSIONIC_REFUGEES,
            allow_random_native_sophonts=ALLOW_RANDOM_SOPHONTS,
            allow_procedural_polities=ALLOW_PROCEDURAL_POLITIES,
            custom_heptamorphs=CUSTOM_HEPTAMORPHS,
            custom_uplifted_cats=CUSTOM_UPLIFTED_CATS,
            custom_halfling_shires=CUSTOM_HALFLING_SHIRES,
            christen_erith=CHRISTEN_ERITH,
        )
    sector = wm.generate_foreven_1105(seed=SEED, scenario=scenario, canon_mode=CANON_MODE)
    SECTOR_NAME = sector.name
    print("Active Foreven Scenario Layers:")
    for layer in scenario.active_layers():
        print(f"  • {layer}")
    print()
else:
    random.seed(SEED)
    universe = (wm.create_universe(SECTOR_NAME, preset=UNIVERSE_PRESET)
                if UNIVERSE_PRESET else None)
    sector = wm.generate_full_sector(
        SECTOR_NAME, width=WIDTH, height=HEIGHT,
        universe=universe, canon_mode=CANON_MODE)

inhabited = sum(1 for s in sector.systems.values()
                for b in s.all_bodies
                if getattr(b, 'is_secondary_world', False))

print(f"{len(sector.systems)} systems, {len(sector.polities)} polities, "
      f"{len(sector.native_sophonts)} sophont worlds, "
      f"{len(sector.settlement_waves)} settlement waves")
print(f"{inhabited} inhabited secondary worlds beyond the mainworlds")
for p in sector.polities:
    print(f"  {p.allegiance_code:6s} {p.name:32s} "
          f"{len(p.controlled_systems):4d} worlds")
if sector.corporations:
    print("\\nCanonical Corporations:")
    for c in sector.corporations:
        print(f"  • {c['name']} (HQ: {c['hq_hex']} {c['hq_world']}, {c['allegiance']}) — {c['role']}")
print()
display(Markdown(wm.describe_sector_analogues(sector)))
""")

# ------------------------------------------------- settlement waves section
md("""
## 2b. Settlement Waves & Sector History (SCG pp. 22–27)

In the *Sector Construction Guide* (pp. 22–27), a sector's demographic density and
historical depth are shaped by **Settlement Waves** (*thick* vs. *thin* waves) propagating
from sector edges or local hubs at a characteristic speed (parsecs per century):
- **Indigenous / Transplanted Sophont Worlds** (`sector.native_sophonts`): Carry a **+6 DM** to Population (SCG p. 22).
- **Thick Settlement Waves** (e.g. the *Zhodani Coreward Heartland Wave* from Ziafrplians, or the *Avalar/Weltbund Radial Wave*): Start at **-3 DM** on the newly settled frontier and gain **+1 DM per century** of local age, maturing at **+1 DM**.
- **Thin Settlement Waves** (e.g. the *Imperial Spinward Main Thin Wave* across Massina, Fessor, Reidain, and Urnian, or the *Zhodani Post-FFW II Thin Wave*): Start at **-5 DM** and gain **+1 DM per century**, maturing at **+0 DM**.
- **Unreached Shadow Zones** (e.g. Spinward Subsectors I, J, M when rimward/custom waves are off): Carry an unsettled frontier penalty (**-3 DM**).
- **Historical Stratigraphy**: When multiple waves cross the same hex at different epochs (for example, Subsector D *Massina*, settled by the pre-war Imperial Thin Wave and conquered by the Zhodani in the First Frontier War), both waves are recorded in `system.settlement_strata`.
""")

code("""
waves_df = wm.create_settlement_waves_dataframe(sector)
display(Markdown("### Active Settlement Waves"))
display(waves_df)

strata_df = wm.create_settlement_strata_dataframe(sector)
display(Markdown("### Multi-Wave Historical Stratigraphy (Systems Reached by 2+ Waves)"))
multi_wave_df = strata_df[strata_df["Wave Count"] >= 2]
print(f"{len(multi_wave_df)} systems have multi-epoch settlement strata; "
      f"{len(strata_df[strata_df['Wave Count'] == 0])} systems lie in unreached shadow space.")
display(multi_wave_df.head(15))
""")

code("""
# Color-coded Settlement Wave & Population DM Map
display(SVG(wm.generate_settlement_wave_svg(sector)))
""")

# ------------------------------------------------ analogues section
md("""
## 2c. Most Earth-like Worlds, Solar System Analogues & Solar Analogue Stars

Every run automatically evaluates all generated star systems and planetary bodies
against three astrobiological and architectural benchmarks:
1. **Age & Metallicity-Coupled Earth Similarity Index (`sector.earth_analogues`)**: Combines physical ESI (radius, density, escape velocity, surface temperature, pressure, hydrographics, breathable atmosphere) with host star spectral class, orbital placement, stellar metallicity `[Fe/H]`, and geological age (`3.5–5.5 Gyr` sweet spot).
2. **Solar System Architectural Analogues (`sector.solar_system_analogues`)**: Scores systems for a single Solar-like primary (`G0V–G5V` or `F8V–K2V`), inner rocky terrestrials inside the snow line, **zero** inner gas giants (no Hot Jupiters disrupting terrestrial orbits), outer gas giants beyond the snow line, and planetoid belts.
3. **Solar Analogue Stars (`sector.solar_analogues`)**: Ranks primary stars against Sol (`G2 V`, $1.00\\,M_\\odot$, $1.00\\,L_\\odot$, $5778\\,\\text{K}$, $4.6\\,\\text{Gyr}$, `[Fe/H] = 0.00`).
""")

code("""
analogues = wm.create_analogues_dataframes(sector)

display(Markdown(f"### Top 10 Most Earth-like Worlds (Top Match: Hex `{sector.erith_hex}`)"))
display(analogues["earth_analogues"])

display(Markdown(f"### Top 10 Solar System Architectural Analogues (Top Match: Hex `{sector.solar_system_analogue_hex}`)"))
display(analogues["solar_system_analogues"])

display(Markdown(f"### Top 10 Solar Analogue Primary Stars (Top Match: Hex `{sector.solar_analogue_hex}`)"))
display(analogues["solar_analogues"])
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
    if getattr(system, "settlement_strata", None):
        out.append("")
        out.append(f"## Settlement Wave Stratigraphy (Pop DM `{system.population_dm:+d}`)")
        for st in system.settlement_strata:
            out.append(
                f"- **{st['wave_name']}** ({st['epoch_label']}): arrived yr `{st['arrival_year']}`, "
                f"local age `{st['local_age_centuries']}c`, wave DM `{st['wave_dm']:+d}` — "
                f"*{st['culture_sphere']}*"
            )
    if getattr(system, "corporations", None):
        out.append(f"- **Canonical Corporations**: {', '.join(system.corporations)}")
    if getattr(system, "historical_notes", None):
        for hnote in system.historical_notes:
            out.append(f"- **Historical Note**: {hnote}")
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
### Inspecting the Top Earth-like Candidate (or Christening Erith)

By default (`CHRISTEN_ERITH = False` in Strict 1105 mode), the top candidate is
inspected **without mutating** its generated UWP or renaming it. Set
`CHRISTEN_ERITH = True` in Section 1 to call `wm.make_erith(sector)`, which
imposes the exact Erith profile, rebuilds its balkanised nations, and records
the freehold proprietor.
""")

code("""
if CHRISTEN_ERITH:
    erith = wm.make_erith(sector, culture_family="terrestrial")
else:
    erith = candidates[0] if candidates else None

if erith is None:
    print("No world in this sector passes the Erith filters. "
          "Try another seed.")
else:
    w = erith.body
    mode_lbl = "Christened Erith" if CHRISTEN_ERITH else "Top Earth-like Candidate (Unmutated)"
    print(f"{mode_lbl} at {erith.hex} ({w.name}): {w.uwp}  ({erith.score}% match)")
    print(f"  star        {erith.star.spectral_type}, "
          f"habitable zone at Orbit# {erith.star.hzco:.2f}")
    print(f"  temperature {w.mean_temperature} K, "
          f"habitability {w.habitability_rating}")
    print(f"  a moon      {getattr(w, 'parent_body', None) is not None}")
    if getattr(w, 'proprietor', None):
        print(f"  proprietor  {w.proprietor['owner']}")
    print()
    if getattr(w, 'nations', None):
        print(wm.describe_nations(w))
""")

code("""
# Erith's surface, with its terrain
if erith is not None:
    display(SVG(wm.render_world_map_svg(erith.body)))
""")

md("""
### Erith as a globe

The hex map above is the Referee's working surface. The same world can also
be modelled as a sphere: terrain generated as noise on the unit sphere and
driven by Erith's own characteristics, then rendered both as a foldable
polyhedral net and as photorealistic views from orbit.

Both nets really fold. Every face is a true gnomonic projection laid beside
the faces that adjoin it on the sphere, so terrain runs continuously across
each fold line. The icosahedral net is the *World Builder's Handbook*
standard (p.135); the dodecahedral one distorts less per face.

This cell takes a minute or so at full resolution. Drop `texture_size` and
`size` for a faster preview.
""")

code("""
# One terrain model, three views of it
from IPython.display import Image

if erith is not None:
    surface = wm.generate_planet_surface(erith.body, width=2048, height=1024)

    display(SVG(wm.render_dodecahedral_net(surface, name=erith.body.name)))
    display(SVG(wm.render_icosahedral_net_svg(surface, name=erith.body.name)))

    for longitude in (-40, 60):
        view = wm.render_orbital_view(
            surface, size=760, sub_observer=(16, longitude),
            sun_direction=(12, longitude + 38),
            population=wm.Utils.from_eHex(erith.body.uwp.population))
        display(Image(data=wm.png_bytes(view)))
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
