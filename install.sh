#!/usr/bin/env bash
#
# Install all dependencies for radcoolpv.
#
#   ./install.sh             # create a .venv and install everything into it
#   ./install.sh --with-s4   # also install system libs + build the S4 Python module
#   ./install.sh --system    # install into the current Python instead of a venv
#
# By default a local virtual environment (.venv) is created so the install is
# hermetic and works on managed system Pythons (Homebrew, PEP 668). If you are
# already inside a virtual environment, that one is used.
#
# The Python deps cover the thermal stage, free-form optics, and resuming from
# existing OUTPUTS4 folders. The live RCWA optics stage (geometry.source: s4)
# additionally needs the S4 Python module, built from source (see --with-s4).
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON="${PYTHON:-python3}"
VENV_DIR="${VENV_DIR:-.venv}"
USE_VENV=1
WITH_S4=0
for arg in "$@"; do
  case "$arg" in
    --with-s4) WITH_S4=1 ;;
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
# S4 RCWA Python module (optional, only needed for live optics).
# --------------------------------------------------------------------------- #
install_s4() {
  echo "==> Installing S4 build dependencies"
  case "$(uname -s)" in
    Darwin)
      if command -v brew >/dev/null 2>&1; then
        brew install fftw openblas lapack boost || true
      else
        echo "!! Homebrew not found. Install it (https://brew.sh), then:"
        echo "     brew install fftw openblas lapack boost"
        return 1
      fi ;;
    Linux)
      if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update
        sudo apt-get install -y build-essential libfftw3-dev libopenblas-dev \
          liblapack-dev libboost-dev
      else
        echo "!! Non-apt Linux: install a C/C++ toolchain plus FFTW3, BLAS/LAPACK,"
        echo "   and Boost development packages with your package manager."
      fi ;;
    *)
      echo "!! Unsupported OS for automatic S4 deps; install FFTW3 + BLAS/LAPACK manually." ;;
  esac

  echo "==> Building the S4 Python module from source (phoebe-p/S4 fork)"
  "$PYTHON" -m pip install "git+https://github.com/phoebe-p/S4.git"
}

if "$PYTHON" -c "import S4" >/dev/null 2>&1; then
  echo "==> S4 Python module: already available."
elif [ "$WITH_S4" -eq 1 ]; then
  if install_s4 && "$PYTHON" -c "import S4" >/dev/null 2>&1; then
    echo "==> S4 Python module: installed."
  else
    cat <<'EOF'
!! S4 did not install cleanly. Build it manually:
     git clone https://github.com/phoebe-p/S4.git
     cd S4 && make S4_pyext      # or: pip install .
   You need a C/C++ compiler plus FFTW3 and BLAS/LAPACK development libraries.
   (S4 is only required for geometry.source: s4 — everything else runs without it.)
EOF
  fi
else
  cat <<'EOF'
==> S4 Python module: not installed (skipped).
    The live RCWA optics stage (geometry.source: s4) needs it. To add it:
      ./install.sh --with-s4
    The thermal stage, free-form optics, and resuming from OUTPUTS4 folders all
    work without S4.
EOF
fi

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
try:
    importlib.import_module("S4")
    print("   [ok]   S4 (live optics available)")
except Exception:
    print("   [--]   S4 (optional; live optics disabled)")
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
