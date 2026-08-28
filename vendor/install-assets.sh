#!/usr/bin/env bash
# Install the vendored JupyterLab frontend extensions for the AequilibraE
# notebook course, so the browser never needs to reach any CDN (unpkg etc.).
#
# Why this exists: JupyterLab renders jupytergis maps through prebuilt
# "federated" labextensions. When any required frontend module is missing or
# version-mismatched on the server, the widget machinery falls back to
# fetching it from a CDN at render time - which fails on networks that block
# those hosts, leaving GISDocument outputs as a bare text repr. This script
# installs the complete, known-good frontend set (captured from a working
# environment running jupytergis 0.16.2 with zero external requests) into the
# per-user Jupyter data directory, which takes precedence over copies
# installed by pip into the environment prefix.
#
# Idempotent: safe to re-run at any time; re-running after a pip
# reinstall/upgrade of jupytergis restores the vendored frontend.
#
# Usage:            bash vendor/install-assets.sh
# Custom location:  JUPYTER_DATA_DIR=/path bash vendor/install-assets.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARCHIVE="$HERE/jupytergis-assets/labextensions.tar.gz"
TARGET="${JUPYTER_DATA_DIR:-$HOME/.local/share/jupyter}/labextensions"

[ -f "$ARCHIVE" ] || { echo "ERROR: $ARCHIVE not found (partial checkout?)" >&2; exit 1; }

mkdir -p "$TARGET"
tar -xzf "$ARCHIVE" -C "$TARGET"

echo "Installed vendored labextensions into: $TARGET"
tar -tzf "$ARCHIVE" | awk -F/ '{print ($1 ~ /^@/) ? $1"/"$2 : $1}' | sort -u | sed 's/^/  - /'
echo
echo "Next steps:"
echo "  1. Restart the Jupyter server."
echo "  2. Hard-refresh the browser tab (Ctrl+Shift+R)."
echo "  3. Verify with 'jupyter labextension list' - each extension above"
echo "     should appear once, served from $TARGET."
echo
echo "Acceptance check: open a notebook, run"
echo "    from jupytergis import GISDocument; GISDocument()"
echo "with the browser Network tab filtered to 'unpkg' - the map must render"
echo "with zero requests to unpkg.com. Note that basemap TILES (e.g."
echo "tile.openstreetmap.org) are still fetched by design; use an offline or"
echo "reachable tile host if tiles are also blocked."
