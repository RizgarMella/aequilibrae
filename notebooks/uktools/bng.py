"""uktools.bng - WGS84 <-> British National Grid in pure Python.

A self-contained implementation of EPSG:4326 <-> EPSG:27700 following the
Ordnance Survey's "A guide to coordinate systems in Great Britain":
geodetic -> cartesian on WGS84, 7-parameter Helmert shift to OSGB36
(position-vector convention, OS/EPSG parameters), then the OSGB
Transverse Mercator projection on the Airy 1830 ellipsoid - and the exact
reverse. No pyproj, no grid files, no downloads.

Accuracy: the Helmert route is the OS-published approximation - within a
few metres of the definitive OSTN15 grid transformation anywhere in GB
(the tests A/B it against pyproj at millimetre agreement on the same
route). Use it for display, interchange and analysis at model scale; use
OSTN15 (pyproj + grids) if you ever need centimetre land-survey truth.

    e, n = wgs84_to_bng(-1.8904, 52.4862)      # scalars or arrays
    lon, lat = bng_to_wgs84(e, n)
"""
import numpy as np

# ellipsoids (semi-major, semi-minor, metres)
_AIRY = (6_377_563.396, 6_356_256.909)          # OSGB36
_WGS84 = (6_378_137.000, 6_356_752.3142)

# OSGB National Grid Transverse Mercator
_F0 = 0.9996012717                  # scale on the central meridian
_PHI0, _LAM0 = np.radians(49.0), np.radians(-2.0)
_E0, _N0 = 400_000.0, -100_000.0

# Helmert WGS84 -> OSGB36 (OS/EPSG values, position-vector convention)
_TX, _TY, _TZ = -446.448, 125.157, -542.060     # metres
_S = 20.4894e-6                                  # scale (ppm -> unitless)
_RX, _RY, _RZ = (np.radians(r / 3600.0) for r in (-0.1502, -0.2470, -0.8421))


def _ecc2(ell):
    a, b = ell
    return (a * a - b * b) / (a * a)


def _geodetic_to_cart(lon, lat, ell):
    a, _ = ell
    e2 = _ecc2(ell)
    sin_lat, cos_lat = np.sin(lat), np.cos(lat)
    nu = a / np.sqrt(1.0 - e2 * sin_lat**2)
    return (nu * cos_lat * np.cos(lon), nu * cos_lat * np.sin(lon),
            nu * (1.0 - e2) * sin_lat)


def _cart_to_geodetic(x, y, z, ell):
    a, _ = ell
    e2 = _ecc2(ell)
    lon = np.arctan2(y, x)
    p = np.hypot(x, y)
    lat = np.arctan2(z, p * (1.0 - e2))
    for _ in range(8):  # converges to sub-mm in 3-4 iterations
        nu = a / np.sqrt(1.0 - e2 * np.sin(lat) ** 2)
        lat = np.arctan2(z + e2 * nu * np.sin(lat), p)
    return lon, lat


def _helmert(x, y, z, sign):
    """sign=+1: WGS84 -> OSGB36; sign=-1: the standard reversed-parameter
    inverse (sub-millimetre from the true matrix inverse at these magnitudes)."""
    s = 1.0 + sign * _S
    rx, ry, rz = sign * _RX, sign * _RY, sign * _RZ
    return (sign * _TX + s * x - rz * y + ry * z,
            sign * _TY + rz * x + s * y - rx * z,
            sign * _TZ - ry * x + rx * y + s * z)


def _meridional_arc(lat, ell):
    a, b = ell
    n = (a - b) / (a + b)
    dp, sp = lat - _PHI0, lat + _PHI0
    return b * _F0 * (
        (1 + n + 1.25 * n**2 + 1.25 * n**3) * dp
        - (3 * n + 3 * n**2 + 2.625 * n**3) * np.sin(dp) * np.cos(sp)
        + (1.875 * n**2 + 1.875 * n**3) * np.sin(2 * dp) * np.cos(2 * sp)
        - (35.0 / 24.0) * n**3 * np.sin(3 * dp) * np.cos(3 * sp))


def _tm_forward(lon, lat, ell):
    """OSGB36 geodetic (radians) -> National Grid easting/northing."""
    a, _ = ell
    e2 = _ecc2(ell)
    sin_lat, cos_lat, tan_lat = np.sin(lat), np.cos(lat), np.tan(lat)
    nu = a * _F0 / np.sqrt(1.0 - e2 * sin_lat**2)
    rho = a * _F0 * (1.0 - e2) * (1.0 - e2 * sin_lat**2) ** -1.5
    eta2 = nu / rho - 1.0

    I = _meridional_arc(lat, ell) + _N0
    II = nu / 2.0 * sin_lat * cos_lat
    III = nu / 24.0 * sin_lat * cos_lat**3 * (5.0 - tan_lat**2 + 9.0 * eta2)
    IIIA = nu / 720.0 * sin_lat * cos_lat**5 * (61.0 - 58.0 * tan_lat**2 + tan_lat**4)
    IV = nu * cos_lat
    V = nu / 6.0 * cos_lat**3 * (nu / rho - tan_lat**2)
    VI = nu / 120.0 * cos_lat**5 * (
        5.0 - 18.0 * tan_lat**2 + tan_lat**4 + 14.0 * eta2 - 58.0 * tan_lat**2 * eta2)

    dl = lon - _LAM0
    n_ = I + II * dl**2 + III * dl**4 + IIIA * dl**6
    e_ = _E0 + IV * dl + V * dl**3 + VI * dl**5
    return e_, n_


def _tm_inverse(e_, n_, ell):
    """National Grid easting/northing -> OSGB36 geodetic (radians)."""
    a, _ = ell
    e2 = _ecc2(ell)

    lat = (np.asarray(n_, dtype=float) - _N0) / (a * _F0) + _PHI0
    for _ in range(10):
        m = _meridional_arc(lat, ell)
        delta = n_ - _N0 - m
        lat = lat + delta / (a * _F0)
        if np.max(np.abs(delta)) < 1e-8:  # 10 nm on the meridian
            break

    sin_lat, cos_lat, tan_lat = np.sin(lat), np.cos(lat), np.tan(lat)
    nu = a * _F0 / np.sqrt(1.0 - e2 * sin_lat**2)
    rho = a * _F0 * (1.0 - e2) * (1.0 - e2 * sin_lat**2) ** -1.5
    eta2 = nu / rho - 1.0

    VII = tan_lat / (2.0 * rho * nu)
    VIII = tan_lat / (24.0 * rho * nu**3) * (
        5.0 + 3.0 * tan_lat**2 + eta2 - 9.0 * tan_lat**2 * eta2)
    IX = tan_lat / (720.0 * rho * nu**5) * (61.0 + 90.0 * tan_lat**2 + 45.0 * tan_lat**4)
    X = 1.0 / (cos_lat * nu)
    XI = 1.0 / (cos_lat * 6.0 * nu**3) * (nu / rho + 2.0 * tan_lat**2)
    XII = 1.0 / (cos_lat * 120.0 * nu**5) * (5.0 + 28.0 * tan_lat**2 + 24.0 * tan_lat**4)
    XIIA = 1.0 / (cos_lat * 5040.0 * nu**7) * (
        61.0 + 662.0 * tan_lat**2 + 1320.0 * tan_lat**4 + 720.0 * tan_lat**6)

    de = e_ - _E0
    out_lat = lat - VII * de**2 + VIII * de**4 - IX * de**6
    out_lon = _LAM0 + X * de - XI * de**3 + XII * de**5 - XIIA * de**7
    return out_lon, out_lat


def _shift_datum(lon, lat, src, dst, sign):
    x, y, z = _geodetic_to_cart(lon, lat, src)
    return _cart_to_geodetic(*_helmert(x, y, z, sign), dst)


def wgs84_to_bng(lon, lat):
    """WGS84 lon/lat (degrees; scalars or array-likes) -> BNG (E, N) metres."""
    lon_r, lat_r = np.radians(np.asarray(lon, dtype=float)), np.radians(np.asarray(lat, dtype=float))
    lon36, lat36 = _shift_datum(lon_r, lat_r, _WGS84, _AIRY, +1)
    e_, n_ = _tm_forward(lon36, lat36, _AIRY)
    if np.ndim(lon) == 0 and np.ndim(lat) == 0:
        return float(e_), float(n_)
    return e_, n_


def bng_to_wgs84(easting, northing):
    """BNG (E, N) metres (scalars or array-likes) -> WGS84 lon/lat degrees."""
    lon36, lat36 = _tm_inverse(np.asarray(easting, dtype=float),
                               np.asarray(northing, dtype=float), _AIRY)
    lon_r, lat_r = _shift_datum(lon36, lat36, _AIRY, _WGS84, -1)
    lon, lat = np.degrees(lon_r), np.degrees(lat_r)
    if np.ndim(easting) == 0 and np.ndim(northing) == 0:
        return float(lon), float(lat)
    return lon, lat
