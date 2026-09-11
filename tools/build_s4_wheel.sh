#!/usr/bin/env bash
#
# Build the S4 optical solver as a pip-installable wheel for Google Colab.
#
# Run this ONCE, inside a fresh Colab runtime, whenever Colab changes its Python
# version (a wheel is tied to one). It takes about ten minutes. Then attach the
# wheel it prints to the GitHub release tagged `s4-wheels` and make sure the
# notebook's S4_WHEEL URL names it:
#
#   !bash radcoolpv-py/tools/build_s4_wheel.sh
#   gh release upload s4-wheels wheelhouse/S4-*.whl --clobber
#
# With --install the wheel is also installed into the running interpreter; the
# notebook uses that as its fallback when no prebuilt wheel fits.
#
# S4 is C++ linked against BLAS/LAPACK, FFTW, CHOLMOD and Boost.Serialization;
# auditwheel copies those shared libraries into the wheel so that `pip install
# S4-*.whl` needs nothing else on the target machine.
set -euo pipefail

S4_COMMIT=9569f5e555b967a4324eb1ea593d0f9f40761a61   # the tested revision
SRC=${S4_SRC:-/content/S4}
OUT=${S4_WHEELHOUSE:-$PWD/wheelhouse}

apt-get -qq update
apt-get -qq install -y build-essential git libboost-all-dev libfftw3-dev \
    liblapack-dev libopenblas-dev libsuitesparse-dev patchelf
python3 -m pip install -q --upgrade pip wheel setuptools auditwheel numpy

if [ ! -d "$SRC" ]; then
    git clone -q https://github.com/phoebe-p/S4.git "$SRC"
fi
git -C "$SRC" checkout -q "$S4_COMMIT"

# `make S4_pyext` compiles libS4.a, writes setup.py, and pip-installs. Reuse
# that setup.py and library to build a wheel, then bundle the shared libraries.
make -C "$SRC" -j"$(nproc)" S4_pyext
python3 -m pip wheel "$SRC" --no-build-isolation --no-deps -w "$SRC/dist"
python3 -m auditwheel repair "$SRC"/dist/S4-*-linux_x86_64.whl \
    --plat "manylinux_2_35_x86_64" -w "$OUT"

if [ "${1:-}" = "--install" ]; then
    python3 -m pip install -q --force-reinstall "$OUT"/S4-*.whl
fi
python3 -c "import S4, sys; print('S4 imports on', sys.version.split()[0])"
echo "Wheel: $(ls "$OUT"/S4-*.whl)"
