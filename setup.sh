#!/usr/bin/env bash
#
# Create the radcoolpv environment.
#
#   ./setup.sh                                  # venv at ~/.venvs/radcoolpv-py
#   VENV_DIR=/path/to/venv ./setup.sh           # somewhere else
#
# The venv deliberately lives OUTSIDE the repo. A venv inside an iCloud-synced
# folder (~/Documents, ~/Desktop) gets marked hidden by macOS, and Python skips
# hidden .pth files - which silently disables the editable install.
#
# Live optics also needs the Stanford S4 module, built from source; see README.
set -euo pipefail
cd "$(dirname "$0")"

VENV="${VENV_DIR:-$HOME/.venvs/radcoolpv-py}"
echo "==> $(python3 --version) -> venv at $VENV"
python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install -q --upgrade pip
"$VENV/bin/python" -m pip install -q -r requirements.txt
"$VENV/bin/python" -m pip install -q -e .

# Verify from / so the current directory cannot mask a broken install.
( cd / && "$VENV/bin/python" -c "import radcoolpv; print('==> radcoolpv OK:', radcoolpv.__file__)" )
( cd / && "$VENV/bin/python" -c "import importlib.util as u; print('==> S4:', 'available' if u.find_spec('S4') else 'not built (live optics unavailable)')" )

echo "==> Done. Activate with:  source $VENV/bin/activate"
