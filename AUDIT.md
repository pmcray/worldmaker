# Functionality Audit: World Builder's Handbook & Sector Construction Guide

**Date:** 2026-07-22
**Scope:** `worldmaker/` package (~2,650 lines) audited against the two reference
books in `documents/`: Mongoose Traveller 2e *World Builder's Handbook* (WBH,
258 pp.) and *Sector Construction Guide* (SCG, 66 pp.).
**Method:** full source review, extraction of both books' contents/index/checklist
pages, and a 29-test pytest suite (`tests/`) combining internal-invariant checks
with statistical conformance checks against the books' dice procedures.

## Verdict

**No — the functionality of the two books is not fully implemented.** The package
implements a working *skeleton* of the WBH expanded-method system generator
(stars → orbits → world placement → basic detailing → core-rulebook UWP) plus a
hardcoded, Foreven-flavoured sector wrapper from the SCG. By procedure count it
covers roughly **a fifth to a quarter of the WBH** and perhaps a third of the SCG,
and several of the parts that *are* present diverge from the books' actual tables
or contain outright bugs. The test suite demonstrates this concretely:
**11 of 29 tests pass; 18 fail**, and each failure is a specific missing rule or
defect (details below).

---

## 1. Coverage against the World Builder's Handbook

### Stars (WBH pp. 14–35) — partially implemented

| Procedure | Status |
|---|---|
| Primary star type/subtype tables (pp. 15–17) | ✅ Implemented, with one big exception below |
| Special/Unusual results: Class Ia–IV giants, Class VI subdwarfs, white dwarfs, brown dwarfs, neutron stars, pulsars, black holes, protostars, nebulae, clusters | ❌ **Not implemented.** `generate_primary_star` hardcodes a `Special` roll to a G-type Class V star. The lookup tables for these objects exist in `data.py` but are unreachable. Over any sample, 100% of primaries are luminosity class V (test `test_primary_star_class_diversity`) |
| Mass/temperature/diameter interpolation (pp. 17–19) | ✅ Implemented |
| Luminosity formula (p. 21) | ✅ Implemented |
| System age (pp. 20–22) | ⚠️ Simplified (no post-stellar age adjustment) |
| Multiple star presence + companion DMs (p. 23) | ✅ Implemented |
| **Secondary star Orbit# assignment (p. 27: Close 1–5, Near 6–10, Far 11–15 + variance)** | ❌ **Never assigned.** `Star.orbit_num` stays 0.0 for every Close/Near/Far star (test `test_secondary_stars_have_orbits`). Secondary eccentricity is also never rolled. This silently breaks all downstream multi-star logic |
| Binary orbital periods (p. 30) | ❌ Not implemented |

### System Worlds and Orbits (pp. 36–68) — the strongest area, still incomplete

| Procedure | Status |
|---|---|
| Gas giant / belt / terrestrial quantities + DMs (p. 37) | ✅ Implemented |
| Available orbits & forbidden zones (p. 38) | ⚠️ Two models exist, both broken in practice. Because secondary `orbit_num` is never set, forbidden zones centre on Orbit 0. Worse, the default "physics" model treats the **primary's own stability sphere as a forbidden zone**, so in every single-star system `available_orbits` computes to an **empty list**. Consequences proven by tests: anomalous worlds are silently dropped (`test_world_counts_match_bodies`: e.g. 15 bodies placed of 17 rolled), and in multi-star systems 19/560 worlds land inside forbidden zones (`test_orbits_within_available_zones`) |
| HZCO (p. 41) | ✅ Implemented (√L formula) |
| Baseline number / baseline orbit / spread (pp. 43–46) | ⚠️ Implemented but unguarded: hot-system baseline orbits can go **negative** (test found a planetoid belt at Orbit# −0.29), and the book's Step 6 per-orbit variance `(2D−7)×0.1×Spread` is omitted |
| Empty & anomalous orbits (p. 47) | ⚠️ Quantities implemented; anomaly types mostly reduced to a note string |
| Orbital periods, eccentricity table | ✅ Implemented (eccentricity DMs omitted) |
| World and gas giant sizing (pp. 54–55) | ✅ Implemented |
| Significant moon **quantity** (p. 55) | ✅ Implemented |
| Moon **orbits** (PD locations, Roche limit, Hill-sphere moon limit, moon periods, ring centre/width profiles, pp. 75–78) | ❌ **Not implemented.** The `Satellite.orbit_pd` / `period_hours` fields exist but are never populated — 5,320 moons generated in testing, none has an orbital distance (`test_satellite_orbits_are_populated`) |
| Mainworld candidate determination (p. 59) | ❌ Replaced by "first terrestrial world is the mainworld" (see Habitability below) |

### World Physical Characteristics (pp. 69–146) — mostly missing

| Procedure | Status |
|---|---|
| Density/composition, gravity, mass, escape velocity (p. 71) | ✅ Implemented (diameter is always Size×1600 km; the book rolls variance) |
| Planetoid belt characteristics: span, c/m/s-type composition %, bulk, resource rating, belt profile (pp. 72–75) | ❌ Not implemented — belts get `size_code='0'` and nothing else |
| **Expanded atmospheres** (pp. 78–98): pressure in bar, oxygen fraction/ppO₂, scale height, taint type/severity, exotic/corrosive/insidious types, Very Dense/Low/Unusual handling, non-HZ atmospheres | ❌ **Entirely absent** — only the core-rulebook 2D−7+Size roll exists. This is the largest single chapter of the book |
| Hydrographics detail: precise %, temperature DMs, surface distribution, exotic liquids (pp. 99–102) | ⚠️ Core roll + flavour-text only |
| Rotation (p. 103): basic roll | ✅ Implemented; solar day, days/year, minutes-seconds ❌ |
| Tidal lock table (p. 105) with 3:2 locks, retrograde results, moon locks | ⚠️ Reduced to a single 2D≥10 check for Orbit# < 1 |
| Axial tilt (p. 104) | ⚠️ Table rows 9–10 diverge; the Extreme Axial Tilt sub-table is missing |
| Surface tidal effects (p. 107) | ❌ Not implemented |
| Mean temperature (p. 108) | ✅ The Stefan-Boltzmann form `279×(L(1−A)(1+G)/AU²)^0.25` matches the book; albedo/greenhouse are crude constants instead of the book's tables |
| High/low temperatures (p. 112), additional scenarios (p. 114) | ❌ Not implemented |
| Seismology: residual/tidal stress, heating, tectonic plates (p. 125) | ❌ Not implemented |
| Native lifeforms (p. 127): biomass & biocomplexity | ⚠️ Rolled without any of the book's DMs; **biodiversity, compatibility ratings and the native/extinct sophont checks are missing** |
| Resource rating (p. 131) | ⚠️ Simplified (uses Size, none of the belt/density DMs) |
| **Habitability rating (p. 132) and Final Mainworld Determination (p. 133)** | ❌ Not implemented — the mainworld is always the innermost terrestrial world, and its UWP is **re-rolled from scratch**, disconnected from the physically generated world (`generate_mainworld_uwp` re-rolls Size/Atm/Hyd and overwrites the world's size) |
| Mainworld mapping (p. 134): icosahedral world maps | ❌ Not implemented |

### World Social Characteristics (pp. 147–218) — core-rulebook level only

| Procedure | Status |
|---|---|
| Core UWP rolls (Pop/Gov/Law/Starport/TL) | ⚠️ Present but buggy: the starport population DM chain tests `pop <= 4` before `pop <= 2`, so **DM−2 is unreachable** (proven statistically: P(Starport X \| Pop 1) = 0.083 vs the correct 0.167); the TL table **omits all Government DMs** (Gov 0/5 +1, Gov 7 +2, Gov D/E −2) |
| Population extension: significant digits, PCR, urbanisation %, major cities (p. 148) | ❌ Not implemented |
| Government: centralisation, authority, structure, factions with strength/relations (p. 156) | ❌ Replaced by ad-hoc random flavour strings |
| Law: justice profile (PSU-I-D), sub-Law Levels O-WECPR (p. 163) | ❌ Not implemented |
| Technology extension (p. 173): minimum sustainable TL, high/low common TL, quality-of-life/transport/military/novelty TLs, profile H-L-QQQQQ-TTTT-MM-N | ❌ Not implemented. The code's "6-field tech matrix" (`tl_spaceflight` etc., commented "WBH p. 172") **does not exist in the book** — it is an invention |
| Culture (p. 181): 8 traits | ⚠️ Present but rolled with **1D instead of 2D+DMs** — trait values above 6 can never occur (proven over 3,088 samples) |
| Economics (p. 185): Importance Ix, Resources/Labour/Infrastructure/Efficiency, RU, GWP, WTN, inequality, development, tariffs | ❌ **Entirely absent** |
| Starport facilities detail: highport/downport capacity, shipyards, traffic (p. 193) | ❌ Not implemented |
| Bases (p. 205) | ⚠️ Approximate core-rulebook-style rolls |
| Military branches/budget (p. 200) | ❌ Not implemented |
| Travel Zones (p. 208) | ❌ Not implemented — no field for zones exists anywhere |

### Special Circumstances (pp. 219–234) & Equipment (pp. 235–243)

❌ Nothing implemented: empty hexes, protostar/primordial systems, brown dwarfs,
dead stars (white dwarf/neutron/black hole systems), nebulae, star clusters,
artificial worlds. (Equipment/robots/software are gear chapters — arguably out of
scope for a generator, but they are part of "all the functionality".)

---

## 2. Coverage against the Sector Construction Guide

| Chapter | Status |
|---|---|
| Creating a Universe (pp. 3–8) | ⚠️ Reflected only as a hardcoded Foreven-like premise |
| System Creation (pp. 9–16) | ⚠️ Fixed 50% presence roll (4+ on 1D). Density contours/rift variants ❌; phased creation ❌ |
| Sector Details (pp. 17–27) | ⚠️ Settlement waves exist but violate the book: SCG DMs are thin −5+1/century and thick −3+1/century **capped at zero**; the hardcoded 10-century wave gives **DM+7**, inflating population sector-wide (`test_population_wave_dm_capped`). Wave reach and trade routes use **Euclidean distance on offset coordinates**, not hex/parsec distance — off by up to 30% (`test_hex_distance_is_hex_metric`). Xboat/communication routes ❌; borders ❌; Zhodani naval→military base coupling ❌; Forbidden/Amber zone substitution ❌ |
| Mainworld Design (pp. 28–39) | ⚠️ Core UWP only; sophont-modified rolls, isolation TL variant, survivability upgrades ❌ |
| Polity Design (pp. 40–49) | ❌ Three polities are hardcoded (Zhodani/Avalar/Imperium) with fixed hex rectangles; no procedural polity generation. Worse, the coordinates are **sector-scale (up to 3240) while `generate_sector()` generates one 8×10 subsector**, so the Imperium/Avalar never match anything and the Zhodani block re-tiles in the top-left of *every* subsector (clearly visible on the rendered sector map) |
| Sophont Design (pp. 50–60) | ⚠️ A minor-race generator exists but uses invented `random.choice` lists, not the SCG's tables; Tlinzha traveller creation ❌ |
| Sector Finalisation (p. 62) | ⚠️ A rough `.sec` exporter exists (not column-exact T5/Travellermap format) |

Additional sector-level defects found: the Aslan homeworld is placed at hex 0805
of **every** subsector (16 copies per sector), and the world-name generator has a
~260-name space with no uniqueness check, so names repeat many times per map.

---

## 3. Test suite and results

Run with: `pip install pytest pandas && python -m pytest tests/ -v`

- `tests/test_invariants.py` — internal consistency (would pass in a correct
  implementation regardless of book fidelity).
- `tests/test_book_conformance.py` — checks against the books' actual dice
  procedures and data model, with page references.

Result: **11 passed, 18 failed.** What passes: generation never crashes over
hundreds of systems; every system has a physically sensible primary; eccentricity
bounds; period positivity; UWP string format; hex-grid adjacency (correct and
symmetric); mainworld size distribution ≈ 2D−2; primary star spectral-type
frequencies match the WBH table; sector generation, `.sec` export and SVG output
are well-formed.

Confirmed defects (each reproduced by a named test):

1. **Worlds silently dropped** — rolled anomalous worlds never placed when
   `available_orbits` is empty (every single-star system under the default
   physics model).
2. **Empty availability inversion** — the primary's stability sphere is treated
   as forbidden, blanking all orbits in single-star systems.
3. **Negative Orbit#s** generated for hot systems (belt at Orbit# −0.29).
4. **Worlds placed inside forbidden zones** in multi-star systems (19/560).
5. **Secondary stars never get orbits or eccentricities** (WBH p. 27 skipped).
6. **Moons have no orbits** (WBH pp. 75–78 skipped; fields exist, never filled).
7. **Starport DM−2 unreachable** (elif ordering bug).
8. **TL roll ignores Government DMs.**
9. **Culture rolled on 1D instead of 2D+DMs.**
10. **Settlement-wave population DM +7** instead of capped ≤ 0 (SCG p. 22).
11. **Euclidean-not-hex distance** for waves and trade routes.
12. Missing subsystems (economics, travel zones, habitability, expanded
    atmospheres, belt profiles, law/government detail, non-V stars, binary
    periods) each have a failing conformance test documenting them.

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

### 4a. Renderer rework — completed

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

## 5. Recommended order of work

1. ~~Fix rule-fidelity bugs that skew every map: wave DM cap, hex distance.~~
   **Done** (see §4a); starport DM ordering and TL government DMs still open.
2. ~~Implement travel zones.~~ **Done** (see §4a).
3. ~~Rework the renderer for classic fidelity and generate sectors in one
   pass.~~ **Done** (see §4a).
4. Fix the placement bugs (empty availability inversion, dropped worlds,
   negative orbits, secondary star orbits) — everything downstream depends on
   it, and these are now the largest remaining source of test failures.
5. Fix the remaining rule-fidelity bugs: starport population DM ordering,
   Tech Level government DMs, culture dice (1D → 2D+DMs).
6. Implement habitability-based mainworld selection and derive the mainworld
   UWP from the physically generated world instead of re-rolling it.
7. Then tackle the big missing WBH subsystems in order of table impact:
   expanded atmospheres, moon orbits, economics, population/government/law
   detail, special circumstances.
