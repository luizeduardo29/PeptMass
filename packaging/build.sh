#!/usr/bin/env bash
#
# build.sh
# ========
# Empacota o PeptMass com PyInstaller (macOS / Linux).
#
# Uso:
#   packaging/build.sh                 # build onedir em dist/PeptMass/ (+ PeptMass.app no macOS)
#   packaging/build.sh --onefile       # build onefile
#   packaging/build.sh --no-venv       # usa o Python atual sem criar venv
#
set -euo pipefail
cd "$(dirname "$0")/.."

ONEFILE=0
USE_VENV=1
for arg in "$@"; do
  case "$arg" in
    --onefile) ONEFILE=1 ;;
    --no-venv) USE_VENV=0 ;;
    *) echo "Argumento desconhecido: $arg" >&2; exit 2 ;;
  esac
done

PYTHON="python3"
if [ "$USE_VENV" -eq 1 ]; then
  if [ ! -d .venv-build ]; then
    echo "==> Criando venv de build (.venv-build)..."
    python3 -m venv .venv-build
  fi
  PYTHON="./.venv-build/bin/python"
fi

echo "==> Instalando dependencias..."
"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -r requirements/build.txt

echo "==> Rodando a suite cientifica (rede de seguranca)..."
"$PYTHON" tests/test_science.py

if [ "$ONEFILE" -eq 1 ]; then
  export PEPTMASS_ONEFILE=1
else
  unset PEPTMASS_ONEFILE || true
fi

echo "==> Empacotando com PyInstaller..."
"$PYTHON" -m PyInstaller packaging/peptmass.spec --noconfirm --clean

echo
echo "==> Pronto. Artefatos em ./dist/"
ls -la dist
