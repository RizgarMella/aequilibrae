# AequilibraE transport-modeling notebooks

A complete, hands-on transport modeling course built on AequilibraE's bundled example
models, with interactive [JupyterGIS](https://jupytergis.readthedocs.io) maps.

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
| 11 | [UK national model](11_uk_national_model.ipynb) | A national model of Great Britain from the real strategic road network (64,000 links, embedded in [`data/`](data)): city zones, national skims, gravity demand, equilibrium flows, busiest corridors and the England–Scotland screenline |

## Setup

These notebooks need **this fork** of AequilibraE — do not `pip install aequilibrae`
from PyPI, which is the upstream package and still requires the native SpatiaLite
library. Install a prebuilt wheel from the fork's
[release page](https://github.com/RizgarMella/aequilibrae/releases/tag/v1.7.0-pip-only)
(Windows/Linux, Python 3.11–3.13):

```bash
pip install <downloaded-aequilibrae-wheel> jupytergis jupyterlab matplotlib
jupyter lab
```

or build from source (needs a C++ compiler):

```bash
pip install "aequilibrae @ git+https://github.com/RizgarMella/aequilibrae.git@remove-native-spatialite" jupytergis jupyterlab matplotlib
```

That is the entire setup: this fork's spatial database engine is pure Python
(shapely + pyproj + SQLite's built-in R*Tree), so no native SpatiaLite package or
download is required on any platform.

The interactive maps render inside **JupyterLab** (the JupyterGIS extension installs
with the `jupytergis` wheel). Each map is a live document: use the layer tree to
toggle layers, edit symbology, or export to QGIS with `doc.export_to_qgis(...)`.

All notebooks are self-contained, run top-to-bottom in a few minutes each, and write
only to a throw-away temporary folder.

The notebooks mirror the worked examples in the
[AequilibraE documentation](https://www.aequilibrae.com) — refer there for deeper
background on each modeling stage.
