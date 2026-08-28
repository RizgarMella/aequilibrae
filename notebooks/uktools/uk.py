"""uktools.uk - Great Britain data management and geography helpers.

Everything UK-specific and non-changing lives here: loaders for the embedded
open datasets (roads, districts, cities, boundary), geography lookups
(city/district centres and bounding boxes), named screenlines and corridor
selection - so notebook cells hold model logic only.

All loaders read from the `data/` folder next to the notebooks and cache in
memory; nothing is downloaded.
"""
import gzip
import json
from functools import lru_cache
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString, shape

from .maps import MapDoc, add_gdf, merge_lines
from .style import STYLE, constant

DATA = Path("data")

#: named national screenlines (lon/lat polylines) - extend freely
SCREENLINES = {
    "England-Scotland border": [(-3.6, 54.98), (-1.8, 55.82)],
    "England-Wales border": [(-3.15, 53.35), (-2.62, 51.58)],
}

#: approximate km per degree at GB latitudes
KM_PER_DEG_LAT = 111.0
KM_PER_DEG_LON = 65.0


# --- loaders (cached) -------------------------------------------------------
@lru_cache(maxsize=None)
def load_roads(detail="dense"):
    """GB road network as a GeoDataFrame (cls, ref, geometry).

    detail: "dense" (motorway+trunk+primary+secondary, 195k links),
            "detailed" (no secondary, 141k), "strategic" (64k).
    """
    name = {"dense": "uk_roads_dense", "detailed": "uk_roads_detailed",
            "strategic": "uk_strategic_roads"}[detail]
    with gzip.open(DATA / f"{name}.geojson.gz", "rt", encoding="utf-8") as fh:
        gj = json.load(fh)
    return gpd.GeoDataFrame(
        [{"cls": f["properties"]["class"], "ref": f["properties"]["ref"]} for f in gj["features"]],
        geometry=[shape(f["geometry"]) for f in gj["features"]], crs=4326)


@lru_cache(maxsize=None)
def load_roads_geojson(detail="dense"):
    """The raw GeoJSON dict (for feeding links straight into a model build)."""
    name = {"dense": "uk_roads_dense", "detailed": "uk_roads_detailed",
            "strategic": "uk_strategic_roads"}[detail]
    with gzip.open(DATA / f"{name}.geojson.gz", "rt", encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache(maxsize=None)
def load_zones():
    """All GB local-authority districts: name, code, population, geometry."""
    with gzip.open(DATA / "gb_lad_zones.geojson.gz", "rt", encoding="utf-8") as fh:
        gj = json.load(fh)
    z = gpd.GeoDataFrame([f["properties"] for f in gj["features"]],
                         geometry=[shape(f["geometry"]) for f in gj["features"]], crs=4326)
    z["centroid"] = z.geometry.representative_point()
    z["area_km2"] = z.to_crs(27700).area / 1e6
    z["density"] = (z.population / z.area_km2).round(0)
    return z


@lru_cache(maxsize=None)
def load_cities():
    """The 75 largest cities and strategic towns: city, lat, lon, population."""
    return pd.read_csv(DATA / "uk_cities.csv")


@lru_cache(maxsize=None)
def load_boundary():
    """Simplified GB outline."""
    gj = json.load(open(DATA / "gb_boundary.geojson", encoding="utf-8"))
    return gpd.GeoDataFrame(geometry=[shape(f["geometry"]) for f in gj["features"]], crs=4326)


# --- geography lookups ------------------------------------------------------
def city(name):
    """(lon, lat) of a city from the embedded table (case-insensitive)."""
    c = load_cities()
    row = c[c.city.str.lower() == name.lower()]
    if row.empty:
        raise KeyError(f"unknown city {name!r} - see load_cities().city")
    return float(row.lon.iloc[0]), float(row.lat.iloc[0])


def city_bbox(name, km=30):
    """(minx, miny, maxx, maxy) box of +-km around a city centre."""
    lon, lat = city(name)
    dy, dx = km / KM_PER_DEG_LAT, km / KM_PER_DEG_LON
    return (lon - dx, lat - dy, lon + dx, lat + dy)


def district(name):
    """The LAD zone row for a district (case-insensitive)."""
    z = load_zones()
    row = z[z.name.str.lower() == name.lower()]
    if row.empty:
        raise KeyError(f"unknown district {name!r} - see load_zones().name")
    return row.iloc[0]


def district_bbox(name, pad_km=5):
    """Bounding box of a district, padded by pad_km."""
    b = district(name).geometry.bounds
    dy, dx = pad_km / KM_PER_DEG_LAT, pad_km / KM_PER_DEG_LON
    return (b[0] - dx, b[1] - dy, b[2] + dx, b[3] + dy)


def screenline(name):
    """A named screenline as a shapely LineString (see SCREENLINES)."""
    return LineString(SCREENLINES[name])


def crossings(loaded_gdf, name, flow_col="matrix_tot"):
    """Links crossing a named screenline, with total flow."""
    line = screenline(name)
    hit = loaded_gdf[loaded_gdf.geometry.intersects(line)]
    return hit, float(hit[flow_col].sum()) if len(hit) else 0.0


def corridor(gdf, ref):
    """All links of one road (by ref/name column), e.g. corridor(loaded, "M6")."""
    col = "ref" if "ref" in gdf.columns else "name"
    return gdf[gdf[col].astype(str).str.fullmatch(str(ref), case=False)]


# --- ready-made map setups --------------------------------------------------
def focus_map(where, km=30, height=None):
    """A map clipped to a city (by name), district ("district:Name"), or an
    explicit (minx, miny, maxx, maxy) bbox - the cure for cramped national
    views: every layer added afterwards is clipped to the window."""
    if isinstance(where, str):
        bbox = (district_bbox(where.split(":", 1)[1]) if where.lower().startswith("district:")
                else city_bbox(where, km))
    else:
        bbox = tuple(where)
    return MapDoc(bbox=bbox, height=height)


#: frame of the pre-rendered GB basemap image (minx, miny, maxx, maxy)
BASEMAP_BOUNDS = (-8.2, 49.8, 2.0, 58.8)


def add_underlay(doc, roads_gdf=None, boundary=False, basemap=True):
    """The UK under-map: geographic context beneath the model layers.

    basemap=True (default) draws the pre-rendered offline GB base
    (data/gb_basemap.png - land, sea, built-up areas, water, the strategic
    road skeleton and city labels; fully embedded, no tiles, no CDN).
    boundary=True adds the plain GB outline instead/on top; roads_gdf adds a
    faint merged backdrop of a network you pass in."""
    if basemap:
        import base64
        img = (DATA / "gb_basemap.png").read_bytes()
        doc.add_bitmap("data:image/png;base64," + base64.b64encode(img).decode(),
                       BASEMAP_BOUNDS, name="GB basemap")
    if boundary:
        add_gdf(doc, load_boundary(), "Great Britain", opacity=0.2,
                symbology=[[constant(STYLE["boundary_fill"]).encoding("fill")]])
    if roads_gdf is not None:
        add_gdf(doc, merge_lines(roads_gdf, tol=0.01), "network", opacity=0.3,
                symbology=[[constant(STYLE["backdrop_line"]).encoding("stroke")]])
    return doc


def compare_links(base_gdf, scen_gdf, col, key="link_id", min_abs=0.0):
    """Difference any link attribute between two runs or networks - capacity,
    speed, flow, travel time. Returns geometry + <col>_base, <col>_scen and
    `delta` (scenario minus base), ready for a diff_style() map:

        cap = compare_links(links_base, links_scen, "capacity_ab")
        add_gdf(doc, cap, "capacity change", symbology=diff_style("delta", cap.delta.abs().max()))
    """
    a = base_gdf[[key, col, "geometry"]].rename(columns={col: f"{col}_base"})
    b = scen_gdf[[key, col, "geometry"]].rename(columns={col: f"{col}_scen"})
    m = a.merge(b.drop(columns="geometry"), on=key, how="outer")
    only_scen = m.geometry.isna()
    if only_scen.any():
        m.loc[only_scen, "geometry"] = b.set_index(key).geometry.reindex(m.loc[only_scen, key]).values
    for c in (f"{col}_base", f"{col}_scen"):
        m[c] = m[c].fillna(0.0)
    m["delta"] = (m[f"{col}_scen"] - m[f"{col}_base"]).round(2)
    m = gpd.GeoDataFrame(m, geometry="geometry", crs=base_gdf.crs)
    return m[m.delta.abs() >= min_abs].copy()


def near(gdf, where, km=None, miles=None):
    """Geometric selection: rows whose centre lies within a radius of a place.

    where: a city name ("London"), a (lon, lat) pair, or any shapely geometry.
    Radius in km= or miles=. Chain with attribute filters freely:

        near(links, "London", miles=3).query("link_type == 'motorway'")
    """
    from shapely.geometry import Point
    r_km = float(km) if km is not None else (float(miles) * 1.60934 if miles is not None else None)
    if r_km is None:
        raise ValueError("give a radius: km=... or miles=...")
    if isinstance(where, str):
        where = Point(*city(where))
    elif isinstance(where, (tuple, list)):
        where = Point(*where)
    center = gpd.GeoSeries([where], crs=4326).to_crs(27700).iloc[0]
    d = gdf.geometry.representative_point().to_crs(27700).distance(center) if gdf.crs         else gpd.GeoSeries(gdf.geometry, crs=4326).representative_point().to_crs(27700).distance(center)
    return gdf[d <= r_km * 1000].copy()


def edit_links(project, links, *, speed=None, speed_factor=None,
               capacity=None, capacity_factor=None):
    """Surgically change selected links in the model database - speeds,
    capacities, or both - and refresh their travel times.

        m25 = near(links_gdf, "London", miles=3).query("link_type == 'motorway'")
        edit_links(project, m25, speed=40)          # set both directions to 40 km/h
        project.network.build_graphs(modes=["c"])   # rebuild before re-assigning

    links: a (Geo)DataFrame with a link_id column, or an iterable of ids.
    Absolute values win over factors if both are given. Returns the number of
    links changed.
    """
    ids = [int(v) for v in (links["link_id"] if hasattr(links, "columns") else links)]
    if not ids:
        return 0
    sets, args = [], []
    if speed is not None:
        sets += ["speed_ab = ?", "speed_ba = ?"]; args += [speed, speed]
    elif speed_factor is not None:
        sets += ["speed_ab = speed_ab * ?", "speed_ba = speed_ba * ?"]; args += [speed_factor, speed_factor]
    if capacity is not None:
        sets += ["capacity_ab = ?", "capacity_ba = ?"]; args += [capacity, capacity]
    elif capacity_factor is not None:
        sets += ["capacity_ab = capacity_ab * ?", "capacity_ba = capacity_ba * ?"]; args += [capacity_factor, capacity_factor]
    if not sets:
        raise ValueError("nothing to change - give speed(_factor) and/or capacity(_factor)")
    with project.db_connection as conn:
        conn.executemany(f"update links set {', '.join(sets)} where link_id = ?",
                         [tuple(args) + (i,) for i in ids])
        conn.executemany("update links set travel_time_ab = distance / 1000.0 / speed_ab * 60, "
                         "travel_time_ba = distance / 1000.0 / speed_ba * 60 where link_id = ?",
                         [(i,) for i in ids])
        conn.commit()
    return len(ids)


def close_direction(project, links, close="ab"):
    """Close ONE direction of the selected links.

    AequilibraE models one-way operation natively through the links table's
    `direction` field (0 = two-way, 1 = a->b only, -1 = b->a only), which the
    graph builder respects. Closing "ab" on a two-way link leaves it b->a
    only; closing the only remaining direction raises (for a full closure,
    drop the car mode or delete the link). Rebuild graphs afterwards:

        m6n = corridor(links_gdf, "M6")
        close_direction(project, m6n, close="ab")
        project.network.build_graphs(modes=["c"])

    The soft alternative - throttling rather than closing - is
    edit_links(..., capacity_factor=...) on the per-direction capacities.
    Returns the number of links changed.
    """
    if close not in ("ab", "ba"):
        raise ValueError("close must be 'ab' or 'ba'")
    ids = [int(v) for v in (links["link_id"] if hasattr(links, "columns") else links)]
    if not ids:
        return 0
    new_dir = -1 if close == "ab" else 1
    changed = 0
    with project.db_connection as conn:
        marks = ",".join("?" * len(ids))
        rows = conn.execute(f"select link_id, direction from links where link_id in ({marks})", ids).fetchall()
        for lid, cur in rows:
            if cur == new_dir:
                continue
            if cur != 0:
                raise ValueError(f"link {lid} is already one-way ({cur}); closing its only "
                                 "direction needs a full closure (drop car mode or delete)")
            conn.execute("update links set direction = ? where link_id = ?", (new_dir, lid))
            changed += 1
        conn.commit()
    return changed
