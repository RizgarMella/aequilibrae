"""uktools.crs - coordinate reference system primitives.

The working CRS for all UK analysis is British National Grid (EPSG:27700):
true metres across Great Britain, so buffers, bounding boxes, lengths and
areas mean what they say. Data files store EPSG:4326; loaders reproject on
read; the display layer (lonboard) accepts any CRS-tagged frame and
reprojects internally.

Rules:
- every GeoDataFrame entering a document is normalized to the working CRS
  at add-time (model frames arrive in 4326, loader frames in 27700 - both fine);
- CRS-less frames are refused with a clear error naming ``assume_crs=``;
- rasters are the one lon/lat-bounds citizen, and their pixels must be
  RENDERED in Web Mercator (EPSG:3857) because that is how deck.gl drapes
  bitmap layers.
"""
from functools import lru_cache

import geopandas as gpd
import pyproj
from shapely.geometry import Point

WORKING_CRS = 27700   # OSGB36 / British National Grid - metres
DISPLAY_CRS = 4326    # lonboard hand-off; it reprojects internally

#: lon/lat window that plausibly contains GB data - used only to
#: disambiguate bbox tuples (BNG coordinates are 0..700k / 0..1.3M, so the
#: numeric ranges are disjoint and the heuristic cannot misfire on GB data)
GB_LONLAT_ENVELOPE = (-9.5, 49.5, 3.5, 61.5)


class CRSError(ValueError):
    """A GeoDataFrame arrived without a usable CRS."""


@lru_cache(maxsize=None)
def _tf(src: str, dst: str) -> pyproj.Transformer:
    return pyproj.Transformer.from_crs(src, dst, always_xy=True)


def ensure_crs(gdf, assume_crs=None, *, context="layer"):
    """Return gdf guaranteed to carry a CRS, or raise CRSError.

    assume_crs (e.g. 27700 or 4326) tags a CRS-less frame instead of raising.
    """
    if gdf.crs is not None:
        return gdf
    if assume_crs is not None:
        return gdf.set_crs(assume_crs)
    raise CRSError(
        f"{context} has no CRS. Tag it first (gdf = gdf.set_crs(27700) or 4326) "
        f"or pass assume_crs=27700 / assume_crs=4326 so it can be interpreted.")


def to_working(gdf, assume_crs=None, *, context="layer"):
    """gdf in the working CRS (EPSG:27700); no copy if already there."""
    gdf = ensure_crs(gdf, assume_crs, context=context)
    if gdf.crs.to_epsg() == WORKING_CRS:
        return gdf
    return gdf.to_crs(WORKING_CRS)


def bbox_is_lonlat(bounds) -> bool:
    """Heuristic: does a 4-tuple look like lon/lat (vs BNG metres)?"""
    minx, miny, maxx, maxy = bounds
    e = GB_LONLAT_ENVELOPE
    return (e[0] <= minx <= e[2] and e[0] <= maxx <= e[2]
            and e[1] <= miny <= e[3] and e[1] <= maxy <= e[3])


def transform_bounds(bounds, src, dst):
    """Reproject a (minx, miny, maxx, maxy) box, densified along the edges."""
    t = _tf(f"EPSG:{src}" if isinstance(src, int) else str(src),
            f"EPSG:{dst}" if isinstance(dst, int) else str(dst))
    return t.transform_bounds(*bounds)


def normalize_bbox(bounds):
    """Any GB bbox (lon/lat or BNG metres) -> BNG metres."""
    bounds = tuple(float(v) for v in bounds)
    if bbox_is_lonlat(bounds):
        return transform_bounds(bounds, 4326, WORKING_CRS)
    return bounds


def point27700(lon, lat) -> Point:
    """A lon/lat position as a working-CRS point."""
    x, y = _tf("EPSG:4326", f"EPSG:{WORKING_CRS}").transform(lon, lat)
    return Point(x, y)


def bbox_around(lon, lat, km) -> tuple:
    """A true-metre square of +-km around a lon/lat centre, in BNG."""
    p = point27700(lon, lat)
    m = float(km) * 1000.0
    return (p.x - m, p.y - m, p.x + m, p.y + m)


def pad_bbox(bounds27700, pad_km) -> tuple:
    """Pad a BNG bbox by pad_km on every side."""
    m = float(pad_km) * 1000.0
    minx, miny, maxx, maxy = bounds27700
    return (minx - m, miny - m, maxx + m, maxy + m)


def layer_bounds_wgs84(gdf) -> tuple | None:
    """(minx, miny, maxx, maxy) of a layer in lon/lat, for Map.fly_to."""
    if gdf is None or not len(gdf):
        return None
    b = gdf.total_bounds
    epsg = gdf.crs.to_epsg() if gdf.crs else None
    if epsg == 4326 or epsg is None:
        return tuple(float(v) for v in b)
    return transform_bounds(tuple(b), epsg, 4326)


def lengths_m(gdf, assume_crs=None):
    """Per-feature lengths in metres (computed in the working CRS)."""
    return to_working(gdf, assume_crs).geometry.length


def areas_km2(gdf, assume_crs=None):
    """Per-feature areas in km^2 (computed in the working CRS)."""
    return to_working(gdf, assume_crs).geometry.area / 1e6
