#!/usr/bin/env bash
#
# Install all dependencies for radcoolpv.
#
#   ./install.sh             # create a .venv and install everything into it
#   ./install.sh --system    # install into the current Python instead of a venv
#
# By default a local virtual environment (.venv) is created so the install is
# hermetic and works on managed system Pythons (Homebrew, PEP 668). If you are
# already inside a virtual environment, that one is used.
#
# The pip dependencies are pure Python. The live RCWA optics stage additionally
# needs the Stanford S4 module, which has no PyPI package and is built from
# source - see README. Everything else runs without it.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON="${PYTHON:-python3}"
VENV_DIR="${VENV_DIR:-.venv}"
USE_VENV=1
for arg in "$@"; do
  case "$arg" in
    --system)  USE_VENV=0 ;;
    -h|--help)
      grep '^#' "$0" | sed 's/^# \{0,1\}//' | sed '1d'
      exit 0 ;;
    *) echo "Unknown option: $arg (use -h for help)"; exit 2 ;;
  esac
done

trap 'echo; echo "!! Install failed. See the error above. On a managed system Python"; \
      echo "   you can also retry inside a fresh venv:"; \
      echo "     python3 -m venv .venv && source .venv/bin/activate && ./install.sh --system"' ERR

in_venv() { "$1" -c 'import sys; raise SystemExit(0 if sys.prefix!=sys.base_prefix else 1)' 2>/dev/null; }

echo "==> Base Python: $($PYTHON --version 2>&1) ($PYTHON)"

CREATED_VENV=0
if in_venv "$PYTHON"; then
  echo "==> Already inside a virtual environment; using it."
elif [ "$USE_VENV" -eq 1 ]; then
  echo "==> Creating virtual environment: $VENV_DIR"
  "$PYTHON" -m venv "$VENV_DIR"
  PYTHON="$VENV_DIR/bin/python"
  CREATED_VENV=1
else
  echo "==> Installing into the current Python (--system)."
fi

echo "==> Upgrading pip (best effort)"
"$PYTHON" -m pip install --upgrade pip >/dev/null 2>&1 \
  || echo "    (could not upgrade pip; continuing with the existing version)"

echo "==> Installing Python dependencies (requirements.txt)"
"$PYTHON" -m pip install -r requirements.txt

echo "==> Installing radcoolpv (editable)"
"$PYTHON" -m pip install -e .

# --------------------------------------------------------------------------- #
# Verify the install.
# --------------------------------------------------------------------------- #
echo "==> Verifying installation"
"$PYTHON" - <<'PY'
import importlib
ok = True
for m in ("numpy", "scipy", "matplotlib", "yaml", "openpyxl", "radcoolpv"):
    try:
        importlib.import_module(m)
        print(f"   [ok]   {m}")
    except Exception as exc:
        ok = False
        print(f"   [FAIL] {m}: {exc}")
print("\nInstallation OK." if ok else "\nInstallation INCOMPLETE.")
PY

trap - ERR
echo
echo "==> Done."
if [ "$CREATED_VENV" -eq 1 ]; then
  echo "    Activate the environment, then run a config:"
  echo "      source $VENV_DIR/bin/activate"
  echo "      radcoolpv run configs/freeform.yaml"
else
  echo "    Try:  radcoolpv run configs/freeform.yaml"
fi
