# worldmaker

A star system and sector generator for Mongoose Traveller 2nd edition,
implementing the procedures of the *World Builder's Handbook* (WBH) and the
*Sector Construction Guide* (SCG), and rendering maps in the style of the
Classic Traveller originals.

## Quick start

### In the browser, with nothing installed

Open a notebook in Google Colab and run the cells. Its first cell installs
the package into the Colab runtime; nothing else is needed, and nothing is
installed on your own machine.

| Notebook | |
|---|---|
| **Sector Explorer** — a sector, its maps and everything in it | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/pmcray/worldmaker/blob/claude/status-colab-notebooks-w4tnm6/Traveller_Sector_Explorer.ipynb) |
| System Builder — one system in full detail | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/pmcray/worldmaker/blob/claude/status-colab-notebooks-w4tnm6/Traveller_System_Builder.ipynb) |
| Sector Generator — polities, maps and universes | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/pmcray/worldmaker/blob/claude/status-colab-notebooks-w4tnm6/traveller_world_generator.ipynb) |

The badges and each notebook's bootstrap cell point at the branch this work
lives on, because `master` still holds only the project's first two
commits. When it is merged, re-point them with `python colab_cells.py
master` and change the three links above.

Colab's runtime is discarded when the session ends, so each notebook ends
with a cell that downloads what it generated — the sector data, the maps
and the dossiers — to your own machine.

### Locally

```bash
pip install -r requirements.txt
jupyter lab                      # then open Traveller_Sector_Explorer.ipynb
```

Or as a library, without the repository:

```bash
pip install git+https://github.com/pmcray/worldmaker.git
```

**`Traveller_Sector_Explorer.ipynb` is the place to start.** Run its cells in
order and you get a generated sector, the sector and subsector maps, a
sortable table of every system, a picker that shows any system in full —
including its secondary worlds and the nations of a balkanised one — the
candidates for Erith, and a scan of the worlds worth a Referee's attention,
each with the reasons it was flagged.

Two narrower notebooks remain: `Traveller_System_Builder.ipynb` for one
system in detail with its temperature scenarios and world map, and
`traveller_world_generator.ipynb` for a sector's polities and maps.

Everything is also a plain library, used from the repository root:

```bash
python -m pytest tests/          # 429 tests
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

The *Sector Construction Guide* does not stop at those seven worlds. Over
sixty pages it works Foreven up into a playable sector and prints the
result, and `scg_foreven_full()` is that whole treatment:

```python
canon = wm.merge_canon(wm.fetch_canonical_sector("Foreven"),
                       wm.scg_foreven_full())
sector = wm.generate_full_sector("Foreven", canon=canon, canon_mode="pin")
```

That adds the Avalar Consulate's 27 named worlds and its capital; the Tlesho
Union, four systems of a xenophobic minor race who reverse-engineered jump
drive from a ship they seized; eleven native sophont homeworlds and Ancients
sites; ten scattered settlements of Droyne, Chirpers, Aslan, Vargr and
stranded humans; the fourteen barren worlds of the subsector J anomaly,
where colonies fail and ships disappear; the Zhodani route waypoints and the
Imperial Navy's cage around Andor and Candory; five Zhodani Red Zones; and
the Tech Level ceilings of both Consulates. Every entry carries its page
citation. None of it is canon — the Guide says so twice — so it layers on
as an option, and `seed` mode gives the worlds straight back.

Looking for one particular kind of world in a sector of hundreds:

```python
match = wm.make_erith(sector, culture_family="terrestrial")
print(match.body.uwp)                    # C867871-1
print(wm.describe_nations(match.body))   # its sovereign states
```

`find_worlds` scores every body — secondary worlds included — against a
`WorldProfile` of hard filters and weighted UWP targets. `make_erith` runs
the whole workflow: find the closest Earth-like world in the habitable zone
of an F, G or K star outside Zhodani space, make it match exactly, rebuild
its nations and record the family that holds the freehold.


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

**Societies beyond the mainworld** — secondary world populations, capped
below the mainworld's and restricted by what a Tech Level can survive;
colonies and independent settlements with their own government, law and
technology. On a balkanised world, the sovereign nations the UWP hides,
each with its own law level, technology, culture, territory and cities —
because a world's single Law Level digit only ever described the
government nearest the starport.

**Cultural character** — the handbook's eight traits rolled procedurally by
default, plus an opt-in palette of 50 templates: 16 terrestrial historical
periods, 11 starfaring, and 23 with no terrestrial parallel at all, from
hive collectives and distributed minds to nomad fleets, clade lineages and
worlds where the dead remain legal persons.

**Sectors** — system placement at configurable density; settlement waves;
native sophonts generated from the SCG's D66 tables; procedural polities that
expand from a capital along jump links bounded by their drive technology;
travel zones; trade routes; per-polity courier networks; subsector naming.

**Universes** — a guided entry point that turns a handful of high-level
choices (theme, star density, maximum Tech Level, trajectory, sophont
prevalence, polity count) into generation parameters, with anomalies —
rifts, clusters, supernova-sterilised regions, barren zones, plagues,
tech-suppressed regions and war-wrecked worlds — that reshape the sector
they cover, plus a rough timeline.

**Published sectors** — an overlay that honours what a source has already
established and generates the rest: star positions, polity borders, world
profiles, bases, travel zones, stellar types, native species, Tech Level
ceilings and worlds a source declares barren, each carrying its citation.
Foreven ships in two tiers — the reserve documentation's seven worlds, and
the *Sector Construction Guide*'s complete worked treatment of the sector.

**Maps** — sector and subsector maps in the Classic Traveller idiom: black ink
on cream, flat-topped hexes, starport class letters, solid discs for worlds
with water and open circles for dry ones, belt scatters, gas giant markers,
base glyphs, travel-zone rings, dashed polity borders, Xboat route lines,
subsector divisions and a legend. Also icosahedral world surface maps.

**Notability** — a scan that reads a whole sector and surfaces the places
that would change what happens at the table: native sophonts, the ruins of
extinct ones, magma oceans, tidally locked worlds, interdictions, dead
stars, and habitable worlds nobody has settled — each with the reasons it
was flagged.

**Planets** — a spherical terrain model for any generated world, and from the
one model both a foldable polyhedral net and photorealistic views from orbit.

## Planets and globes

`planet.py` builds terrain as 3D noise sampled on the unit sphere, so it wraps
seamlessly in longitude with no polar pinching. The world's own generated
characteristics drive it: hydrographics sets sea level, mean temperature and
axial tilt set the climate bands, tectonic plate count sets the continent
scale, biomass sets the vegetation, atmospheric pressure sets the cloud deck.

```python
import worldmaker as wm

sector = wm.generate_full_sector(name="Foreven Reach")

# The most Terra-like world in the sector, scored against Terra's own profile
hex_coord, world, score = wm.find_earthlike_candidate(sector)

# Surface model, both nets and three orbital views, written to disk
wm.render_planet_package(world, out_dir="planet")
```

The package writes an equirectangular texture, three orbital views, an
icosahedral net (the World Builder's Handbook standard, p.135) and a
dodecahedral net. Either net folds into the world: every face is drawn as a
true gnomonic projection and laid beside the faces that really adjoin it on
the sphere, so terrain runs continuously across each fold line.

For a single product rather than the whole set:

```python
surface = wm.generate_planet_surface(world, width=2048, height=1024)
image = wm.render_orbital_view(surface, size=1024, altitude_radii=3.2)
svg = wm.render_dodecahedral_net(surface, name=world.name)
```

`render_orbital_view` shades the terrain with a Lambertian model, softens the
day/night terminator, adds specular sun-glint on open water, a cloud deck,
city lights on the night side of a populated world, a Rayleigh-scattered limb
and a starfield, then tone-maps the result.

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
| `planet.py` | Spherical terrain, polyhedral nets, orbital rendering |
| `sophont.py` | Major races and the SCG sophont design tables |
| `polity.py` | Procedural polities, travel zones, bases |
| `scenarios.py` | Season, latitude, time of day, twilight and altitude temperatures |
| `special.py` | Special Circumstances: empty hexes, dead stars, protostars |
| `universe.py` | Guided universe creation, anomalies and timelines |
| `canon.py` | Canonical sector overlays: published positions, borders and worlds, and the Guide's worked Foreven |
| `secondary.py` | Secondary world populations |
| `nations.py` | Sovereign nations on balkanised worlds |
| `cultures.py` | Procedural cultures and the template palette |
| `findworld.py` | Weighted world matching, and the Erith workflow |
| `notable.py` | Surfacing the worlds worth a Referee's attention |
| `sector.py` | Sector assembly and the classic map renderers |
| `t5.py` | Traveller5 Second Survey column and tab output |
| `exporters.py` | DataFrame, markdown dossier and `.sec` output |

The notebooks are generated rather than hand-edited as JSON:
`build_explorer_nb.py` builds the Sector Explorer from source, and
`colab_cells.py` inserts the Colab badge, the bootstrap cell and the
download cell into all three. Both are idempotent — re-run them after
changing a notebook's structure.

## Fidelity

`AUDIT.md` records what is implemented against each chapter of both books,
what remains unimplemented, and where the code approximates a table the
source leaves ambiguous. The test suite checks conformance to the procedures
and their invariants — value ranges, dice distributions and derived-quantity
consistency — rather than transcribing every table entry; the temperature
model is validated against the book's own Terra benchmark.

Traveller is a trademark of Far Future Enterprises. The reference PDFs in
`documents/` are the owner's own copies and are not redistributable.
