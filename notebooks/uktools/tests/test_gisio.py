import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import LineString, MultiPolygon, Point, Polygon

from uktools import gisio
from uktools.crs import CRSError


def _round_trip(gdf, tmp_path, name):
    base = gisio.to_shapefile(gdf, tmp_path / name)
    return gisio.read_shapefile(base)


def test_line_round_trip_with_attributes(tmp_path):
    gdf = gpd.GeoDataFrame(
        {"flow": [1234.5, 87.25], "name": ["M6", "A38"], "lanes": [3, 2]},
        geometry=[LineString([(400000, 300000), (401000, 301000)]),
                  LineString([(402000, 300500), (402500, 300900)])],
        crs=27700)
    back = _round_trip(gdf, tmp_path, "links")
    assert len(back) == 2
    assert list(back["name"]) == ["M6", "A38"]
    assert back["flow"].tolist() == pytest.approx([1234.5, 87.25])
    assert back["lanes"].tolist() == [3, 2]
    assert back.geometry[0].equals_exact(gdf.geometry[0], tolerance=1e-6)
    assert back.crs is not None and back.crs.to_epsg() == 27700


def test_point_and_polygon_with_hole(tmp_path):
    pts = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(-1.89, 52.49)], crs=4326)
    back = _round_trip(pts, tmp_path, "pts")
    assert back.geometry[0].equals_exact(pts.geometry[0], tolerance=1e-9)
    assert back.crs.to_epsg() == 4326

    shell = [(0, 0), (10, 0), (10, 10), (0, 10)]
    hole = [(4, 4), (6, 4), (6, 6), (4, 6)]
    poly = gpd.GeoDataFrame({"zone": ["a"]},
                            geometry=[Polygon(shell, [hole])], crs=27700)
    back = _round_trip(poly, tmp_path, "zones")
    assert back.geometry[0].geom_type in ("Polygon", "MultiPolygon")
    g = back.geometry[0]
    if isinstance(g, MultiPolygon):
        g = g.geoms[0]
    assert g.area == pytest.approx(poly.geometry[0].area)  # hole preserved
    assert len(g.interiors) == 1


def test_field_name_truncation_dedup(tmp_path):
    gdf = gpd.GeoDataFrame(
        {"capacity_ab": [100.0], "capacity_ba": [200.0]},
        geometry=[Point(0, 0)], crs=27700)
    back = _round_trip(gdf, tmp_path, "dedup")
    vals = sorted(v for c in back.columns if c != "geometry"
                  for v in [back[c].iloc[0]])
    assert vals == [100.0, 200.0]  # both columns survived under distinct names


def test_mixed_geometry_refused(tmp_path):
    gdf = gpd.GeoDataFrame({"id": [1, 2]},
                           geometry=[Point(0, 0), LineString([(0, 0), (1, 1)])],
                           crs=27700)
    with pytest.raises(TypeError, match="one geometry family"):
        gisio.to_shapefile(gdf, tmp_path / "mixed")


def test_crsless_refused_and_assume_crs(tmp_path):
    gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(0, 0)])
    with pytest.raises(CRSError):
        gisio.to_shapefile(gdf, tmp_path / "nocrs")
    base = gisio.to_shapefile(gdf, tmp_path / "nocrs", assume_crs=27700)
    assert gisio.read_shapefile(base).crs.to_epsg() == 27700


def test_nan_and_none_records(tmp_path):
    gdf = gpd.GeoDataFrame(
        {"v": [1.5, np.nan], "s": ["x", None]},
        geometry=[Point(0, 0), Point(1, 1)], crs=27700)
    back = _round_trip(gdf, tmp_path, "nulls")
    assert back["v"].iloc[0] == pytest.approx(1.5)
    assert pd.isna(back["v"].iloc[1]) or back["v"].iloc[1] in (None, "")
