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
git clone https://github.com/RizgarMella/aequilibrae.git ~/aequilibrae
```

(The repo is public, so no auth is needed - and the workstation has no
GitHub CLI; nothing in this guide uses gh. If the repo is ever made
private, use a personal access token as the password when git prompts.)

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
# download the wheel matching your Python minor version (cp312 for 3.12 etc.)
curl -LO https://github.com/RizgarMella/aequilibrae/releases/download/v1.7.0.post1-pip-only/aequilibrae-1.7.0.post1-cp312-cp312-manylinux_2_24_x86_64.manylinux_2_28_x86_64.whl
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

## Phase 3 — the Jupyter server: two paths, no new ports

Assume the port policy is strict: the **only** reachable URL is the one
already serving JupyterLab. Both paths below deliver the verified stack
through exactly that URL.

### Path A (default): align the image's server in place

The image's Lab runs from system Python (evidence: `--break-system-packages`
installs change its extension list). So pin the entire verified stack —
including `jupyterlab` itself — into system Python, and the sanctioned URL
serves the verified build after a restart:

```bash
bash ~/aequilibrae/vendor/setup-image-server.sh
# then restart the workstation and open the normal URL in a NEW tab (hard-refresh)
```

The script is idempotent — re-run it after image updates or any stray pip
upgrade. It also prints the diagnostics that matter.

**Check:** `jupyter labextension list` shows `@jupytergis/*` 0.16.2,
`@jupyter-widgets/jupyterlab-manager` 5.0.16 and `yjs-widgets`. Ignore red
X / "not compatible" marks against `yjs-widgets`,
`@jupyter/collaboration-extension` and `@jupyter/docprovider-extension` —
the verified-working environment shows exactly the same marks.

### Path B (fallback): venv Lab through the sanctioned port

If Path A's premise ever fails (an image update moves the server off system
Python), run the venv's Lab bound to localhost and let the image's server
proxy it through the already-open port:

```bash
/usr/bin/python -m pip install --break-system-packages jupyter-server-proxy
# restart the workstation so the proxy extension loads, then:
source ~/aeq-env/bin/activate
pip install -r ~/aequilibrae/vendor/server-requirements.txt
cd ~/aequilibrae/notebooks
jupyter lab --no-browser --ip 127.0.0.1 --port 8890     --ServerApp.base_url=/proxy/absolute/8890/     --IdentityProvider.token=aeq
```

Open `https://<the-normal-workstation-host>/proxy/absolute/8890/lab?token=aeq`
— same origin, same sanctioned port, websockets included; nothing new is
exposed. (`/proxy/absolute/` keeps the URL prefix so the inner Lab's links
resolve; the inner Lab is reachable only via the authenticated outer server.)

Either path ends with server, frontend and kernel on pinned,
mutually-consistent versions — the set verified to make zero CDN requests.

Expect the basemap to be blank grey when tile hosts (openstreetmap.org) are
outside the egress allowlist — model layers still draw over it; only the
background street map is missing.

## Phase 4 — vendored frontend (belt-and-braces for Path A)

Path A's script already runs this; on Path B it is unnecessary (the venv
serves its own frontend). Kept for manual repair if a pip upgrade breaks an
extension set.

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
