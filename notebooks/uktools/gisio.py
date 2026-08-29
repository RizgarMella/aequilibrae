"""uktools.gisio - shapefile interchange without GDAL.

geopandas' own ``read_file``/``to_file`` need a compiled I/O engine
(pyogrio or fiona). This module writes and reads ESRI shapefiles with the
embedded pure-Python pyshp (``uktools._vendor.shapefile``) instead, so model
outputs travel to QGIS/ArcGIS - and shapefiles come back in - on any
machine that can run the notebooks at all.

    to_shapefile(loaded, "outputs/loaded_links")     # .shp/.shx/.dbf/.prj
    gdf = read_shapefile("outputs/loaded_links")

Shapefile format limits are handled, not hidden: field names are truncated
to 10 bytes (deduplicated), text is capped at 254 bytes, and datetimes are
written as ISO text.
"""
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import (LineString, MultiLineString, MultiPoint,
                              MultiPolygon, Point, Polygon)
from shapely.geometry.polygon import orient

from . import crs as _crs
from ._vendor import shapefile as _shp

_SHAPE_TYPE = {
    "Point": _shp.POINT, "MultiPoint": _shp.MULTIPOINT,
    "LineString": _shp.POLYLINE, "MultiLineString": _shp.POLYLINE,
    "Polygon": _shp.POLYGON, "MultiPolygon": _shp.POLYGON,
}


def _dedup_names(columns):
    """Shapefile DBF field names: max 10 chars, unique. 'capacity_ab' and
    'capacity_ba' must not silently collapse into one field."""
    out, seen = [], {}
    for col in columns:
        name = str(col)[:10]
        if name.lower() in seen:
            seen[name.lower()] += 1
            suffix = f"_{seen[name.lower()]}"
            name = name[: 10 - len(suffix)] + suffix
        seen.setdefault(name.lower(), 0)
        out.append(name)
    return out


def _field_spec(series):
    """(type, size, decimal) DBF spec for a pandas column."""
    if pd.api.types.is_bool_dtype(series):
        return "L", 1, 0
    if pd.api.types.is_integer_dtype(series):
        return "N", 18, 0
    if pd.api.types.is_float_dtype(series):
        return "N", 24, 8
    if pd.api.types.is_datetime64_any_dtype(series):
        return "C", 25, 0
    width = int(series.astype(str).str.len().max() or 1)
    return "C", min(max(width, 1), 254), 0


def _rings(polygon):
    """Exterior ring clockwise, holes counter-clockwise (shapefile spec)."""
    p = orient(polygon, sign=-1.0)
    return [list(p.exterior.coords)] + [list(r.coords) for r in p.interiors]


def _write_geom(writer, geom):
    if geom is None or geom.is_empty:
        writer.null()
    elif isinstance(geom, Point):
        writer.point(geom.x, geom.y)
    elif isinstance(geom, MultiPoint):
        writer.multipoint([(p.x, p.y) for p in geom.geoms])
    elif isinstance(geom, LineString):
        writer.line([list(geom.coords)])
    elif isinstance(geom, MultiLineString):
        writer.line([list(g.coords) for g in geom.geoms])
    elif isinstance(geom, Polygon):
        writer.poly(_rings(geom))
    elif isinstance(geom, MultiPolygon):
        writer.poly([ring for g in geom.geoms for ring in _rings(g)])
    else:
        raise TypeError(f"cannot write {geom.geom_type} to a shapefile")


def to_shapefile(gdf, path, assume_crs=None):
    """Write a GeoDataFrame as an ESRI shapefile (.shp/.shx/.dbf/.prj).

    ``path`` is the base name (with or without ``.shp``). The CRS is carried
    into a ``.prj`` sidecar; CRS-less frames are refused unless
    ``assume_crs=`` says how to read them. Returns the base path written.
    """
    gdf = _crs.ensure_crs(gdf, assume_crs, context="to_shapefile() input")
    base = str(path)[:-4] if str(path).lower().endswith(".shp") else str(path)

    geom_types = set(gdf.geometry.geom_type.dropna())
    shape_types = {_SHAPE_TYPE[t] for t in geom_types if t in _SHAPE_TYPE}
    if unknown := geom_types - set(_SHAPE_TYPE):
        raise TypeError(f"unsupported geometry types for shapefile: {unknown}")
    if len(shape_types) > 1:
        raise TypeError(
            f"shapefiles hold one geometry family; this frame mixes {sorted(geom_types)}. "
            "Split it (e.g. gdf[gdf.geom_type == 'LineString']) and export each part.")
    shape_type = shape_types.pop() if shape_types else _shp.NULL

    attrs = gdf.drop(columns=gdf.geometry.name)
    names = _dedup_names(attrs.columns)

    with _shp.Writer(base, shapeType=shape_type) as w:
        specs = []
        for name, col in zip(names, attrs.columns):
            ftype, size, decimal = _field_spec(attrs[col])
            w.field(name, ftype, size, decimal)
            specs.append(ftype)
        if not names:  # DBF needs at least one field
            w.field("fid", "N", 18, 0)

        for i, (_, row) in enumerate(gdf.iterrows()):
            _write_geom(w, row[gdf.geometry.name])
            if names:
                values = []
                for col, ftype in zip(attrs.columns, specs):
                    v = row[col]
                    if pd.isna(v):
                        values.append("" if ftype == "C" else None)
                    elif ftype == "C" and not isinstance(v, str):
                        values.append(str(v))
                    else:
                        values.append(v)
                w.record(*values)
            else:
                w.record(i)

    with open(base + ".prj", "w", encoding="utf-8") as f:
        f.write(gdf.crs.to_wkt(version="WKT1_ESRI"))
    return base


def read_shapefile(path, crs=None):
    """Read an ESRI shapefile into a GeoDataFrame - no GDAL, no pyogrio.

    The CRS comes from the ``.prj`` sidecar when present; ``crs=`` overrides
    or supplies it. Reads only what pyshp reads: geometry + DBF attributes.
    """
    from shapely.geometry import shape as _shape

    base = str(path)[:-4] if str(path).lower().endswith(".shp") else str(path)
    with _shp.Reader(base) as r:
        fields = [f[0] for f in r.fields if f[0] != "DeletionFlag"]
        records, geoms = [], []
        for sr in r.iterShapeRecords():
            records.append([sr.record[f] for f in fields])
            gj = sr.shape.__geo_interface__
            geoms.append(None if gj is None else _shape(gj))

    if crs is None:
        try:
            with open(base + ".prj", encoding="utf-8") as f:
                crs = f.read().strip() or None
        except OSError:
            crs = None
    df = pd.DataFrame(records, columns=fields)
    return gpd.GeoDataFrame(df, geometry=geoms, crs=crs)
