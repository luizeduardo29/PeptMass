# -*- mode: python ; coding: utf-8 -*-
"""
peptmass.spec
=============
Receita de empacotamento do PeptMass com PyInstaller (Windows / macOS / Linux).

Build:
    pyinstaller peptmass.spec --noconfirm --clean

Gera um diretório  dist/PeptMass/  (modo onedir, mais confiável e com
startup mais rápido). No macOS gera também  dist/PeptMass.app.

Para gerar UM único executável (onefile), defina a variável de ambiente
PEPTMASS_ONEFILE=1 antes de rodar o pyinstaller. Onefile é mais portátil
para distribuir, mas tem startup mais lento (extrai tudo num tempdir) e
pode irritar antivírus no Windows.

Ícone (opcional): se existir 'peptmass.ico' (Windows) ou 'peptmass.icns'
(macOS) ao lado deste arquivo, ele é usado automaticamente.
"""

import os
import sys

from PyInstaller.utils.hooks import collect_all

ONEFILE = os.environ.get("PEPTMASS_ONEFILE") == "1"

# ---------------------------------------------------------------------------
# Coleta de dependências que precisam de dados/submódulos além do .py
#   - matplotlib: dados (fontes, mpl-data) + backend QtAgg
#   - reportlab : fontes embutidas e arquivos de dados para PDF
# PyQt6 e openpyxl são tratados pelos hooks nativos do PyInstaller.
# ---------------------------------------------------------------------------
datas = []
binaries = []
hiddenimports = [
    "matplotlib.backends.backend_qtagg",
    "PyQt6.QtPrintSupport",  # usado pelo backend Qt de impressão/exportação
]

for pkg in ("matplotlib", "reportlab", "pyteomics", "psims"):
    try:
        pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
    except Exception:
        continue  # pacote opcional ausente: a aba experimental fica desativada
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

# Bundle opcional do ThermoRawFileParser (para abrir .raw direto), se a pasta
# 'ThermoRawFileParser/' existir ao lado do .spec.
_trfp = os.path.join(os.getcwd(), "ThermoRawFileParser")
if os.path.isdir(_trfp):
    datas += [(_trfp, "ThermoRawFileParser")]

# ---------------------------------------------------------------------------
# Ícone opcional (resolvido em relação à pasta do .spec)
# ---------------------------------------------------------------------------
_here = os.path.abspath(os.getcwd())
if sys.platform.startswith("win"):
    _icon_path = os.path.join(_here, "peptmass.ico")
elif sys.platform == "darwin":
    _icon_path = os.path.join(_here, "peptmass.icns")
else:
    _icon_path = None
icon = _icon_path if (_icon_path and os.path.exists(_icon_path)) else None


a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Evita conflito de múltiplos bindings Qt (causa comum de falha com matplotlib)
    excludes=["PyQt5", "PySide6", "PySide2", "tkinter", "test", "pytest"],
    noarchive=False,
)

pyz = PYZ(a.pure)

if ONEFILE:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name="PeptMass",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,          # app GUI: sem janela de console
        icon=icon,
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="PeptMass",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        icon=icon,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name="PeptMass",
    )

# Bundle .app no macOS
if sys.platform == "darwin":
    _target = exe if ONEFILE else coll
    app = BUNDLE(
        _target,
        name="PeptMass.app",
        icon=icon,
        bundle_identifier="org.peptmass.app",
        info_plist={
            "CFBundleName": "PeptMass",
            "CFBundleDisplayName": "PeptMass",
            "NSHighResolutionCapable": True,
        },
    )
