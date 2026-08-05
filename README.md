# worldmaker

A star system and sector generator for Mongoose Traveller 2nd edition,
implementing the procedures of the *World Builder's Handbook* (WBH) and the
*Sector Construction Guide* (SCG), and rendering maps in the style of the
Classic Traveller originals.

## Quick start

```bash
pip install pytest pandas
python -m pytest tests/          # 273 tests
```

```python
import random
import worldmaker as wm

random.seed(1105)

# One system, in full
system = wm.generate_full_system("Regina")
print(system.mainworld.uwp)              # e.g. A788899-C
print(wm.export_system_markdown(system)) # complete dossier

# A whole sector, generated in a single coherent pass
sector = wm.generate_full_sector("Foreven Reach")
open("sector.svg", "w").write(wm.generate_sector_svg(sector))
open("subsector.svg", "w").write(wm.generate_subsector_svg(sector, "Subsector A"))
open("sector.sec", "w").write(wm.export_sector_sec_file(sector))
```

Or start from the high-level choices the *Sector Construction Guide* asks
for, and let them drive generation:

```python
universe = wm.create_universe("Foreven Reach", preset="frontier")
universe.add_anomaly("barren", "The Quiet Zone", centre="1124", radius=2)
wm.build_default_timeline(universe)
print(universe.describe())

sector = wm.generate_universe_sector(universe, "Foreven")
```

Published sectors carry facts a generator must not overwrite. The canon
overlay honours them and generates the rest:

```python
canon = wm.fetch_canonical_sector("Foreven")      # travellermap.com, cached
canon = wm.merge_canon(canon, wm.scg_foreven())   # plus the Guide's own worlds
print(canon.summary())

sector = wm.generate_full_sector("Foreven", canon=canon, canon_mode="pin",
                                 canon_expand={"Av": 14})
```

For Foreven that fixes all 358 star positions, the Zhodani Consulate's
143-hex border, three Imperial client states and the seven established
worlds — while everything else is generated. `canon_mode` selects how much
to honour: `pin` (all of it), `seed` (positions and borders only, worlds are
yours to invent) or `positions` (star placements alone).

The two notebooks are thin front-ends over the package:

- `Traveller_System_Builder.ipynb` — one system in detail, with its world map.
- `traveller_world_generator.ipynb` — a sector, its polities and its maps.

## What it generates

**Stars** — primary type, subtype, mass, diameter, luminosity and system age;
the Special and Unusual results (giants, subgiants, subdwarfs, white and brown
dwarfs, neutron stars, pulsars, black holes, protostars); multiple-star
systems with Orbit#s, eccentricity and binary periods.

**System architecture** — gas giant, planetoid belt and terrestrial counts;
available orbits with the book's exclusion zones; habitable zone centre;
baseline number, baseline orbit and spread; empty and anomalous orbits;
world placement and orbital periods.

**Worlds** — size with precise diameter, composition, density, gravity, mass
and escape velocity; expanded atmospheres (pressure, oxygen fraction and
partial pressure, scale height, taints, exotic and corrosive subtypes);
hydrographics and surface distribution; rotation and tidal locking; albedo,
greenhouse, and mean, high and low temperatures; surface tides, seismic stress
and tectonic plates; native lifeforms (biomass, biocomplexity, biodiversity,
compatibility) with native and extinct sophont checks; resource and
habitability ratings.

**Temperature scenarios** — worst-case extremes, temperature by season,
mean temperature by latitude, temperature by time of day with sunlight
hours, twilight-zone mapping for tidally locked worlds, the altitude
temperature factor, and per-star contributions combined with the
temperature addition equation.

**Special circumstances** — white dwarf, neutron star, pulsar and black
hole systems; brown dwarfs by L/T/Y type; protostar and primordial systems
with magma oceans and debris belts; the empty-hex survey, with rogue gas
giants, terrestrials and small bodies; nebulae, star clusters and
artificial worlds from station modules to Dyson spheres.

**Moons and belts** — significant moon counts, Hill sphere and Roche limits,
moon orbits in planetary diameters, periods and rings; planetoid belt span,
composition, bulk, resource rating and significant bodies.

**Societies** — the UWP; population with concentration, urbanisation and named
major cities; government structure, centralisation, authority and factions;
justice profile and Law Level subcodes; the technology profile
(H-L-QQQQQ-TTTT-MM-N); the economic extension (importance, resources, labour,
infrastructure, efficiency, resource units, GWP, world trade number,
inequality, tariffs); starport facilities and capacities; military branches
and budget; cultural traits.

**Sectors** — system placement at configurable density; settlement waves;
native sophonts generated from the SCG's D66 tables; procedural polities that
expand from a capital along jump links bounded by their drive technology;
travel zones; trade and Xboat routes; subsector naming.

**Universes** — a guided entry point that turns a handful of high-level
choices (theme, star density, maximum Tech Level, trajectory, sophont
prevalence, polity count) into generation parameters, with anomalies —
rifts, clusters, supernova-sterilised regions, barren zones, plagues,
tech-suppressed regions and war-wrecked worlds — that reshape the sector
they cover, plus a rough timeline.

**Maps** — sector and subsector maps in the Classic Traveller idiom: black ink
on cream, flat-topped hexes, starport class letters, solid discs for worlds
with water and open circles for dry ones, belt scatters, gas giant markers,
base glyphs, travel-zone rings, dashed polity borders, Xboat route lines,
subsector divisions and a legend. Also icosahedral world surface maps.

## Layout

| Module | Contents |
|---|---|
| `classes.py` | Dataclasses: `UWP`, `Satellite`, `PlanetaryBody`, `Star`, `StellarSystem`, `Sector`, `Polity`, `Sophont` |
| `stellar.py` | Star generation, spectral data, stellar orbits |
| `system.py` | World counts, available orbits, baseline and spread, placement |
| `geophysics.py` | Size, composition, gravity, moons, life, habitability |
| `atmosphere.py` | Expanded atmosphere characteristics |
| `temperature.py` | Albedo, greenhouse, temperature range, tides, seismology |
| `belts.py` | Planetoid belt internals |
| `society.py` | UWP rolls, trade codes, culture |
| `population.py` | Concentration, urbanisation, cities |
| `technology.py` | The technology profile |
| `economics.py` | The economic extension |
| `government.py` | Government structure, factions, law |
| `starport.py` | Starport facilities and world military |
| `worldmap.py` | Icosahedral world surface maps |
| `sophont.py` | Major races and the SCG sophont design tables |
| `polity.py` | Procedural polities, travel zones, bases |
| `scenarios.py` | Season, latitude, time of day, twilight and altitude temperatures |
| `special.py` | Special Circumstances: empty hexes, dead stars, protostars |
| `universe.py` | Guided universe creation, anomalies and timelines |
| `canon.py` | Canonical sector overlays: published positions, borders and worlds |
| `sector.py` | Sector assembly and the classic map renderers |
| `t5.py` | Traveller5 Second Survey column and tab output |
| `exporters.py` | DataFrame, markdown dossier and `.sec` output |

## Fidelity

`AUDIT.md` records what is implemented against each chapter of both books,
what remains unimplemented, and where the code approximates a table the
source leaves ambiguous. The test suite checks conformance to the procedures
and their invariants — value ranges, dice distributions and derived-quantity
consistency — rather than transcribing every table entry; the temperature
model is validated against the book's own Terra benchmark.

Traveller is a trademark of Far Future Enterprises. The reference PDFs in
`documents/` are the owner's own copies and are not redistributable.
