# Workstation setup — phased install

Phased install of this fork and its notebook course on a locked-down machine
(written for Google Cloud Workstations: JupyterLab preinstalled, Debian
system Python that is externally managed, egress limited to github.com and
PyPI, CDNs such as unpkg.com blocked). Every phase ends with a check —
do not move on until the check passes. Each check exists because its failure
mode has actually been hit.

Throughout, `python3` means the system interpreter and `~/aeq-env` the
project venv. Run everything in a Jupyter terminal (File → New → Terminal).

---

## Phase 0 — auth and clone

```bash
gh auth login          # choose github.com, HTTPS; handles git credentials too
git clone https://github.com/RizgarMella/aequilibrae.git ~/aequilibrae
```

Clone into the home directory (persistent disk), not `/tmp`. A full clone —
the notebooks need `notebooks/data/` and `vendor/`; a sparse notebooks-only
checkout will miss the vendored frontend. If you have an old
`~/aeq-notebooks` sparse checkout, retire it in favour of this clone.

**Check:** `ls ~/aequilibrae/vendor/jupytergis-assets/labextensions.tar.gz`
exists.

---

## Phase 1 — venv with the fork wheel

```bash
python3 -m venv ~/aeq-env            # skip if ~/aeq-env already exists
source ~/aeq-env/bin/activate
python -V                            # note the minor version, e.g. 3.12
gh release download v1.7.0.post1-pip-only --repo RizgarMella/aequilibrae \
   --pattern "*cp312*manylinux*x86_64*"     # match your Python minor version
pip install --upgrade ./aequilibrae-1.7.0.post1-*.whl
pip install ipykernel ipywidgets geopandas matplotlib scipy
```

Why the release wheel and why `--upgrade`: the fork's package is also named
`aequilibrae`, and plain `1.7.0` wheels were silently skipped by pip on any
machine where the upstream PyPI package had ever been installed ("requirement
already satisfied") — the classic symptom being
`no such function: AddGeometryColumn` at run time, because upstream needs
native SpatiaLite. The `1.7.0.post1` version outranks upstream's `1.7.0`, and
`--upgrade` replaces an upstream install if one is present. Never
`pip install aequilibrae` from PyPI in this venv.

(A `numpy<2` pin is not needed — the fork is verified on numpy 2.5.)

**Check (all three, inside the venv):**

```bash
python -c "import aequilibrae; print(aequilibrae.version, aequilibrae.__file__)"
#  -> 1.7.0.post1, path inside ~/aeq-env
python -c "from aequilibrae.utils import spatialite_shim; print('shim OK')"
python -c "from aequilibrae.project import Project; import tempfile, os
p = Project(); p.new(os.path.join(tempfile.mkdtemp(), 'chk')); p.close(); print('project OK')"
```

The third check exercises `AddGeometryColumn` and friends — if it passes, the
shim is live and the day-one error class is gone.

---

## Phase 2 — register the venv as the notebooks' kernel

The course notebooks reference the standard kernel name `python3`. If that
resolves to the system interpreter, every notebook dies at
`ModuleNotFoundError: No module named 'geopandas'` (or `aequilibrae`).
Override it per-user with the venv:

```bash
source ~/aeq-env/bin/activate
python -m ipykernel install --user --name python3 --display-name "Python (aeq)"
```

**Check:** `jupyter kernelspec list` shows `python3` pointing under
`~/.local/share/jupyter/kernels/python3`, and
`cat ~/.local/share/jupyter/kernels/python3/kernel.json` names the venv's
python. Every notebook now opens on the right interpreter without manual
kernel switching.

---

## Phase 3 — server-side jupytergis

The Jupyter *server* (system Python on Cloud Workstations) must also have
jupytergis so its extensions are served:

```bash
/usr/bin/python -m pip install --break-system-packages "jupytergis==0.16.2"
source ~/aeq-env/bin/activate && pip install "jupytergis==0.16.2" jupyterlab
```

If `jupyter labextension list` later flags an `@jupyter/ydoc` version
conflict (an X against collaboration/docprovider), upgrade those on the
server side: `/usr/bin/python -m pip install --break-system-packages -U
jupyter-collaboration`.

**Check:** `jupyter labextension list 2>&1 | grep -E "jupytergis|widgets|yjs"`
shows `@jupytergis/jupytergis-core`, `-lab`, `-qgis` 0.16.2 and
`@jupyter-widgets/jupyterlab-manager` — all `OK`, no `X`.

---

## Phase 4 — vendored frontend (the CDN fix)

Networks that block unpkg.com break map rendering in a specific way:
`GISDocument()` shows only its text repr, and DevTools shows blocked unpkg
requests. Root cause: when any required frontend module is missing or
version-mismatched server-side (in practice `yjs-widgets`, the module
jupytergis notebook outputs render through), the widget machinery falls back
to fetching it from a CDN at render time. A complete, version-consistent
extension set makes zero CDN requests — and this repo vendors exactly that
set, captured from a verified environment:

```bash
bash ~/aequilibrae/vendor/install-assets.sh
```

Installs into `~/.local/share/jupyter/labextensions/`, which outranks
pip-installed copies. Idempotent — **re-run it after any pip
install/upgrade touching jupytergis or jupyter-collaboration**, since those
can reintroduce mismatched frontend copies. Details: `vendor/README.md`.

Then restart the Jupyter server (on Cloud Workstations the reliable way is
stopping and starting the workstation, or `File → Shut Down` and relaunch)
and **hard-refresh the browser** (Ctrl+Shift+R) — JupyterLab caches
federated extensions aggressively, and a stale tab will keep showing the old
behaviour. Stale-tab state has burned us more than once: if anything looks
half-updated, close the tab entirely and reopen.

**Check:** `jupyter labextension list` includes `yjs-widgets v0.6.0`
alongside the Phase 3 set, served from `~/.local/share/jupyter`.

---

## Phase 5 — acceptance tests

1. **Bare map, zero CDN.** New notebook (it should open on "Python (aeq)"),
   browser Network tab open, filtered to `unpkg`:

   ```python
   from jupytergis import GISDocument
   doc = GISDocument()
   doc
   ```

   An interactive map must render with **zero** unpkg requests. (Basemap
   *tiles* — e.g. `tile.openstreetmap.org` — are map data, fetched at
   pan/zoom by design; if tiles are also blocked the map renders with a
   blank background but layers still draw.)

2. **Course smoke test.** Run `notebooks/01_project_and_network.ipynb`
   top-to-bottom: exercises the shim, GeoDataFrames and a layered map in
   ~a minute.

3. **Full model.** Run `notebooks/13_gb_complete_model.ipynb` (5–10 min),
   Network tab still filtered to `unpkg`. Any failed unpkg request that
   appears is a lazily-loaded module missing from the vendor bundle —
   capture its full URL from the Network tab and report it so the bundle
   can be extended.

---

## Troubleshooting index (today's greatest hits)

| Symptom | Cause | Fix |
|---|---|---|
| `no such function: AddGeometryColumn` | upstream PyPI `aequilibrae` shadowing the fork | Phase 1: `pip install --upgrade` the `.post1` wheel; verify `aequilibrae.version == "1.7.0.post1"` |
| `ModuleNotFoundError: geopandas` (or `aequilibrae`) in a notebook | notebook opened on the system `python3` kernel | Phase 2 kernel override; or Kernel → Change Kernel → "Python (aeq)" |
| `GISDocument()` shows text repr; unpkg blocked in DevTools | missing/mismatched frontend module triggers CDN fallback | Phase 4 script + server restart + hard refresh |
| Map renders but a layer listed in the panel draws nothing / only first layers appear | oversized layer payload silently dropped by the notebook sync | already fixed in the course notebooks (coordinates quantized, backdrops merged) — `git pull` |
| Maps lack colours / "unsupported symbology" | jupytergis 0.16 renders from legacy flat-styles only | already fixed in the notebooks' shared `add_gdf` helper — `git pull` |
| Notebook edits on disk not appearing in the browser | JupyterLab collaborative store serving a cached copy | close the tab, reopen; stubborn cases: stop server, delete `.jupyter_ystore.db` in the notebooks folder, restart |
| Everything ran yesterday, broken after a pip upgrade | upgrade clobbered frontend copies | re-run Phase 4 script (idempotent), restart, hard-refresh |
