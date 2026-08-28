#!/usr/bin/env bash
# Align the workstation image's own Jupyter server with the verified stack,
# in place - no new ports, no proxies. Use when the ONLY reachable URL is the
# one already serving JupyterLab (locked-down port policy).
#
# What it does:
#   1. installs the pinned server stack (vendor/server-requirements.txt),
#      including jupyterlab itself, into the interpreter that runs the
#      image's server (default /usr/bin/python) - after a restart the
#      sanctioned URL serves exactly the verified Lab build;
#   2. installs the vendored labextension set into the per-user directory
#      as a belt-and-braces overlay;
#   3. prints the diagnostics that matter.
#
# Idempotent: safe to re-run any time (pip pins are exact; re-running
# restores state after image updates or stray pip upgrades).
#
# Usage:  bash vendor/setup-image-server.sh [python-interpreter]
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${1:-/usr/bin/python}"

echo "== 1/3 pinning server stack into: $PY"
"$PY" -m pip install --break-system-packages --upgrade -r "$HERE/server-requirements.txt"

echo "== 2/3 vendored frontend overlay"
bash "$HERE/install-assets.sh"

echo "== 3/3 diagnostics"
"$PY" -m jupyter --version | sed 's/^/    /' || true
"$PY" -m jupyter labextension list 2>&1 | grep -E "jupytergis|yjs|widgets|collaboration|docprovider" | sed 's/^/    /' || true
echo
echo "Done. Now RESTART the workstation (or fully stop/start the Jupyter"
echo "service) and open the normal workstation URL in a NEW browser tab"
echo "(hard-refresh; stale tabs keep the old frontend)."
echo
echo "Red X / 'not compatible' marks against yjs-widgets, collaboration- and"
echo "docprovider-extension are metadata noise - the verified-working"
echo "environment shows the same marks."
