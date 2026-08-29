# Vendored assets

**Current:** the notebook course renders maps with **lonboard** (offline
WebGL via ipywidgets). Two files here support that:

- `jupytergis-assets/parquet_wasm_bg.wasm` - lonboard's parquet decoder,
  vendored so no CDN is needed; applied by `patch-lonboard-offline.py`.
- `patch-lonboard-offline.py` - inlines the wasm into the installed
  lonboard (idempotent; re-run after lonboard upgrades).

Everything below this line concerns the **abandoned jupytergis stack** and
is kept for reference only.

---

# Vendored JupyterLab frontend assets

`jupytergis-assets/labextensions.tar.gz` contains the complete set of
prebuilt JupyterLab federated extensions the notebook course's maps need,
captured from a verified-working environment (JupyterLab 4.6, jupytergis
0.16.2) that renders every notebook with **zero CDN requests**:

- `@jupytergis/jupytergis-core`, `-lab`, `-qgis` 0.16.2
- `yjs-widgets` 0.6.0 (the module jupytergis notebook outputs render through)
- `@jupyter-widgets/jupyterlab-manager` 5.0.16 + `jupyterlab-sidecar`
- `@jupyter/collaboration-extension`, `@jupyter/docprovider-extension` 4.4.2
- `jupyterlab-tour`, `jupyterlab_pygments`

`server-requirements.txt` pins the exact server-side Python stack of the same
verified environment. The strongest setup on an offline workstation is to
install it into the project venv and run `jupyter lab` from that venv
(see `INSTALL_WORKSTATION.md`, Phase 3) — then this tarball is only a backup
for repairing a broken extension set.

Note: `jupyter labextension list` marks `yjs-widgets`,
`@jupyter/collaboration-extension` and `@jupyter/docprovider-extension` with a
red X ("not compatible") even in the verified-working environment — those
marks are metadata noise; do not chase them.

## Offline workstations (unpkg.com etc. unreachable)

If `GISDocument()` shows only a text repr and the browser console shows
failed requests to a CDN such as unpkg.com, the server is missing (or has a
version mismatch in) one of the frontend modules above, and the widget
machinery is falling back to fetching it from the CDN at render time.

One-time setup on such a machine:

```bash
git pull                        # get this vendor/ directory
bash vendor/install-assets.sh   # installs into ~/.local/share/jupyter/labextensions
# restart the Jupyter server, then hard-refresh the browser (Ctrl+Shift+R)
```

The script is idempotent — re-run it after any `pip install`/upgrade that
touches jupytergis or jupyter-collaboration. The per-user labextensions
directory takes precedence over environment copies, so the vendored,
version-consistent frontend always wins.

If a map later makes any CDN request (browser Network tab, filter `unpkg`),
that module is missing from this bundle — capture the URL and add the
corresponding labextension to the tarball.

Note: basemap **tiles** (e.g. `tile.openstreetmap.org`) are map data, not
frontend assets, and are still fetched at pan/zoom time by design. The
notebooks otherwise run fully offline. (One unrelated CDN reference exists in
nbconvert's reveal.js slide-export template — it only matters if you export
notebooks as slides, not for running them.)
