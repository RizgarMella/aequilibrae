#!/usr/bin/env bash
# Diagnose why jupytergis maps degrade to a text repr, using only local
# facts - run on the workstation and paste the full output.
#   bash vendor/diagnose.sh
set -uo pipefail

echo "=== 1. Running Jupyter server processes (interpreter + start time)"
for pid in $(pgrep -f "jupyter" 2>/dev/null); do
    exe="$(readlink -f /proc/$pid/exe 2>/dev/null)"
    lstart="$(ps -o lstart= -p $pid 2>/dev/null)"
    cmd="$(tr '\0' ' ' < /proc/$pid/cmdline 2>/dev/null | cut -c1-140)"
    echo "  pid=$pid started='$lstart'"
    echo "     exe=$exe"
    echo "     cmd=$cmd"
done

echo
echo "=== 2. When Path A last ran (newer than server start => RESTART NEEDED)"
for f in "$HOME/.local/share/jupyter/labextensions/yjs-widgets/package.json" \
         /usr/lib/python3*/dist-packages/yjs_widgets/__init__.py \
         /usr/local/lib/python3*/dist-packages/yjs_widgets/__init__.py; do
    [ -e "$f" ] && echo "  $(stat -c '%y' "$f" | cut -c1-19)  $f"
done

echo
echo "=== 3. What the RUNNING server actually serves (queried over localhost)"
FOUND=0
for rt in "$HOME/.local/share/jupyter/runtime" /tmp; do
    for j in "$rt"/jpserver-*.json; do
        [ -e "$j" ] || continue
        url="$(python3 - "$j" <<'PYEOF'
import json, sys
d = json.load(open(sys.argv[1]))
print(f"http://127.0.0.1:{d['port']}{d.get('base_url','/')}?token={d.get('token','')}")
PYEOF
)"
        page="$(curl -s -m 5 "${url/\?/lab?}" 2>/dev/null)"
        [ -n "$page" ] || continue
        FOUND=1
        echo "  server config: $j"
        echo "  serving /lab: yes"
        for probe in "yjs-widgets" "jupytergis-lab" "jupytergis-core" "unpkg"; do
            n="$(printf '%s' "$page" | grep -o "$probe" | wc -l)"
            echo "    page mentions '$probe': $n time(s)"
        done
        printf '%s' "$page" | grep -o '"@jupytergis/jupytergis-lab"[^}]*' | head -1 | sed 's/^/    /'
        printf '%s' "$page" | grep -o '"yjs-widgets"[^}]*' | head -1 | sed 's/^/    /'
    done
done
[ "$FOUND" = 1 ] || echo "  could not reach a running server via runtime files"

echo
echo "=== 4. yjs-widgets frontend on disk, per location"
for d in "$HOME/.local/share/jupyter/labextensions" \
         /usr/share/jupyter/labextensions /usr/local/share/jupyter/labextensions \
         /opt/*/share/jupyter/labextensions; do
    [ -d "$d/yjs-widgets" ] && echo "  present: $d/yjs-widgets (v$(python3 -c "import json;print(json.load(open('$d/yjs-widgets/package.json'))['version'])" 2>/dev/null))"
done

echo
echo "=== 5. Interpretation"
echo "  - Section 1 'exe' tells you which environment really runs the server."
echo "    If it is not /usr/bin/python*, Path A patched the wrong env - report it."
echo "  - If Section 2 timestamps are NEWER than the server start in Section 1,"
echo "    the server predates the fix: RESTART THE WORKSTATION, hard-refresh,"
echo "    and re-test before anything else."
echo "  - In Section 3, 'yjs-widgets: 0 time(s)' on a fresh server means the"
echo "    served frontend lacks the renderer module - paste this output."
echo "  - Finally: in the browser Network tab, filter 'unpkg', right-click the"
echo "    failed request -> Copy -> Copy link address, and include that URL."
