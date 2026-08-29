import numpy as np
import pyproj
import pytest

from uktools import bng

# GB-spanning probe points: Cornwall, Birmingham, London, Snowdonia,
# Edinburgh, far-north Scotland
POINTS = [(-5.54, 50.12), (-1.8904, 52.4862), (-0.1276, 51.5072),
          (-4.08, 53.07), (-3.19, 55.95), (-3.10, 58.64)]


def _pipeline_same_route():
    """pyproj forced onto the identical Helmert+TM route (no OSTN15 grid)."""
    return pyproj.Transformer.from_pipeline(
        "+proj=pipeline "
        "+step +proj=unitconvert +xy_in=deg +xy_out=rad "
        "+step +proj=cart +ellps=WGS84 "
        "+step +proj=helmert +x=-446.448 +y=125.157 +z=-542.060 "
        "+rx=-0.1502 +ry=-0.2470 +rz=-0.8421 +s=20.4894 "
        "+convention=position_vector "
        "+step +inv +proj=cart +ellps=airy "
        "+step +proj=tmerc +lat_0=49 +lon_0=-2 +k=0.9996012717 "
        "+x_0=400000 +y_0=-100000 +ellps=airy")


def test_ab_against_pyproj_same_route_millimetres():
    t = _pipeline_same_route()
    for lon, lat in POINTS:
        e_ref, n_ref = t.transform(lon, lat)
        e, n = bng.wgs84_to_bng(lon, lat)
        assert e == pytest.approx(e_ref, abs=1e-3)
        assert n == pytest.approx(n_ref, abs=1e-3)


def test_ab_against_pyproj_default_route_metres():
    # pyproj's default 4326->27700 may use the OSTN15 grid if installed;
    # Helmert is documented as within a few metres of it anywhere in GB
    t = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:27700", always_xy=True)
    for lon, lat in POINTS:
        e_ref, n_ref = t.transform(lon, lat)
        e, n = bng.wgs84_to_bng(lon, lat)
        assert abs(e - e_ref) < 5.0 and abs(n - n_ref) < 5.0


def test_tm_core_against_pyproj_osgb36_geographic():
    # EPSG:4277 (OSGB36 geographic) -> 27700 is the projection alone: the
    # TM math must match pyproj to a tenth of a millimetre
    t = pyproj.Transformer.from_crs("EPSG:4277", "EPSG:27700", always_xy=True)
    for lon36, lat36 in [(-1.9, 52.5), (1.717921583, 52.657570306)]:
        e_ref, n_ref = t.transform(lon36, lat36)
        e, n = bng._tm_forward(np.radians(lon36), np.radians(lat36), bng._AIRY)
        assert float(e) == pytest.approx(e_ref, abs=1e-4)
        assert float(n) == pytest.approx(n_ref, abs=1e-4)


def test_round_trip():
    for lon, lat in POINTS:
        e, n = bng.wgs84_to_bng(lon, lat)
        lon2, lat2 = bng.bng_to_wgs84(e, n)
        # the reversed-parameter Helmert inverse is ~3 mm from the true
        # inverse; 1e-7 deg is ~1 cm
        assert lon2 == pytest.approx(lon, abs=1e-7)
        assert lat2 == pytest.approx(lat, abs=1e-7)


def test_vectorized_and_scalar_forms_agree():
    lons = np.array([p[0] for p in POINTS])
    lats = np.array([p[1] for p in POINTS])
    e_arr, n_arr = bng.wgs84_to_bng(lons, lats)
    assert isinstance(e_arr, np.ndarray) and e_arr.shape == lons.shape
    for i, (lon, lat) in enumerate(POINTS):
        e, n = bng.wgs84_to_bng(lon, lat)
        assert isinstance(e, float)
        assert e == pytest.approx(e_arr[i], abs=1e-9)
        assert n == pytest.approx(n_arr[i], abs=1e-9)
