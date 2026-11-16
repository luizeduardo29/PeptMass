"""Instalacao do leitor de .raw (ThermoRawFileParser) pelo proprio usuario.

O executavel do PeptMass nao traz o ThermoRawFileParser: a licenca da
biblioteca RawFileReader, da Thermo, que vai junto com ele, restringe
distribui-la com software GPL. Em vez disso, o usuario baixa o conversor do
repositorio oficial (github.com/compomics/ThermoRawFileParser), le a licenca
da Thermo que vem no pacote e so entao o instala, em ~/.peptmass.

Fluxo: download() baixa a versao fixada, confere o SHA-256 e extrai numa
pasta provisoria, devolvendo os textos das licencas; accept() instala;
cancel() apaga o que foi baixado.
"""

from __future__ import annotations

import hashlib
import io
import os
import shutil
import sys
import urllib.error
import urllib.request
import zipfile

from peptmass.core.i18n import t as _

VERSION = "1.4.5"
URL = ("https://github.com/compomics/ThermoRawFileParser/releases/download/"
       f"v{VERSION}/ThermoRawFileParser{VERSION}.zip")
SHA256 = "be1f8fd6f85b20750d5f59c324f031882f911035ff4e93c4e98c9b2d73944b37"
MAX_BYTES = 30 * 1024 * 1024
_TIMEOUT = 60
_HEADERS = {"User-Agent": "PeptMass/1.0"}


class RawReaderError(Exception):
    pass


def base_dir() -> str:
    return os.path.join(os.path.expanduser("~"), ".peptmass")


def install_dir() -> str:
    """Pasta onde peptmass.infra.spectra_io.find_thermo_parser o procura."""
    return os.path.join(base_dir(), "ThermoRawFileParser")


def _staging_dir() -> str:
    return os.path.join(base_dir(), "ThermoRawFileParser.baixando")


def supported() -> bool:
    """O pacote baixado e o build .NET Framework: roda direto no Windows."""
    return sys.platform == "win32"


def _fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers=_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            data = resp.read(MAX_BYTES + 1)
    except urllib.error.URLError as exc:
        raise RawReaderError(
            _("Não foi possível baixar o leitor de .raw: {e}").format(
                e=getattr(exc, "reason", exc))) from exc
    if len(data) > MAX_BYTES:
        raise RawReaderError(_("O download do leitor de .raw veio maior que o esperado."))
    return data


def _read_text(folder: str, name: str) -> str:
    path = os.path.join(folder, name)
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        return f.read().decode("utf-8", errors="replace").replace("\r\n", "\n").strip()


def download(fetch=_fetch) -> dict:
    """Baixa e confere o pacote; devolve as licencas para o usuario aceitar."""
    data = fetch(URL)
    if hashlib.sha256(data).hexdigest() != SHA256:
        raise RawReaderError(_("O arquivo baixado não confere com a versão "
                               "oficial do leitor de .raw. Nada foi instalado."))
    staging = _staging_dir()
    shutil.rmtree(staging, ignore_errors=True)
    os.makedirs(staging)
    root = os.path.realpath(staging)
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for info in zf.infolist():
                target = os.path.realpath(os.path.join(staging, info.filename))
                if not target.startswith(root + os.sep):
                    raise RawReaderError(_("Pacote do leitor de .raw inválido."))
            zf.extractall(staging)
    except zipfile.BadZipFile as exc:
        shutil.rmtree(staging, ignore_errors=True)
        raise RawReaderError(_("Pacote do leitor de .raw inválido.")) from exc
    except RawReaderError:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    if not os.path.exists(os.path.join(staging, "ThermoRawFileParser.exe")):
        shutil.rmtree(staging, ignore_errors=True)
        raise RawReaderError(_("Pacote do leitor de .raw inválido."))
    return {"version": VERSION,
            "thermo_license": _read_text(staging, "THERMO_LICENSE"),
            "license": _read_text(staging, "LICENSE")}


def accept() -> str:
    """Instala o que foi baixado (depois que o usuario aceitou a licenca)."""
    staging = _staging_dir()
    if not os.path.isdir(staging):
        raise RawReaderError(_("Baixe o leitor de .raw antes de instalar."))
    target = install_dir()
    shutil.rmtree(target, ignore_errors=True)
    os.replace(staging, target)
    return os.path.join(target, "ThermoRawFileParser.exe")


def cancel() -> None:
    shutil.rmtree(_staging_dir(), ignore_errors=True)


def installed() -> bool:
    return os.path.exists(os.path.join(install_dir(), "ThermoRawFileParser.exe"))
