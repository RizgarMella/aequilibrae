import matplotlib

matplotlib.use("Agg")

from uktools import add_underlay, focus_map, new_map

UNDERLAY_LAYERS = ["sea", "land", "built-up areas", "road skeleton", "city labels"]


def test_national_underlay_builds_all_vector_layers():
    doc = new_map()
    add_underlay(doc)
    doc._build()
    assert [n for n, _ in doc._layers] == UNDERLAY_LAYERS
    assert not doc._bitmap_layers  # the under-map is vector, not raster


def test_focus_underlay_clipped_to_window():
    doc = focus_map("Birmingham", km=40)
    add_underlay(doc)
    doc._build()
    minx, miny, maxx, maxy = doc.bbox
    pad = 1e-6
    for g, name, *_ in doc.items:
        if not len(g):
            continue
        b = g.total_bounds
        assert b[0] >= minx - pad and b[2] <= maxx + pad, f"{name} leaks x"
        assert b[1] >= miny - pad and b[3] <= maxy + pad, f"{name} leaks y"
    # labels exist and are inside the window too
    (labels, _, col, *_ ) = doc._text_items[0]
    assert len(labels) >= 1 and "Birmingham" in set(labels[col])


def test_static_backend_renders_underlay():
    doc = focus_map("Birmingham", km=40)
    add_underlay(doc)
    fig = doc._static_figure()
    assert fig is not None
