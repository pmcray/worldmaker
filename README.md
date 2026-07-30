# worldmaker

A star system and sector generator for Mongoose Traveller 2nd edition,
implementing the procedures of the *World Builder's Handbook* (WBH) and the
*Sector Construction Guide* (SCG), and rendering maps in the style of the
Classic Traveller originals.

## Quick start

```bash
pip install pytest pandas
python -m pytest tests/          # 114 tests
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
| `sector.py` | Sector assembly and the classic map renderers |
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
