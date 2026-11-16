# -*- mode: python ; coding: utf-8 -*-
"""
peptmass.spec
=============
Receita de empacotamento do PeptMass com PyInstaller (Windows / macOS / Linux).

Build:
    pyinstaller packaging/peptmass.spec --noconfirm --clean

Gera um diretório  dist/PeptMass/  (modo onedir, mais confiável e com
startup mais rápido). No macOS gera também  dist/PeptMass.app.

Para gerar UM único executável (onefile), defina a variável de ambiente
PEPTMASS_ONEFILE=1 antes de rodar o pyinstaller. Onefile é mais portátil
para distribuir, mas tem startup mais lento (extrai tudo num tempdir) e
pode irritar antivírus no Windows.

Ícone (opcional): se existir 'peptmass.ico' (Windows) ou 'peptmass.icns'
(macOS) na raiz do projeto, ele é usado automaticamente.
"""

import os
import sys

from PyInstaller.utils.hooks import collect_all

ONEFILE = os.environ.get("PEPTMASS_ONEFILE") == "1"
ROOT = os.path.dirname(SPECPATH)  # SPECPATH: pasta deste .spec (PyInstaller)

# ---------------------------------------------------------------------------
# O executavel abre a interface web (peptmass/web) numa janela propria
# (PyQt6-WebEngine), entao leva junto as telas, traducoes e arquivos
# estaticos do site.
#   - reportlab : fontes embutidas e arquivos de dados para PDF
#   - pyteomics/psims: leitura de mzML/mzXML
# PyQt6, PyQt6-WebEngine e openpyxl sao tratados pelos hooks do PyInstaller.
#
# O ThermoRawFileParser NAO vai no pacote: a licenca da biblioteca da Thermo
# restringe distribui-la junto com software GPL. Se a pessoa o instalar, o
# PeptMass o encontra (PEPTMASS_THERMO_PARSER, PATH) e abre .raw.
# ---------------------------------------------------------------------------
datas = []
binaries = []
hiddenimports = ["waitress"]

for pkg in ("reportlab", "pyteomics", "psims"):
    try:
        pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
    except Exception:
        continue
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

_web = os.path.join(ROOT, "peptmass", "web")
datas += [
    (os.path.join(_web, "templates"), os.path.join("peptmass", "web", "templates")),
    (os.path.join(_web, "static"), os.path.join("peptmass", "web", "static")),
    (os.path.join(_web, "locales"), os.path.join("peptmass", "web", "locales")),
    # icone da janela (mesmo mascote do site)
    (os.path.join(ROOT, "peptmass", "desktop", "assets"),
     os.path.join("peptmass", "desktop", "assets")),
]

# ---------------------------------------------------------------------------
# Ícone do executável
# ---------------------------------------------------------------------------
if sys.platform.startswith("win"):
    _icon_path = os.path.join(SPECPATH, "peptmass.ico")
elif sys.platform == "darwin":
    _icon_path = os.path.join(ROOT, "peptmass.icns")
else:
    _icon_path = None
icon = _icon_path if (_icon_path and os.path.exists(_icon_path)) else None


a = Analysis(
    [os.path.join(ROOT, "run_desktop.py")],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Evita conflito de múltiplos bindings Qt; matplotlib nao e usado pela
    # interface web (os graficos sao Plotly, no navegador embutido)
    excludes=["PyQt5", "PySide6", "PySide2", "tkinter", "test", "pytest",
              "matplotlib"],
    noarchive=False,
)

# Modulos QML/Quick do Qt nao sao usados (a janela e QtWidgets + WebEngine):
# tira-los encurta os caminhos (limite de 260 caracteres do Windows) e o pacote.
# As ferramentas de desenvolvedor do navegador embutido (~80 MB) tambem nao.
def _sem_qml(entries):
    return [e for e in entries
            if "/qml/" not in e[0].replace("\\", "/")
            and "/qml/" not in str(e[1]).replace("\\", "/")
            and "qtwebengine_devtools_resources" not in e[0]]


a.datas = _sem_qml(a.datas)
a.binaries = _sem_qml(a.binaries)

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
