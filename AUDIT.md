# Functionality Audit: World Builder's Handbook & Sector Construction Guide

**Scope:** the `worldmaker/` package, audited against the two reference books in
`documents/`: Mongoose Traveller 2e *World Builder's Handbook* (WBH, 258 pp.)
and *Sector Construction Guide* (SCG, 66 pp.).
**Method:** full source review, extraction of both books' contents, index and
checklist pages, and a 56-test pytest suite (`tests/`) combining
internal-invariant checks with conformance checks against the books' procedures
and dice distributions.

This document was first written as a gap analysis (11 of 29 tests passing) and
has since been updated as the gaps were closed. §5 lists what is still missing.

## Verdict

**Substantially implemented, and the test suite is now fully green: 56 passed,
0 failed.** (At the first audit it was 11 passed / 18 failed.)

The package now implements the WBH expanded method end to end — stars including
the Special/Unusual results, orbit availability by the book's exclusion rules,
world placement, physical detailing, the expanded atmosphere system, moon orbits,
habitability-driven mainworld selection, the economic extension, and detailed
government and law profiles — plus the SCG sector layer with travel zones, Xboat
routes and settlement waves, and classic 1981-style map rendering.

What remains genuinely unimplemented is listed in §6. It is real but narrower
than before: mainly world mapping (icosahedral surface maps), the full
high/low-temperature and seismology chains, planetoid belt internal composition,
population/city detail, military branches, and the Special Circumstances
chapter's system types beyond basic support for exotic primaries.

Two caveats about what "all tests pass" means. First, the suite tests
conformance to the procedures and their invariants — value ranges, dice
distributions, derived-quantity consistency — not every table entry
transcribed digit for digit. Second, several WBH tables are approximated
where the book leaves latitude or where a sub-table would have added little;
those approximations are flagged in the code comments and in §6.

---

## 1. Coverage against the World Builder's Handbook

Legend: ✅ implemented · ⚠️ implemented with documented approximation · ❌ absent

### Stars (pp. 14–35)

| Procedure | Status |
|---|---|
| Primary star type/subtype tables (pp. 15–17) | ✅ |
| Special/Unusual results: giants (Ia–III), subgiants (IV), subdwarfs (VI), white/brown dwarfs, neutron stars, pulsars, black holes, protostars, nebulae, clusters | ✅ Now reachable. ~2.3% of primaries are non-Class-V, matching the 1-in-36 Special rate. Exotic objects get representative mass/diameter/temperature/MAO from `_EXOTIC_PROPERTIES` rather than the full Special Circumstances sub-tables (⚠️) |
| Mass/temperature/diameter interpolation (pp. 17–19) | ✅ Now falls back to the nearest tabulated type where classes IV/VI omit part of the range |
| Luminosity formula (p. 21) | ✅ |
| System age (pp. 20–22) | ⚠️ No post-stellar age adjustment |
| Multiple star presence + companion DMs (p. 23) | ✅ |
| **Minimum Allowable Orbit# (p. 39 table)** | ✅ The real MAO table by type and class, replacing the previous ad-hoc `0.01 × diameter` |
| **Secondary star Orbit#s (p. 27)** | ✅ Close 1D−1, Near 1D+5, Far 1D+11, Companion 1D÷10+(2D−7)÷100, with fractional variance; giants' companions use 1D × primary MAO |
| Secondary star eccentricity (p. 26, DM+2) | ✅ |
| Crossing stellar orbits resolved (p. 29) | ✅ Outer star pushed out one Orbit# until clear |
| Binary orbital periods (p. 30) | ✅ P = √(AU³/(M₁+M₂)) |

### System Worlds and Orbits (pp. 36–68)

| Procedure | Status |
|---|---|
| Gas giant / belt / terrestrial quantities + DMs (p. 37) | ✅ |
| **Available orbits & exclusion zones (pp. 38–39, rules 5–7)** | ✅ The book's Orbit#-based model is now the default, including the secondary's MAO in the margin and the eccentricity widenings. The Hill-sphere model remains available via `model='physics'`, with its zone-inversion bug fixed. Rules 8–11 (secondaries' own orbit allowances) are not implemented (❌) |
| HZCO (p. 41) | ✅ |
| Baseline number / orbit / spread (pp. 43–46) | ✅ Baseline is clamped to ≥ MAO and snapped into an available zone; no negative Orbit#s. The Step 6 per-orbit variance is still omitted (⚠️) |
| Empty & anomalous orbits (p. 47) | ⚠️ Quantities and placement order correct; anomaly types recorded as notes, and every rolled world is now placed |
| Orbital periods, eccentricity (p. 27) | ✅ |
| World and gas giant sizing (pp. 54–55) | ✅ |
| Significant moon quantity (p. 55) | ✅ |
| **Moon orbits (pp. 75–78)** | ✅ Hill sphere in AU and PD, Hill Sphere Moon Limit, Roche limit at 1.537 PD, Moon Orbit Range with the >200 cap, the Inner/Middle/Outer location table with the MOR<60 DM, moon periods, eccentricity, retrograde, and moon-removal (moons inside the Roche limit collapse to a ring; below 0.55 PD nothing survives) |
| Ring centre and width (p. 78) | ⚠️ Implemented, clamped inside the Roche limit; the width formula is an approximation of a garbled table |
| Mainworld candidates (p. 59) | ✅ Planets, significant moons and planetoid belts all compete |

### World Physical Characteristics (pp. 69–146)

| Procedure | Status |
|---|---|
| Density/composition, gravity, mass, escape velocity (p. 71) | ✅ Diameter is Size×1600 km without the book's variance (⚠️) |
| Planetoid belt internals: span, c/m/s-type %, bulk (pp. 72–75) | ❌ Belts carry a resource rating but no composition profile |
| **Expanded atmospheres (pp. 78–98)** | ✅ New `atmosphere.py`: the Atmosphere Codes table with pressure ranges and spans, total pressure, oxygen fraction and ppO₂, scale height, pressure-at-altitude, taint type/severity/persistence, exotic/corrosive/insidious/unusual subtypes, safe-altitude bands for Very Dense and Low, composition strings, and the runaway-greenhouse check |
| Hydrographics detail (pp. 99–102) | ⚠️ Core roll plus surface-distribution description; precise % and exotic liquids absent |
| Rotation period (p. 103) | ⚠️ Basic roll; solar day and days-in-year absent |
| Tidal lock (p. 105) | ⚠️ Single check for close orbits; the full table with 3:2 locks and retrograde results absent |
| Axial tilt (p. 104) | ⚠️ Main table only; Extreme Axial Tilt sub-table absent |
| Mean temperature (p. 108) | ✅ Book's Stefan-Boltzmann form; albedo and greenhouse are simplified (⚠️) |
| High/low temperatures (p. 112), seismology (p. 125), surface tidal effects (p. 107) | ❌ |
| Native lifeforms (p. 127) | ⚠️ Biomass and biocomplexity rolled; biodiversity, compatibility and the native/extinct sophont checks absent |
| Resource rating (p. 131) | ⚠️ Size-based; belt/density DMs absent |
| **Habitability rating (p. 132)** | ✅ 10 + DMs across the full Size/Atmosphere/Hydrographics/temperature/gravity table, clamped 0–12, with the frozen/boiling DM−6 provision |
| **Final Mainworld Determination (p. 133)** | ✅ Highest habitability wins, resource rating breaks ties, moons and belts eligible. The UWP's Size/Atmosphere/Hydrographics are now **derived from the physically generated world** instead of re-rolled |
| Mainworld mapping (p. 134) | ❌ Icosahedral world maps not implemented |

### World Social Characteristics (pp. 147–218)

| Procedure | Status |
|---|---|
| Core UWP rolls | ✅ Starport population DM ordering fixed (DM−2 now reachable); Tech Level now takes Government DMs |
| Population detail: significant digit, PCR, urbanisation, cities (p. 148) | ⚠️ Significant digit and total population implemented; PCR, urbanisation and city detail absent |
| **Government detail (p. 156)** | ✅ New `government.py`: centralisation, primary authority, structure, government profile, and factions with government type, strength and symmetric pairwise relationships |
| **Law detail (p. 163)** | ✅ Justice profile (PSU-I-D) with primary/secondary system, uniformity, presumption of innocence and death penalty; Law Level subcodes O-WECPR via 2D3−4 |
| Technology (p. 173) | ⚠️ The 6-field matrix is retained but is **not a WBH procedure** — the book's H-L-QQQQQ-TTTT-MM-N profile is not implemented. The misleading "WBH p.172" comment has been corrected |
| **Culture (p. 181)** | ✅ All eight traits now 2D + per-trait DMs from Population/Government/Law/Starport/TL, minimum 1 |
| **Economics (p. 185)** | ✅ New `economics.py`: Importance, Resource/Labour/Infrastructure/Efficiency factors, resource units, WTN with the starport modifier table, total population, GWP per capita and world GWP, inequality, development score, tariffs, and the T5-style economic extension string |
| Starport facilities detail (p. 193) | ❌ |
| Bases (p. 205) | ⚠️ Approximate core-rulebook rolls |
| Military branches and budget (p. 200) | ❌ |
| **Travel Zones (p. 208)** | ✅ Amber/Red on `StellarSystem.travel_zone` |

### Special Circumstances (pp. 219–234)

⚠️ Exotic primaries (white dwarf, brown dwarf, neutron star, pulsar, black hole,
protostar, nebula, cluster) are generated and physically usable, but the
chapter's dedicated system-characteristic procedures, empty hexes and artificial
worlds are ❌. Equipment (pp. 235–243) is gear, out of scope for a generator.

---

## 2. Coverage against the Sector Construction Guide

| Chapter | Status |
|---|---|
| Creating a Universe (pp. 3–8) | ⚠️ Reflected as a hardcoded Foreven-like premise |
| System Creation (pp. 9–16) | ⚠️ Density is a parameter (`density_target`) but contour/rift variants absent |
| Sector Details (pp. 17–27) | ✅ Settlement-wave population DMs now follow p.22 (thin −5, thick −3, +1/century, **capped at 0**); distances are true hex/parsec; Xboat network and travel zones implemented. Xboat *waystations*, border generation from history, and the Zhodani naval→military base coupling remain ❌ |
| Mainworld Design (pp. 28–39) | ⚠️ Core UWP plus the full WBH extensions; sophont-modified rolls and the isolation TL variant absent |
| Polity Design (pp. 40–49) | ⚠️ Three polities are still hardcoded, but now in **sector coordinates on a single 32×40 pass**, so the old re-tiling bug is gone and borders trace correctly. Procedural polity generation is ❌ |
| Sophont Design (pp. 50–60) | ⚠️ Minor-race generator uses invented lists rather than the SCG tables; homeworlds now placed at random hexes instead of a fixed hex per subsector |
| Sector Finalisation (p. 62) | ⚠️ `.sec` exporter present, not column-exact T5 |

---

## 3. Test suite and results

Run with: `pip install pytest pandas && python -m pytest tests/ -v`

- `tests/test_invariants.py` (15 tests) — internal consistency: no dropped
  worlds, orbits positive and sorted and inside available zones, secondary
  stars placed, moons given orbits, UWP well-formed, hex adjacency and
  distance correct against a reference cube-coordinate implementation.
- `tests/test_book_conformance.py` (18 tests) — the books' procedures with page
  references: star class diversity and spectral-type frequencies, binary
  periods, atmosphere pressure inside each code's tabulated range, ppO₂
  consistency, barometric falloff, habitability bounds and hostile-world
  ceilings, habitability-driven mainworld choice, moon mainworlds, UWP/physical
  consistency, 2D cultural traits, Tech Level government DMs, the economic
  extension's bounds and identities, WTN monotonicity in starport and
  population, government/justice/law profile structure, faction relationship
  symmetry, balkanised faction counts, travel zones, wave DM capping, and
  mainworld size distribution.
- `tests/test_renderer.py` (23 tests) — the drawing layer, described in §4a.

**Result: 56 passed, 0 failed, 0 skipped** (was 11 passed / 18 failed at the
first audit). Verified stable across multiple seeds, and 1,200 systems generate
across 40 seeds without error.

Defects found by the first audit and now fixed, each still covered by the test
that caught it:

1. Worlds silently dropped when the availability list was empty — fixed by
   correcting the availability model and rewriting `place_worlds`.
2. Availability inversion: the primary's own stability sphere was treated as
   forbidden, blanking all orbits in single-star systems.
3. Negative Orbit#s in hot systems.
4. Worlds placed inside exclusion zones (a rounding-after-snapping bug).
5. Secondary stars never given orbits or eccentricities.
6. Moons never given orbital distances.
7. Starport DM−2 unreachable through elif ordering.
8. Tech Level ignoring Government DMs.
9. Culture rolled on 1D instead of 2D+DMs.
10. Settlement-wave population DM reaching +7 instead of capping at 0.
11. Euclidean rather than hex distance.

Two structural changes were needed once moons could be mainworlds:
`StellarSystem.mainworld` and `.all_bodies` now search planets *and*
satellites, and every lookup goes through them — previously the map renderer
and `.sec` exporter silently missed moon mainworlds (123 of 626 systems in the
demo sector).

---

## 4. Can the maps look like the 1981 Classic Traveller originals?

Rendered samples generated during this audit (seed 1105) are the fairest basis
for comparison. The subsector renderer is the closer of the two: black-ink
hexes on cream, flat-topped hex grid in staggered vertical columns, hex numbers,
solid world discs, star/triangle base glyphs, upper-case names and a bounding
frame are all present and legible.

Against the 1981 Deluxe boxset foldout of the Spinward Marches (and the
Supplement-format subsector maps), the following are **missing or wrong**:

1. **No starport class letter** at the world — the single most prominent glyph
   on classic maps. Instead a full UWP string is printed inside the hex, which
   the originals never did (UWPs live in the accompanying world tables).
2. **No Amber/Red travel-zone rings** — zones are never generated (see §1), so
   the foldout's most distinctive markings can't be drawn.
3. **No polity borders** — the 1981 foldout's dashed Imperial/Zhodani/Sword
   Worlds borders are absent; allegiance data exists but no border-tracing.
4. **No Xboat/communication route network** — the defining connective tissue of
   the foldout. The code draws only adjacent-hex "trade routes" from an invented
   WTN formula, which almost never trigger (none visible on the sample render).
5. **No asteroid-belt glyph** — Size-0 mainworlds render as ordinary discs
   instead of the scattered-dots belt symbol; water worlds are not distinguished.
6. **Gas giant marker misplaced** — drawn as a concentric ring around the world
   instead of the classic small circle at the hex's upper right.
7. **No legend, subsector name grid, or scale**; layout bug: the bottom hex row
   overflows the border frame.
8. **Sector-scale map is unusable as a classic facsimile**: pastel allegiance
   fills tile incorrectly (hardcoded polity bug), coloured trade-code dots and
   green route lines are a modern style, and names/homeworlds repeat 16×.

**Conclusion:** the SVG approach is sound and the subsector map is perhaps
two-thirds of the way to a Supplement-style page, but a faithful 1981-foldout
look needs: travel-zone generation, border tracing from allegiance, an Xboat
route layer, starport letters, belt/water glyphs, a legend block, unique naming,
and single-pass whole-sector generation (32×40 with sector-wide polities) instead
of 16 independent subsectors. All are tractable; none currently exist.

### 4a. Renderer rework

All ten gaps listed above have since been addressed. `worldmaker/sector.py`
now renders in the classic idiom at both scales; `audit/classic_sector.png`
and `audit/classic_subsector.png` are the current output (seed 1105), against
`audit/gen_*.png` as the "before".

Supporting data added so the classic markings have something to draw:

- **Travel zones** — `generate_travel_zones()` in `polity.py` implements the
  SCG p.27 rules of thumb (Exotic/Corrosive/Insidious atmospheres, Government
  + Law Level ≥ 20, Balkanised worlds with conflict), with rare escalation to
  Red. `StellarSystem.travel_zone` holds `""`/`"A"`/`"R"`.
- **Xboat network** — `calculate_xboat_routes()` builds a minimum spanning
  network over Class A and B starports with every link inside jump-4, which is
  what produces the long connective route lines of the foldout.
- **Polity borders** — polities are now stored on `Sector.polities` and traced
  as dashed lines along the hex edges between territory and non-territory,
  using a new `hex_neighbors()` helper.
- **Unique names** — `generate_world_name(used)` takes a set and guarantees
  uniqueness; a sector of 617 systems now yields 617 distinct names.
- **Single-pass sectors** — `generate_full_sector()` generates a whole 32×40
  sector at once, so polities, sophonts, waves and routes are coherent
  sector-wide. `merge_subsectors()` retains support for the old sixteen-
  subsector data, and `generate_sector_svg()` still accepts a list of
  subsectors for legacy callers.
- **Two rule fixes the map depends on** — `hex_distance()` is now the true
  hex/parsec metric via cube coordinates (was Euclidean), and settlement-wave
  population DMs are capped at zero per SCG p.22 (was reaching +7).

Rendering conventions now implemented, per the numbered gaps above:

| Gap | Resolution |
|---|---|
| 1. Starport letter | Class letter drawn above the world symbol; UWP strings removed from hexes entirely |
| 2. Travel zones | Broken red ring (Amber) / solid red ring (Red) around hex contents |
| 3. Polity borders | Dashed red lines traced along hex edges |
| 4. Xboat routes | Heavy solid black lines, drawn beneath the grid |
| 5. Belt & water glyphs | Five-dot scatter for Size-0 mainworlds; solid disc when Hydrographics > 0, open circle when dry |
| 6. Gas giant marker | Small filled circle at the hex's upper right |
| 7. Legend / layout | Boxed legend of all ten conventions, reflowing to fewer columns on narrow maps; canvas sized so nothing overflows the frame |
| 8. Sector-scale style | Black ink throughout, no pastel fills or coloured trade dots; subsector division lines with A–P letters; single coherent polity layout |

Also: world names are set in bold capitals at Population 9+ and mixed case
otherwise, mirroring the originals' treatment of high-population worlds.

`tests/test_renderer.py` adds **23 tests** guarding the drawing layer —
glyph counts checked against the generated data, gas-giant offset direction,
zone ring styling, border segment geometry, Xboat jump-range and acyclicity,
legend completeness and reflow, hex regularity and flat-topped orientation,
viewBox containment, subsector windowing, and regression guards against UWP
strings and pastel fills reappearing. All 23 pass.

Suite total after the rework: **38 passed, 14 failed** (from 11/18 at the
audit baseline). The remaining 14 failures are the pre-existing generator
defects and missing WBH subsystems catalogued in §1–§3; this rework was
scoped to the map layer and did not touch them.

Known cosmetic limits: border segments are drawn per-edge rather than joined
into continuous paths, so at sector scale they read as a dashed chain rather
than a single sweeping line; and subsectors are labelled by letter only, not
by name.

---

## 5. What remains unimplemented

Honest list of gaps, for anyone picking this up:

**WBH**
- Mainworld mapping (p. 134): icosahedral world surface maps.
- High and low temperatures (p. 112) and additional temperature scenarios
  (p. 114); surface tidal effects (p. 107); seismology (p. 125).
- Planetoid belt internal composition: span, c/m/s-type percentages, bulk
  (pp. 72–75).
- Native lifeform biodiversity and compatibility ratings, and the native /
  extinct sophont checks (p. 127).
- Population detail beyond the significant digit: PCR, urbanisation, major
  cities (p. 148).
- The book's technology profile H-L-QQQQQ-TTTT-MM-N (p. 173). The existing
  6-field matrix is this project's own invention, now labelled as such.
- Starport facilities detail (p. 193) and military branches/budget (p. 200).
- Special Circumstances system procedures (pp. 219–234) beyond exotic primaries.
- Available-orbit rules 8–11: secondary stars' own orbit allowances.
- Assorted per-table variance the code approximates: world diameter variance,
  the Extreme Axial Tilt sub-table, the full tidal-lock table, albedo and
  greenhouse tables, Step 6 orbital variance.

**SCG**
- Procedural polity generation; the three polities remain hardcoded.
- Sophont design tables; the minor-race generator uses invented lists.
- Density contours and rift variants; Xboat waystations; border generation
  from sector history; column-exact T5 `.sec` output.

## 6. Suggested next steps

1. Replace the hardcoded polities with procedural generation (SCG pp. 40–49) —
   the biggest remaining gap between this and a usable custom sector, and the
   borders and allegiance colouring already exist to display it.
2. Implement the high/low temperature chain (p. 112), which feeds habitability
   properly and would let the frozen/boiling approximation be removed.
3. Population and city detail (p. 148), which the economics already half-needs.
4. The book's technology profile (p. 173), replacing the invented matrix.
5. Belt composition (pp. 72–75) and world mapping (p. 134) as polish.
