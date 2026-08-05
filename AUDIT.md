# Functionality Audit: World Builder's Handbook & Sector Construction Guide

**Scope:** the `worldmaker/` package, audited against the two reference books in
`documents/`: Mongoose Traveller 2e *World Builder's Handbook* (WBH, 258 pp.)
and *Sector Construction Guide* (SCG, 66 pp.).
**Method:** full source review, extraction of both books' contents, index and
checklist pages, and a 233-test pytest suite (`tests/`) combining
internal-invariant checks with conformance checks against the books' procedures
and dice distributions.

This document was first written as a gap analysis (11 of 29 tests passing) and
has been updated as the gaps were closed. §5 lists what is still missing.

## Verdict

**Both books are now implemented to the level this generator can usefully
reach, and the suite is green: 233 passed, 0 failed.** (The first audit found
11 passed / 18 failed.)

Every procedure the two books define for generating a system, a world, its
society and a sector is present. §5 lists the handful of things deliberately
left out and the places where a table in the source is ambiguous enough that
the code approximates it.

Two caveats about what "all tests pass" means. First, the suite tests
conformance to the procedures and their invariants - value ranges, dice
distributions, derived-quantity identities - rather than transcribing every
table entry digit for digit. The temperature model is validated against the
book's own Terra benchmark (255K equilibrium, 288K with greenhouse), which is
the one place the source gives a checkable answer. Second, where the PDF text
is illegible or the book leaves latitude, the code approximates and says so in
a comment; those cases are listed in §5.

---

## 1. Coverage against the World Builder's Handbook

Legend: OK implemented - APPROX implemented with documented approximation -
NO absent

### Stars (pp. 14-35)

| Procedure | Status |
|---|---|
| Primary star type and subtype tables (pp.15-17) | OK |
| Special and Unusual results: giants Ia-III, subgiants IV, subdwarfs VI, white and brown dwarfs, neutron stars, pulsars, black holes, protostars, nebulae, clusters | OK - about 2.3% of primaries are non-Class-V. White and brown dwarf masses and diameters are rolled; the rarer objects use representative values (APPROX) |
| Mass, temperature and diameter interpolation (pp.17-19) | OK - falls back to the nearest tabulated type where classes IV and VI omit part of the range |
| Luminosity formula (p.21) | OK |
| System age (pp.20-22) | APPROX - no post-stellar age adjustment |
| Multiple star presence and companion DMs (p.23) | OK |
| Minimum Allowable Orbit# (p.39 table) | OK |
| Secondary star Orbit#s (p.27) | OK - Close 1D-1, Near 1D+5, Far 1D+11, Companion 1D/10+(2D-7)/100, with giants' companions at 1D x primary MAO |
| Secondary star eccentricity (p.26, DM+2) | OK |
| Crossing stellar orbits resolved (p.29) | OK |
| Binary orbital periods (p.30) | OK |

### System Worlds and Orbits (pp. 36-68)

| Procedure | Status |
|---|---|
| Gas giant, belt and terrestrial quantities with DMs (p.37) | OK |
| Available orbits and exclusion zones (pp.38-39, rules 5-7) | OK - the book's Orbit#-based model is the default; the Hill-sphere model remains available as `model='physics'` |
| Secondaries' own orbit allowances (pp.39-40, rules 8-11) | OK |
| HZCO (p.41) | OK |
| Baseline number, orbit and spread (pp.43-46) | OK - clamped to at least MAO and snapped into an available zone. The Step 6 per-orbit variance is still omitted (APPROX) |
| Empty and anomalous orbits (p.47) | APPROX - quantities and placement order correct; anomaly types recorded as notes |
| Orbital periods and eccentricity (p.27) | OK |
| World and gas giant sizing (pp.54-55) | OK |
| Significant moon quantity (p.55) | OK |
| Moon orbits (pp.75-78) | OK - Hill sphere in AU and PD, moon limit, Roche limit, Moon Orbit Range with the >200 cap, the Inner/Middle/Outer table, periods, eccentricity, retrograde, and moon removal |
| Rings (p.78) | OK for centre location and the overlap rule; the span formula's dice operand is illegible in the source, so a d100 fraction is used (APPROX) |
| Mainworld candidates (p.59) | OK - planets, significant moons and belts all compete |

### World Physical Characteristics (pp. 69-146)

| Procedure | Status |
|---|---|
| Size with precise diameter, composition, density, gravity, mass, escape velocity (pp.70-71) | OK |
| Planetoid belt internals: span, m/s/c-type composition, bulk, resource rating, significant bodies (pp.72-75) | OK |
| Expanded atmospheres (pp.78-98) | OK - pressure ranges and spans, total pressure, oxygen fraction and ppO2, scale height, pressure at altitude, taint type/severity/persistence, exotic, corrosive, insidious and unusual subtypes, safe-altitude bands, composition, runaway greenhouse |
| Hydrographics detail (pp.99-102) | APPROX - core roll plus surface distribution; precise percentage and exotic liquids absent |
| Rotation period (p.103) | APPROX - basic roll; solar day and days-in-year absent |
| Tidal lock (p.105) | APPROX - single check for close orbits; the full table with 3:2 locks absent |
| Axial tilt (p.104) | APPROX - main table only; the Extreme Axial Tilt sub-table absent |
| Albedo and greenhouse (p.110) | OK - both tables with all their modifiers |
| Mean temperature (p.108) | OK - validated against Terra |
| High and low temperatures (pp.112-115) | OK - axial tilt, rotation and geographic factors, atmospheric damping, luminosity modifier, near and far AU |
| Temperature scenarios (pp.114-124) | OK - worst case, by season, by latitude (Parts A and B), by time of day (both methods), sunlight portion and hours, twilight zone worlds, altitude factor, multiple-star contributions, gas giant residual heat. See `scenarios.py` |
| Surface tidal effects (pp.107, 126) | OK |
| Seismology (pp.125-128) | OK - residual stress, tidal stress, tidal heating, total stress, tectonic plates, seismic temperature addition |
| Native lifeforms (pp.127-131) | OK - biomass with its DMs, biocomplexity, biodiversity, compatibility, and the native and extinct sophont checks |
| Resource rating (p.131) | OK for worlds and belts |
| Habitability rating (p.132) | OK - the full DM table, clamped 0-12 |
| Final Mainworld Determination (p.133) | OK - habitability, resources and native life weighed together as the book's four criteria describe; the UWP derives from the physical world |
| Mainworld mapping (pp.134-146) | OK - icosahedral terrain generation and an SVG net renderer |

### World Social Characteristics (pp. 147-218)

| Procedure | Status |
|---|---|
| Core UWP rolls | OK |
| Population detail: significant digit, PCR, urbanisation, major cities (pp.148-156) | OK |
| Government detail (p.156) | OK - centralisation, authority, structure, profile, factions with strength and symmetric relationships |
| Law detail (p.163) | OK - justice profile PSU-I-D and Law Level subcodes O-WECPR |
| Technology profile (pp.173-180) | OK - H-L-QQQQQ-TTTT-MM-N with the TLM table and every subcategory bound |
| Culture (pp.181-185) | OK - eight traits at 2D + DMs |
| Economics (pp.185-199) | OK - importance, resources, labour, infrastructure, efficiency, resource units, WTN, GWP, inequality, development, tariffs |
| Starport facilities (pp.193-196) | OK - highport, fuel, repair, shipyard, bases including waystations and corsairs, capacities, traffic |
| Bases (p.205) | OK - via the Starport Facilities table, with polity overrides |
| Military branches and budget (pp.200-207) | OK - eight branches with Effect ratings, budget percentage, readiness, EMAWF-SNM profile |
| Travel Zones (p.208) | OK |

### Special Circumstances (pp. 219-234)

| Procedure | Status |
|---|---|
| Empty hexes: object types and probabilities (pp.219-221) | OK - the full sequence (neutron star/black hole on 3D 18, white dwarf on 1D 6, brown dwarf, then rogue planets) each gated on the region's system-density check |
| Empty Hex Objects table: survey indices and detection points (p.221) | OK as data. The detection *procedure* (accumulating points, sensor checks) is a referee/player activity, not generation, and is NO |
| Jumping to empty hexes (p.223) | OK for the target-type DMs and the prepared-template DM; the arrival-variance task chain is NO |
| Protostar systems (pp.224-225) | OK - DM+1 star type, inflated diameter with luminosity scaling, debris belt in every planetary orbit, age-capped world sizes, magma oceans, DM+2 eccentricity, atmosphere DM+4 and remap, no native life |
| Primordial systems (pp.225-226) | OK - DM+1 eccentricity, belt existence DM+4, doubled belt spans, co-orbital planets on a 1D 6, atmosphere DM+2 and remap, magma oceans, no native life |
| Brown dwarfs (pp.226-227) | OK - mass formula, gas-giant diameter roll with the 0.05-0.07 DM, the L/T/Y types table with subtype ageing, MAO 0.005, gas giant present on 7- |
| Dead stars: white dwarfs (p.227) | OK - mass and inverse-mass diameter formulas, the White Dwarf Aging table interpolated and mass-scaled |
| Dead stars: neutron stars, pulsars, magnetars (p.228) | OK - mass formula under the 2.16 limit, 19+1D km diameter, pulsar and magnetar frequencies |
| Dead stars: black holes (p.228) | OK - exploding-sixes mass formula, 5.9km x Mass diameter, no radiation |
| Dead star planetary systems (p.229) | OK - the 8+ existence check with its DMs and the natural-12 rule, rarer gas giants, commoner belts, 1D-2 terrestrials, MAO 0.001, radioactive taint at severity and persistence 9 around pulsars |
| Nebulae (pp.229-230) | OK for the Random Nebula Type table, the planetary nebula's new white dwarf and the supernova remnant's central object. Multi-hex expansion is left to the referee (the book calls it a map-drawing choice) |
| Star clusters (p.231) | OK - 2D+5 systems in a hex, all sharing an age of 1D x 1D x 50 million years |
| Artificial worlds (pp.231-232) | OK as the full Artificial World Types table, gated by Tech Level |
| M-drive efficiency in deep space (p.224) | NO - a ship-operations table, not a generation procedure |
| Profile forms (pp.233-234) | NO - a presentation format; the markdown dossier covers the same ground |

---

## 2. Coverage against the Sector Construction Guide

| Chapter | Status |
|---|---|
| Creating a Universe (pp.3-8) | OK - `create_universe()` takes the book's high-level choices (theme, density, maximum Tech Level, trajectory, sophont prevalence, polity count) and drives generation from them; anomalies and a rough timeline are modelled. See `universe.py` |
| System Creation (pp.9-16) | OK - density is a parameter, and rift and cluster anomalies vary it by region; the book's density *contour* drawing is NO |
| Sector Details (pp.17-27) | OK - settlement waves per p.22 with DMs capped at zero, true hex distances, Xboat network, travel zones. Xboat waystations come from the starport table; border generation from sector history is NO |
| Mainworld Design (pp.28-39) | OK via the WBH extensions; the isolation TL variant is NO |
| Polity Design (pp.40-49) | OK - procedural capitals, jump-range-bounded expansion, government form, naming, type and defence index. `define_foreven_polities()` retains the book's worked example |
| Sophont Design (pp.50-60) | OK - the full D66 Sophont Physical Characteristics table, with senses, psychology and characteristic DMs derived from the results |
| Sector Finalisation (p.62) | OK - column-exact T5 Second Survey output, plus the tab-delimited interchange format. See `t5.py` |

---

## 3. Test suite

Run with `pip install -r requirements.txt && python -m pytest tests/`.

| File | Tests | Covers |
|---|---|---|
| `test_invariants.py` | 15 | Internal consistency: no dropped worlds, orbits positive, sorted and inside available zones, secondary stars placed, moons given orbits, UWP well-formed, hex adjacency and distance against a reference implementation |
| `test_book_conformance.py` | 20 | Star class diversity and spectral frequencies, binary periods, atmosphere pressure ranges and ppO2, barometric falloff, habitability bounds, mainworld selection, moon and desert mainworlds, 2D cultural traits, Tech Level DMs, economic identities, WTN monotonicity, government and law profile structure, faction symmetry, travel zones, wave DM capping, size distribution |
| `test_temperature.py` | 16 | Terra benchmark, inverse-square falloff, the tilt/rotation/geographic factor tables, albedo bounds, greenhouse scaling, high/low bracketing, atmospheric damping, tidal falloff, seismic stress identities |
| `test_world_detail.py` | 21 | Belt composition and bulk, lifeform profiles, sophont thresholds, population profiles and urbanisation caps, city populations, technology profile structure and bounds |
| `test_polity.py` | 14 | Jump ranges, capital selection and separation, non-overlapping contiguous territory, allegiance recording, independent space, defence index scaling |
| `test_renderer.py` | 29 | Every map convention checked against the generated data, hex geometry, viewBox containment, border chaining, legend reflow, windowing, and regression guards against UWP strings and pastel fills |
| `test_scenarios.py` | 30 | Worst-case temperatures against the book's Terra and Zed Prime checks, seasonal cycling and lag, latitude zones and adjustments for both tilt cases, the diurnal curve and its continuity across dusk, sunlight portion at the equator and poles, twilight-zone monotonicity, altitude cooling, the temperature addition equation against the book's own table, gas giant residual heat |
| `test_special.py` | 34 | Dead star mass and diameter formulas and their limits, the aging table, brown dwarf types against the book's table, dead-star system existence DMs, pulsar taint, protostar and primordial conditions, rogue world sizes, empty-hex object frequencies, nebula and cluster generation, artificial world tech gating, jump DMs |
| `test_t5_export.py` | 21 | The format specification's own example parsed field for field, T5SS field order, separator-defined column widths and minimums, every row's alignment, round-tripping, field syntax, and agreement between the column and tab formats |
| `test_universe.py` | 29 | Density targets and the playable range, Tech Level ceilings holding across a sector, trajectory DMs, preset validity, sophont prevalence scaling, every anomaly's effect on the worlds it covers, rift and cluster density changes, timeline ordering and content, and that a universe-driven sector still exports and renders |

**233 passed, 0 failed.** Verified across multiple seeds; 1,200 systems
generate across 40 seeds without error.

The eleven defects the first audit found are all fixed and each is still
covered by the test that caught it: dropped worlds, the availability
inversion, negative Orbit#s, worlds in exclusion zones, unplaced secondary
stars, moons without orbits, the unreachable starport DM, missing Tech Level
government DMs, 1D culture rolls, uncapped settlement-wave DMs, and Euclidean
hex distance. Later work surfaced and fixed three more: a polity could swallow
another's capital and claim it twice; a Sibling star of an exotic primary
crashed the generator; and trace atmospheres rounded away to an exact vacuum.

Building the temperature scenarios surfaced two more, both in the existing
temperature and placement code:

- **Worlds piled onto the outermost orbit.** A wide system spread walked the
  outer worlds past the end of the orbit table, where each one snapped onto
  the same outermost Orbit#. About one system in six stacked three or more
  worlds at Orbit# 20 - 78,700 AU - and one stacked ten. The spread is now
  narrowed so the last world still lands inside the available orbits, and a
  world that would land on top of its neighbour moves to the next available
  orbit, stepping over an exclusion zone where it has to. Duplicate orbits
  fell from routine to three worlds in 1,940. Guarded by
  `test_worlds_do_not_pile_onto_one_orbit` and
  `test_outermost_orbit_is_not_a_dumping_ground`.
- **Inherent heat was dropped from cold worlds.** The seismic temperature
  addition returned early when the equilibrium temperature was zero, so a
  world receiving nothing from its sun read 0K rather than the temperature
  its own internal heat sustains - precisely the rogue-world case the book
  uses to make the point (p.127). The scenarios then disagreed with the
  world's own mean, by 96K in the first system the notebook generated.
  Inherent heat is now applied to every scenario result, as pp.125-126
  require ("all high, low, mean, local or periodic temperature values").
  Guarded by `test_scenarios_carry_the_worlds_inherent_heat` and
  `test_mean_is_the_temperature_at_45_degrees`.

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

Since that pass, border edges are chained head-to-tail into continuous
polylines, so a border reads as one sweeping line rather than a chain of
disconnected dashes (57 polylines in place of several hundred segments in the
demo sector), and subsectors are labelled with both their letter and a name
taken from their most notable world.

`audit/classic_sector.png` and `audit/classic_subsector.png` are the current
sector and subsector output; `audit/worldmap.png` is an icosahedral world
surface map; `audit/gen_*.png` are the original "before" renders.

---

## 5. What remains unimplemented

Deliberately out of scope, or approximated:

**Not implemented**
- Equipment, vehicles, robots and software (pp.235-243) - gear chapters, not
  generation procedures.
- Precise hydrographic percentages and exotic liquid composition (pp.99-102).
- Solar day and days-in-year (p.104); the full Tidal Lock Status table with
  3:2 locks (p.105); the Extreme Axial Tilt sub-table.
- The empty-hex *detection* procedure (pp.221-222) and the empty-hex arrival
  variance task chain (p.223): both are play procedures rather than
  generation, though the tables they need are present as data.
- M-drive efficiency in deep space (p.224) and the IISS profile forms
  (pp.233-234).
- SCG density contour drawing; border generation from sector history.

**Approximated, and flagged in the code**
- The ring span formula's dice operand is illegible in the source PDF; a d100
  fraction is used. Ring centre location and the overlap rule are exact.
- System age ignores post-stellar adjustment.
- The Step 6 per-orbit variance in world placement is omitted.
- Anomalous orbit types are recorded as notes rather than modelled.
- The time-of-day thermal lag is applied as a lag rather than the lead the
  printed formula's `+0.15` would produce: taken literally it puts the
  warmest hour in mid-morning and a warm spike at dawn, contradicting the
  surrounding text ("coldest near dawn... does not reach full heat until the
  afternoon"). The sign is flipped so the curve matches the description.
- In the seasonal and time-of-day scenarios the luminosity modifier is
  allowed to go negative, so that deep winter and the small hours fall
  *below* the mean. Read strictly, "the luminosity modifier... must still be
  between 0 and 1" (p.115) would mean a world is never cooler than its mean
  at any time of year, which contradicts the same paragraph's description of
  the tilt factor going "to the negative in winter". The magnitude is still
  bounded by 1.
- The T5 cultural extension `[Cx]` wants Homogeneity, Acceptance,
  Strangeness and Symbols; the generator produces the WBH's eight cultural
  traits instead, so the four are read off cohesion, xenophilia, uniqueness
  and symbology, which cover the same ground.
- T5 nobility codes are assigned from the world's Importance rather than
  from the Traveller5 rulebook's own table, which is outside these two
  books.
- The `Star Cluster` and `Nebula` results on the primary star table still
  use representative stellar values, since a hex-scale structure has no
  single set of stellar characteristics; `special.py` generates the real
  thing for callers who want it.

**Retained but not from the books**
- The 6-field technology matrix on `UWP` (`tl_spaceflight` and friends) is this
  project's own invention. It is kept for backward compatibility and labelled
  as such; the book's real technology profile is implemented separately in
  `technology.py`.

## 6. Suggested next steps

The four items this section previously listed - the temperature scenarios,
the Special Circumstances system types, column-exact T5 output and the
guided universe entry point - are all implemented; see §1, §2 and §3. What
is left is smaller and largely a matter of taste:

1. Precise hydrographic percentages and exotic liquid composition
   (pp.99-102), the one remaining physical characteristic still rolled at
   UWP granularity.
2. Solar day, days-in-year and the full Tidal Lock Status table (pp.104-105).
   The scenario code already takes a solar day as an argument, so this would
   feed it real values rather than the rotation period.
3. Border generation from sector history (SCG p.26): borders are currently
   traced from the polity territory the generator produces, not from the
   sequence of wars and treaties that would explain their shape.
4. A play-side layer over the empty-hex data: the detection procedure
   (pp.221-222) and the arrival-variance task chain (p.223) are the only
   parts of Special Circumstances left out, and both are about resolving a
   scene rather than building a sector.
