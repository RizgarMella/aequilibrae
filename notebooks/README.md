# AequilibraE transport-modeling notebooks

A complete, hands-on transport modeling course built on AequilibraE's bundled example
models, with interactive, fully offline WebGL maps (lonboard).

| # | Notebook | What you learn |
|---|----------|----------------|
| 01 | [Project & network](01_project_and_network.ipynb) | Project structure, links/nodes/zones as GeoDataFrames, first map |
| 02 | [Zones & connectors](02_zones_and_connectors.ipynb) | Hexagonal zoning, centroids, centroid connectors |
| 03 | [Paths & skimming](03_paths_and_skimming.ipynb) | Graphs, shortest paths, zone-to-zone skim matrices |
| 04 | [Trip distribution](04_trip_distribution.ipynb) | Gravity model calibration, deterrence functions, IPF |
| 05 | [Traffic assignment](05_traffic_assignment.ipynb) | BPR volume-delay, BFW equilibrium, congestion mapping |
| 06 | [Route choice](06_route_choice.ipynb) | BFSLE choice sets, path-size logit assignment |
| 07 | [Public transport](07_public_transport.ipynb) | GTFS import, transit database, route/stop mapping |
| 08 | [Full model workflow](08_full_model_workflow.ipynb) | Base/future years, select-link analysis, scenario comparison |
| 09 | [Full regional model](09_full_regional_model.ipynb) | Everything at once on the Coquimbo region: network prep, land-use trip generation, gravity + IPF, multi-class assignment with select link, congestion maps, route choice, GTFS |
| 10 | [Models at every scale](10_model_scales.ipynb) | From 76-link toys to 50,000-link synthetic metros: how every stage scales with link count, with timing charts and large-model flow maps |
| 11 | [UK national model](11_uk_national_model.ipynb) | A national model of Great Britain from the real strategic road network (64,000 links, embedded in [`data/`](data)): sectored city zones, calibrated gravity demand, equilibrium flows with separate flow and congestion map views, busiest corridors and the England–Scotland screenline |
| 12 | [UK in finer detail](12_uk_detailed_network.ipynb) | The same national model rebuilt on a 141,000-link network that adds every primary A-road in Great Britain (embedded in [`data/`](data)) — route competition, diversion and what network detail buys a model |
| 13 | [GB complete model](13_gb_complete_model.ipynb) | All out: every local-authority district as a zone (350, real ONS boundaries and populations), a 195,000-link four-class network, and the full showcase — choropleths, accessibility, desire lines, select-link, flow/congestion views, corridors, screenlines — with every assumption in one PARAMS cell |

## Setup

These notebooks need **this fork** of AequilibraE — do not `pip install aequilibrae`
from PyPI, which is the upstream package and still requires the native SpatiaLite
library. Install a prebuilt wheel from the fork's
[release page](https://github.com/RizgarMella/aequilibrae/releases/tag/v1.7.0.post1-pip-only)
(Windows/Linux, Python 3.11–3.14):

```bash
pip install <downloaded-aequilibrae-wheel> lonboard anywidget jupyterlab matplotlib
jupyter lab
```

or build from source (needs a C++ compiler):

```bash
pip install "aequilibrae @ git+https://github.com/RizgarMella/aequilibrae.git@remove-native-spatialite" lonboard anywidget jupyterlab matplotlib
```

**Locked-down networks** (CDNs such as unpkg.com blocked): if maps show only a
text repr, install the vendored JupyterLab frontend from this repo — see
[`vendor/README.md`](../vendor/README.md); everything the notebooks need then
comes from this repository alone.

That is the entire setup: this fork's spatial database engine is pure Python
(shapely + pyproj + SQLite's built-in R*Tree), so no native SpatiaLite package or
download is required on any platform.

The interactive maps render through **lonboard** - WebGL maps whose
frontend ships from the kernel via ipywidgets: no map server extensions and
no CDN. On networks that block CDNs, run
`python vendor/patch-lonboard-offline.py` once (see
[`INSTALL_WORKSTATION.md`](../INSTALL_WORKSTATION.md)). Set
`AEQ_MAP_BACKEND=static` for plain matplotlib rendering.

All notebooks are self-contained, run top-to-bottom in a few minutes each, and write
only to a throw-away temporary folder.

The notebooks mirror the worked examples in the
[AequilibraE documentation](https://www.aequilibrae.com) — refer there for deeper
background on each modeling stage.
