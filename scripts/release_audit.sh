#!/usr/bin/env bash
set -euo pipefail
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
export PYTHONPATH="$ROOT/src"
python -m compileall -q src
python -m pytest -q
python - <<'PY'
import universal_coder
assert universal_coder.__version__ == '2.1.0'
print('version:', universal_coder.__version__)
PY
wheel_dir=".release-wheel"
rm -rf "$wheel_dir"
mkdir -p "$wheel_dir"
python -m pip wheel . --no-build-isolation --no-deps -w "$wheel_dir" >/dev/null
python - <<'PY'
from pathlib import Path
import tarfile, zipfile
wheel=sorted(Path(".release-wheel").glob("*.whl"))[-1]
assert wheel.exists()
with zipfile.ZipFile(wheel) as z:
    names=z.namelist()
    assert not any(n.startswith('.git/') or '__pycache__' in n for n in names)
print('wheel:', wheel.name)
PY
printf '%s\n' 'release audit: PASS'
