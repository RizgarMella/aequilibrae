"""Make lonboard fully offline: inline its parquet-wasm decoder.

lonboard's frontend fetches parquet_wasm_bg.wasm from cdn.jsdelivr.net at
render time; on CDN-blocked networks the map dies decoding its first layer.
This script rewrites lonboard/static/index.js so the wasm ships inline as a
data: URI, using the copy vendored in this repo — after which lonboard makes
no CDN requests at all.

Idempotent; re-run after any lonboard reinstall/upgrade.

Usage:  python vendor/patch-lonboard-offline.py            # patches this interpreter's lonboard
        /path/to/other/python vendor/patch-lonboard-offline.py
"""
import base64
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
WASM = HERE / "jupytergis-assets" / "parquet_wasm_bg.wasm"

try:
    import lonboard
except ImportError:
    sys.exit("lonboard is not installed in this interpreter - pip install lonboard anywidget first")

js = pathlib.Path(lonboard.__file__).parent / "static" / "index.js"
src = js.read_text(encoding="utf-8")

if "data:application/wasm;base64," in src:
    print(f"already patched: {js}")
    sys.exit(0)

pattern = re.compile(r"`https://cdn\.jsdelivr\.net/npm/parquet-wasm@\$\{[A-Za-z0-9_$]+\}/esm/parquet_wasm_bg\.wasm`")
if not pattern.search(src):
    sys.exit(f"no jsdelivr parquet-wasm reference found in {js} - lonboard version changed? "
             "Re-derive the pattern before patching.")

data_uri = "data:application/wasm;base64," + base64.b64encode(WASM.read_bytes()).decode()
patched = pattern.sub("`" + data_uri + "`", src)

backup = js.with_suffix(".js.orig")
if not backup.exists():
    backup.write_text(src, encoding="utf-8")
js.write_text(patched, encoding="utf-8")
print(f"patched {js}")
print(f"  wasm inlined: {WASM.stat().st_size:,} bytes (original kept at {backup.name})")
print("Restart the notebook kernel (not the server) for the change to take effect.")
