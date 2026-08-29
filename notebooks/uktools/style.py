"""uktools.style - cartographic standards and the symbology DSL.

Every colour, ramp and standard lives in STYLE; notebooks reference STYLE and
the canned builders instead of hard-coding styling next to model logic.
"""
import matplotlib.colors
import matplotlib.pyplot as _plt
import numpy as np

STYLE = {
    # colour ramps
    "flow_ramp": "YlOrRd",            # traffic volume
    "congestion_ramp": "RdYlGn",      # V/C - reversed so red = congested
    "diff_ramp": "RdBu",              # scenario differences - reversed: red = increase
    "density_ramp": "viridis",
    "desire_ramp": "plasma",        # zone choropleths
    "access_ramp": "magma",           # accessibility (reversed: bright = close)
    "select_ramp": "Blues",           # select-link flows
    "category_ramp": "tab10",         # categorical (corridors etc.)
    # fixed colours
    "boundary_fill": "#94a3b8",
    "backdrop_line": "#94a3b8",
    # the vector under-map (colours harvested from the retired raster basemap)
    "sea_fill": "#d6e3ef",
    "land_fill": "#f7f5f0",
    "builtup_fill": "#e6dfd4",
    "skeleton_line": "#cfc6b8",
    "label_color": [71, 85, 105, 255],       # slate-600
    "label_size_px": 13,
    "city_point": "#dc2626",
    "emphasis": "#dc2626",
    "road_class_colors": {"motorway": "#1d4ed8", "trunk": "#475569",
                          "primary": "#059669", "secondary": "#d4a373",
                          "ramp": "#7c3aed"},
    # standards
    "line_width_px": (0.5, 7.0),      # min/max flow-scaled widths
    "voc_domain": (0.0, 1.5),
    "map_height": 520,
    "highlight_rgba": [255, 214, 10, 160],
}


# --- declarative symbology --------------------------------------------------
class _Mapping:
    def __init__(self, field, scheme, params):
        self.field, self.scheme, self.params = field, scheme, params

    def encoding(self, *targets):
        return {"field": self.field, "scheme": self.scheme,
                "params": self.params, "encodings": list(targets)}


class _Field:
    def __init__(self, name):
        self.name = name

    def colormap(self, name="viridis", *, domain=None, reverse=False, n_shades=9):
        return _Mapping(self.name, "colormap",
                        {"name": name, "domain": domain, "reverse": reverse})

    def scalar(self, *, domain, output_range):
        return _Mapping(self.name, "scalar",
                        {"domain": list(domain), "range": list(output_range)})

    def categorical(self, name=None):
        return _Mapping(self.name, "categorical",
                        {"name": name or STYLE["category_ramp"]})


class _Constant:
    def __init__(self, value):
        self.value = value

    def encoding(self, *targets):
        scheme = "constant_num" if isinstance(self.value, (int, float)) else "constant_color"
        return {"field": None, "scheme": scheme,
                "params": {"value": self.value}, "encodings": list(targets)}


def field(name):
    """Style by a data column: .colormap() / .scalar() / .categorical()."""
    return _Field(name)


def constant(value):
    """A fixed colour (hex/name) or number, e.g. constant(STYLE["emphasis"])."""
    return _Constant(value)


# --- canned symbologies (the standards, ready to use) -----------------------
def flow_style(flow_col, fmax, *, ramp=None):
    """Volume map: colour and width both scale with flow."""
    return [[field(flow_col).colormap(ramp or STYLE["flow_ramp"], domain=(0.0, fmax)).encoding("stroke"),
             field(flow_col).scalar(domain=(0.0, fmax), output_range=STYLE["line_width_px"]).encoding("stroke-width")]]


def congestion_style(voc_col, flow_col, fmax):
    """Congestion map: colour = V/C (green->red), width = flow."""
    return [[field(voc_col).colormap(STYLE["congestion_ramp"], reverse=True, domain=STYLE["voc_domain"]).encoding("stroke"),
             field(flow_col).scalar(domain=(0.0, fmax), output_range=STYLE["line_width_px"]).encoding("stroke-width")]]


def diff_style(diff_col, dmax, flow_col=None, fmax=None):
    """Scenario difference: red = increase, blue = decrease."""
    sym = [field(diff_col).colormap(STYLE["diff_ramp"], reverse=True, domain=(-dmax, dmax)).encoding("stroke")]
    if flow_col:
        sym.append(field(flow_col).scalar(domain=(0.0, fmax), output_range=STYLE["line_width_px"]).encoding("stroke-width"))
    else:
        sym.append(constant(2.0).encoding("stroke-width"))
    return [sym]


def class_style(cls):
    """The standard colour for a road class."""
    return [[constant(STYLE["road_class_colors"].get(cls, "#6b7280")).encoding("stroke")]]


def _rgba255(c, alpha=1.0):
    r, g, b, a = matplotlib.colors.to_rgba(c, alpha)
    return [int(r * 255), int(g * 255), int(b * 255), int(a * 255)]


def _style_arrays(symbology, gdf):
    n = len(gdf)
    out = {"stroke": None, "width": None, "fill": None}
    if not symbology:
        return out
    mappings = [m for group in symbology for m in (group if isinstance(group, list) else [group])]
    for m in mappings:
        scheme, params, fld, encs = m["scheme"], m["params"], m["field"], m["encodings"]
        arr = wid = None
        if scheme == "constant_color":
            arr = np.tile(_rgba255(params["value"]), (n, 1)).astype(np.uint8)
        elif scheme == "colormap":
            cmap = _plt.get_cmap(params["name"])
            if params.get("reverse"):
                cmap = cmap.reversed()
            dom = params.get("domain") or [float(gdf[fld].min()), float(gdf[fld].max())]
            vals = gdf[fld].to_numpy(dtype=float)
            t = np.clip((vals - dom[0]) / max(dom[1] - dom[0], 1e-12), 0, 1)
            arr = (cmap(t) * 255).astype(np.uint8)
        elif scheme == "categorical":
            cmap = _plt.get_cmap(params["name"])
            uniq = list(dict.fromkeys(gdf[fld].dropna()))
            idx = {v: i for i, v in enumerate(uniq)}
            arr = np.array([_rgba255(cmap(idx.get(v, 0) % cmap.N)) for v in gdf[fld]], dtype=np.uint8)
        elif scheme == "constant_num":
            wid = np.full(n, float(params["value"]))
        elif scheme == "scalar":
            d, r = params["domain"], params["range"]
            vals = gdf[fld].to_numpy(dtype=float)
            t = np.clip((vals - d[0]) / max(d[1] - d[0], 1e-12), 0, 1)
            wid = r[0] + t * (r[1] - r[0])
        if arr is not None:
            if any("stroke" in e for e in encs):
                out["stroke"] = arr
            if any("fill" in e for e in encs):
                out["fill"] = arr
        if wid is not None and any("width" in e for e in encs):
            out["width"] = wid
    return out


