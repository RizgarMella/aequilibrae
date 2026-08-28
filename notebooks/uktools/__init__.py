"""uktools - offline maps, cartographic standards and UK geography helpers
for the AequilibraE notebook course.

    from uktools import *

gives notebooks the whole analyst toolkit while keeping model logic, data
management and styling in separate modules:

- uktools.style : STYLE standards, field()/constant() symbology, canned builders
- uktools.maps  : MapDoc, new_map/add_gdf, layer toggles, sidecar, side_by_side
- uktools.progress : progress_box scrolling live-log panel
- uktools.report : summary_card unified one-page summaries
- uktools.uk    : data loaders, city/district lookups, screenlines, focus maps
"""
from .style import (STYLE, field, constant, flow_style, congestion_style,
                    diff_style, class_style)
from .maps import MapDoc, new_map, add_gdf, side_by_side, merge_lines
from .progress import progress_box
from .report import summary_card
from .uk import (SCREENLINES, load_roads, load_roads_geojson, load_zones,
                 load_cities, load_boundary, city, city_bbox, district,
                 district_bbox, screenline, crossings, corridor, focus_map,
                 add_underlay, compare_links, near, edit_links, close_direction, save_run, save_select_link_run)

__all__ = [
    "STYLE", "field", "constant", "flow_style", "congestion_style",
    "diff_style", "class_style",
    "MapDoc", "new_map", "add_gdf", "side_by_side", "merge_lines",
    "progress_box", "summary_card",
    "SCREENLINES", "load_roads", "load_roads_geojson", "load_zones",
    "load_cities", "load_boundary", "city", "city_bbox", "district",
    "district_bbox", "screenline", "crossings", "corridor", "focus_map",
    "add_underlay", "compare_links", "near", "edit_links", "close_direction", "save_run", "save_select_link_run",
]
