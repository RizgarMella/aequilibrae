import geopandas as gpd
import pyproj
import pytest
from shapely.geometry import LineString, Point

from uktools import crs


def test_bbox_around_metric_truth():
    lon, lat = -1.8904, 52.4862  # Birmingham
    b = crs.bbox_around(lon, lat, 30)
    assert b[2] - b[0] == pytest.approx(60_000, rel=1e-9)
    assert b[3] - b[1] == pytest.approx(60_000, rel=1e-9)
    # west and east edge midpoints are ~60 km apart by true geodesy
    t = pyproj.Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True)
    w = t.transform(b[0], (b[1] + b[3]) / 2)
    e = t.transform(b[2], (b[1] + b[3]) / 2)
    _, _, d = pyproj.Geod(ellps="WGS84").inv(*w, *e)
    assert d == pytest.approx(60_000, rel=1e-3)   # 0.1% of Geod truth


def test_normalize_bbox_both_branches():
    lonlat = (-2.35, 52.2, -1.43, 52.75)
    m = crs.normalize_bbox(lonlat)
    assert m[0] > 100_000 and m[3] > 200_000            # metres now
    same = crs.normalize_bbox(m)
    assert same == pytest.approx(m)                      # metres pass through


def test_ensure_crs_refusal_names_assume_crs():
    g = gpd.GeoDataFrame(geometry=[Point(0, 0)])
    with pytest.raises(crs.CRSError, match="assume_crs"):
        crs.ensure_crs(g, context="test layer")
    tagged = crs.ensure_crs(g, assume_crs=27700)
    assert tagged.crs.to_epsg() == 27700


def test_to_working_from_4326_and_noop():
    g4326 = gpd.GeoDataFrame(geometry=[Point(-1.89, 52.49)], crs=4326)
    w = crs.to_working(g4326)
    assert w.crs.to_epsg() == 27700
    assert w.geometry.iloc[0].x == pytest.approx(407_000, abs=2_000)
    assert crs.to_working(w) is w                        # no copy when already working


def test_lengths_in_true_metres():
    g = gpd.GeoDataFrame(geometry=[LineString([(-1.9, 52.0), (-1.9, 52.0 + 1/111.0)])], crs=4326)
    assert crs.lengths_m(g).iloc[0] == pytest.approx(1000, rel=0.01)


def test_layer_bounds_wgs84_roundtrip():
    g = gpd.GeoDataFrame(geometry=[Point(-1.89, 52.49), Point(-1.5, 52.6)], crs=4326)
    w = crs.to_working(g)
    b = crs.layer_bounds_wgs84(w)
    assert b[0] == pytest.approx(-1.89, abs=3e-3) and b[3] == pytest.approx(52.6, abs=3e-3)
    assert crs.layer_bounds_wgs84(g.iloc[0:0]) is None   # empty layer
