# Workstation setup — phased install

Phased install of this fork and its notebook course on a locked-down machine
(written for Google Cloud Workstations: JupyterLab preinstalled, Debian
system Python that is externally managed, egress limited to github.com and
PyPI, CDNs blocked, no new ports, no GitHub CLI). Every phase ends with a
check — do not move on until the check passes.

The maps use **lonboard**: interactive WebGL maps whose frontend JavaScript
ships from the kernel through the ipywidgets channel — no jupytergis, no
server extensions, no collaboration stack, no CDN (its one CDN dependency,
a wasm decoder, is vendored in this repo and patched inline by a script).
The course previously used jupytergis; that stack is abandoned — its vendor
files remain in `vendor/` for reference only.

---

## Phase 0 — clone

```bash
git clone https://github.com/RizgarMella/aequilibrae.git ~/aequilibrae
```

The repo is public: no auth, no `gh`. Clone into the home directory
(persistent disk), not `/tmp`. A full clone — the notebooks need
`notebooks/data/` and `vendor/`.

**Check:** `ls ~/aequilibrae/vendor/jupytergis-assets/parquet_wasm_bg.wasm`
exists.

---

## Phase 1 — venv with the fork

```bash
python3 -m venv ~/aeq-env            # skip if ~/aeq-env already exists
source ~/aeq-env/bin/activate
pip install --upgrade "aequilibrae @ git+https://github.com/RizgarMella/aequilibrae.git@remove-native-spatialite"
pip install ipykernel ipywidgets geopandas matplotlib scipy lonboard anywidget sidecar
```

Git-source install uses only git-over-github.com (proven on the
workstation). The branch's version is `1.7.0.post1`, which outranks upstream
PyPI's `1.7.0`, and `--upgrade` replaces an upstream install if one is
present — this closes the `no such function: AddGeometryColumn` trap
(upstream package shadowing the fork). Never `pip install aequilibrae` from
PyPI in this venv.

**Check (all three, inside the venv):**

```bash
python -c "import aequilibrae; print(aequilibrae.version, aequilibrae.__file__)"
#  -> 1.7.0.post1, path inside ~/aeq-env
python -c "from aequilibrae.utils import spatialite_shim; print('shim OK')"
python -c "from aequilibrae.project import Project; import tempfile, os
p = Project(); p.new(os.path.join(tempfile.mkdtemp(), 'chk')); p.close(); print('project OK')"
```

---

## Phase 2 — register the venv as the notebooks' kernel

The course notebooks reference the standard kernel name `python3`; if that
resolves to the system interpreter, every notebook dies with
`ModuleNotFoundError`. Override it per-user:

```bash
source ~/aeq-env/bin/activate
python -m ipykernel install --user --name python3 --display-name "Python (aeq)"
```

**Check:** `cat ~/.local/share/jupyter/kernels/python3/kernel.json` names the
venv's python.

---

## Phase 3 — the map frontend (two commands)

The ipywidgets channel already works on the workstation (an `IntSlider`
renders). lonboard needs only two more things:

1. **anywidget's tiny labextension served by the image's Lab.** Installing
   it with system pip drops the extension where the server already picks
   extensions up (a mechanism proven on this workstation):

   ```bash
   /usr/bin/python -m pip install --break-system-packages anywidget lonboard sidecar
   ```

2. **lonboard's wasm decoder inlined** (it otherwise loads from
   cdn.jsdelivr.net at render time — blocked). Patch the venv copy; the
   wasm is vendored in this repo:

   ```bash
   ~/aeq-env/bin/python ~/aequilibrae/vendor/patch-lonboard-offline.py
   ```

   Idempotent — re-run after any lonboard reinstall/upgrade.

Then restart the Jupyter server (workstation stop/start) and hard-refresh
the browser. **A stale tab is the most common way a completed fix looks
broken** — when in doubt, close the tab entirely and reopen.

**Check:** `jupyter labextension list 2>&1 | grep anywidget` shows
`anywidget` enabled OK.

---

## Phase 4 — acceptance tests

1. **Offline interactive map.** Open
   `notebooks/01_project_and_network.ipynb` (it should open on
   "Python (aeq)"), browser Network tab open with filters `unpkg` and
   `jsdelivr`, and Run All. The maps render as WebGL panels (pan/zoom with
   the mouse) with **zero** unpkg/jsdelivr requests. One request to
   `fonts.googleapis.com` may appear and fail — cosmetic font fallback,
   harmless.

2. **Full model.** Run `notebooks/13_gb_complete_model.ipynb` (5–10 min):
   choropleth, accessibility map, desire lines, flow and congestion views,
   select-link and corridors all render as interactive offline maps.

There is **no basemap** on these maps by design (basemap tiles are
CDN-hosted); model layers draw on a neutral background, with the GB boundary
layer providing geographic context. `AEQ_MAP_BACKEND=static` switches the
same notebooks to plain matplotlib rendering if ever needed.

---

## Troubleshooting index

| Symptom | Cause | Fix |
|---|---|---|
| `no such function: AddGeometryColumn` | upstream PyPI `aequilibrae` shadowing the fork | Phase 1 `pip install --upgrade`; verify version is `1.7.0.post1` |
| `ModuleNotFoundError` (geopandas/aequilibrae) in a notebook | notebook on the system `python3` kernel | Phase 2 kernel override |
| Map output empty or shows a javascript error | anywidget frontend not served, or stale tab | Phase 3 step 1, restart server, hard-refresh |
| Console: `No version of module anywidget is registered` | anywidget labextension missing server-side | Phase 3 step 1 + server restart |
| Map panel appears but layers never draw; failed `cdn.jsdelivr.net/.../parquet_wasm_bg.wasm` request | lonboard's wasm decoder blocked | Phase 3 step 2 (patch script), then restart the **kernel** |
| Everything ran yesterday, broken after a pip upgrade | upgrade replaced the patched lonboard | re-run Phase 3 step 2 |
| Notebook edits on disk not appearing in the browser | stale tab / collaborative cache | close the tab and reopen; stubborn: restart server |
