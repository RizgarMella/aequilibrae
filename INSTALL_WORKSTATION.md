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

## Phase 3 — the Jupyter server: run it from the venv

The decisive lesson from the field: do **not** rely on the workstation
image's preinstalled JupyterLab for the map notebooks. Its build and
configuration differ from the verified stack in ways that surface as
maps degrading to a text repr and CDN fallback requests. Instead, install
the exact verified server stack into the venv and run Lab from there:

```bash
source ~/aeq-env/bin/activate
pip install -r ~/aequilibrae/vendor/server-requirements.txt
cd ~/aequilibrae/notebooks
jupyter lab --no-browser --port 8890
```

Open port 8890 through the workstation's port-forward/preview URL (Cloud
Workstations exposes forwarded ports from its toolbar). On a locked-down
workstation config the port-prefixed URL (`https://8890-<workstation-host>/`)
may not be forwarded; if it does not respond, take over the port the image's
Lab already uses — that one is proven reachable:

```bash
jupyter server list            # note the running server's port, e.g. 8080
jupyter server stop 8080  ||  pkill -f jupyter    # stop the image's server
source ~/aeq-env/bin/activate
cd ~/aequilibrae/notebooks
jupyter lab --no-browser --port 8080 --ip 127.0.0.1
```

then reload the normal workstation URL, now served by the venv stack. (If a
supervisor keeps restarting the image's Lab on that port, ask the admin to
open one forwarded port instead.)

Expect the basemap to be blank grey when tile hosts (openstreetmap.org) are
outside the egress allowlist — model layers still draw over it; only the
background street map is missing. Everything —
server, frontend extensions, kernel — now comes from one venv with pinned,
mutually-consistent versions: the same set verified to make zero CDN
requests.

**Check:** `jupyter labextension list` (venv active) shows
`@jupytergis/jupytergis-core`, `-lab`, `-qgis` 0.16.2,
`@jupyter-widgets/jupyterlab-manager` 5.0.16 and `yjs-widgets`.
Ignore red X / "not compatible" marks against `yjs-widgets`,
`@jupyter/collaboration-extension` and `@jupyter/docprovider-extension` —
the verified-working environment shows exactly the same marks; they are
metadata noise from the compatibility checker, not real failures.

<details><summary>Fallback: using the image's JupyterLab anyway</summary>

If you must use the preinstalled Lab (server in system Python), mirror the
pins there too — `/usr/bin/python -m pip install --break-system-packages -r
~/aequilibrae/vendor/server-requirements.txt` — and continue with Phase 4.
This is the configuration that has repeatedly misbehaved; prefer the venv
server.

</details>

## Phase 4 — vendored frontend (only for the image-Lab fallback)

Running the server from the venv (Phase 3) already serves every frontend
asset same-origin — this phase is only needed on the image-Lab fallback
path, or if a future pip upgrade breaks the venv's extension set.

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
| Red X / "not compatible" against `yjs-widgets`, `collaboration-extension`, `docprovider-extension` | compatibility-checker metadata noise | ignore — the verified-working environment shows the same marks |
| Object repr persists; console shows `No provider for: yjs-widgets:IJupyterYWidgetManager` or `Exception opening new comm` | the notebook-renderer plugin failed to activate in the server's frontend | run the server from the venv (Phase 3) so server+frontend+kernel versions match |
| Everything ran yesterday, broken after a pip upgrade | upgrade clobbered frontend copies | re-run Phase 4 script (idempotent), restart, hard-refresh |
