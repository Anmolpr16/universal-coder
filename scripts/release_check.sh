#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/src"
python -m compileall -q src
python -m pytest -q
python - <<'PY'
import universal_coder
assert universal_coder.__version__ == '1.2.0'
print('release version:', universal_coder.__version__)
PY
