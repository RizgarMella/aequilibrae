"""uktools.maps - offline interactive maps and analyst tools.

lonboard (default) renders WebGL maps whose frontend ships from the kernel via
ipywidgets - no server extensions, no CDN. AEQ_MAP_BACKEND=static switches to
matplotlib. See MapDoc.show() for layer toggles and sidecar panels.
"""
import os

import matplotlib.pyplot as _plt
import numpy as np

from .style import STYLE, _style_arrays

class MapDoc:
    """Collects styled layers; renders via lonboard (or matplotlib)."""

    def __init__(self, bbox=None, height=None):
        self.items = []      # (gdf, name, arrays, opacity, tooltip_cols)
        self.bbox = bbox     # (minx, miny, maxx, maxy) - clips every layer
        self.height = height or STYLE["map_height"]
        self._map = None

    def add(self, gdf, name, symbology, opacity, tooltip=None):
        g = gdf
        if self.bbox is not None:
            minx, miny, maxx, maxy = self.bbox
            g = g.cx[minx:maxx, miny:maxy]
        g = g.reset_index(drop=True).explode(index_parts=False).reset_index(drop=True)
        self.items.append((g, name, _style_arrays(symbology, g), opacity, tooltip or []))

    def _build(self):
        from lonboard import Map, PathLayer, PolygonLayer, ScatterplotLayer
        built = []
        for g, name, st, op, tips in self.items:
            if not len(g):
                continue
            geom = g.geometry.geom_type.iloc[0]
            cols = [c for c in tips if c in g.columns]
            base = g[cols + ["geometry"]]
            pick = {"pickable": bool(cols), "auto_highlight": bool(cols),
                    "highlight_color": STYLE["highlight_rgba"]}
            if "LineString" in geom:
                kw = {"width_units": "pixels", "width_min_pixels": 1.0, "opacity": op, **pick}
                if st["stroke"] is not None:
                    kw["get_color"] = st["stroke"]
                if st["width"] is not None:
                    kw["get_width"] = st["width"]
                layer = PathLayer.from_geopandas(base, **kw)
            elif "Polygon" in geom:
                kw = {"opacity": op * 0.6, "stroked": False, **pick}
                if st["fill"] is not None:
                    kw["get_fill_color"] = st["fill"]
                layer = PolygonLayer.from_geopandas(base, **kw)
            else:
                kw = {"radius_min_pixels": 5, "opacity": op, **pick}
                fill = st["fill"] if st["fill"] is not None else st["stroke"]
                if fill is not None:
                    kw["get_fill_color"] = fill
                layer = ScatterplotLayer.from_geopandas(base, **kw)
            built.append((name, layer))
        show_tip = any(t for *_, t in self.items)
        self._map = Map(layers=[l for _, l in built], basemap=None,
                        show_tooltip=show_tip, height=self.height)
        self._layers = built
        return self._map

    # ---- analyst tools ----
    def show(self, controls=False, sidecar=None):
        """Display the map; controls=True adds layer on/off checkboxes;
        sidecar="Title" opens it in a JupyterLab side panel."""
        from IPython.display import display
        be = os.environ.get("AEQ_MAP_BACKEND", "lonboard").strip().lower()
        if be == "static":
            display(self._static_figure())
            return
        m = self._build()
        widget = m
        if controls:
            import ipywidgets as W
            boxes = []
            for name, layer in self._layers:
                cb = W.Checkbox(value=True, description=name, indent=False)
                W.jslink((cb, "value"), (layer, "visible"))
                boxes.append(cb)
            panel = W.VBox(boxes, layout=W.Layout(width="220px", overflow="auto"))
            widget = W.HBox([panel, m], layout=W.Layout(width="100%"))
        if sidecar:
            try:
                from sidecar import Sidecar
                with Sidecar(title=sidecar):
                    display(widget)
                return
            except ImportError:
                print("sidecar not installed - pip install sidecar; showing inline")
        display(widget)

    def selection(self):
        """Bounds (minx, miny, maxx, maxy) of the box dragged on the map
        (hold Shift and drag), or None."""
        return None if self._map is None else self._map.selected_bounds

    def _static_figure(self):
        fig, ax = _plt.subplots(figsize=(9, 7))
        ax.set_facecolor("#eef1f4")
        for g, name, st, op, _ in self.items:
            if not len(g):
                continue
            geom = g.geometry.geom_type.iloc[0]
            if "LineString" in geom:
                colors = st["stroke"] / 255 if st["stroke"] is not None else "#1d4ed8"
                widths = st["width"] if st["width"] is not None else 1.0
                g.plot(ax=ax, color=colors, linewidth=widths, alpha=op)
            elif "Polygon" in geom:
                colors = st["fill"] / 255 if st["fill"] is not None else "#cbd5e1"
                g.plot(ax=ax, color=colors, alpha=op * 0.6)
            else:
                fill = st["fill"] if st["fill"] is not None else st["stroke"]
                g.plot(ax=ax, color=(fill / 255 if fill is not None else STYLE["city_point"]),
                       markersize=25, alpha=op)
        ax.set_aspect(1.4)
        ax.set_xticks([]), ax.set_yticks([])
        _plt.tight_layout()
        _plt.close(fig)
        return fig

    def _ipython_display_(self):
        self.show()


def new_map(gdf_for_extent=None, zoom=12, bbox=None, height=None):
    """Create a map document. bbox=(minx, miny, maxx, maxy) clips all layers."""
    return MapDoc(bbox=bbox, height=height)


def add_gdf(doc, gdf, name, symbology=None, tooltip=None, split_by=None, **kwargs):
    """Add a GeoDataFrame as a styled layer.

    tooltip=["col", ...] shows those attributes on hover (with highlight).
    split_by="col" adds one layer per category - each independently
    toggleable in doc.show(controls=True)."""
    op = kwargs.get("opacity", 1.0)
    if split_by:
        for val in dict.fromkeys(gdf[split_by].dropna()):
            doc.add(gdf[gdf[split_by] == val], f"{name}: {val}", symbology, op, tooltip)
        return name
    doc.add(gdf, name, symbology, op, tooltip)
    return name


def side_by_side(doc_a, doc_b, titles=("A", "B")):
    """Two maps in one row - compare scenarios or runs."""
    import ipywidgets as W
    half = W.Layout(width="49%")
    cols = []
    for doc, title in zip((doc_a, doc_b), titles):
        cols.append(W.VBox([W.HTML(f"<b>{title}</b>"), doc._build()], layout=half))
    return W.HBox(cols, layout=W.Layout(width="100%"))


def merge_lines(gdf, tol=0.01):
    """Collapse many lines into a single MultiLineString feature - backdrops
    do not need per-feature identity, and one merged feature draws far cheaper."""
    import geopandas as _gpd
    from shapely.geometry import MultiLineString
    parts = []
    for geom in gdf.geometry.simplify(tol):
        if geom is None or geom.is_empty:
            continue
        parts.extend(geom.geoms if geom.geom_type == "MultiLineString" else [geom])
    return _gpd.GeoDataFrame({"links": [len(parts)]}, geometry=[MultiLineString(parts)], crs=gdf.crs)
