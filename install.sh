#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PYTHON=${PYTHON:-python3}
"$PYTHON" -m pip install --no-build-isolation "$ROOT"
printf '%s\n' 'Universal Coder installed. Run: coder --help'
