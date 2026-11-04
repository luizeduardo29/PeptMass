"""Estado do servidor: um Workspace por processo e os arquivos de MS abertos.

Um unico estado por processo, protegido por uma trava: o SQLite e as tabelas
de residuos/modificacoes sao compartilhados entre as requisicoes. O peptideo em
edicao NAO mora aqui: cada tela manda a definicao dele (sequencia + mods) e o
servidor recalcula, como o desktop faz a cada tecla.

Os arquivos de MS abertos na tela "Dados experimentais" ficam num cache pequeno
(RUNS), com o arquivo enviado gravado na pasta de dados.
"""

from __future__ import annotations

import os
import shutil
import threading
import time
import uuid

from peptmass.core.workspace import Workspace
from peptmass.infra.database import Database

LOCK = threading.RLock()


def data_dir() -> str:
    """PEPTMASS_DATA_DIR manda (container: /data); senao ~/.peptmass, a mesma
    pasta do desktop, entao os dois enxergam o mesmo banco."""
    path = os.environ.get("PEPTMASS_DATA_DIR") or os.path.join(
        os.path.expanduser("~"), ".peptmass")
    os.makedirs(path, exist_ok=True)
    return path


_STATE: Workspace | None = None


def get_state() -> Workspace:
    global _STATE
    with LOCK:
        if _STATE is None:
            _STATE = Workspace(Database(os.path.join(data_dir(), "peptmass.db")))
        return _STATE


# ---------------------------------------------------------------------------
# Arquivos de MS abertos (tela "Dados experimentais")
# ---------------------------------------------------------------------------
MAX_RUNS = 3
RUNS: dict[str, dict] = {}


def uploads_dir() -> str:
    path = os.path.join(data_dir(), "uploads")
    os.makedirs(path, exist_ok=True)
    return path


def new_upload_dir() -> tuple[str, str]:
    rid = uuid.uuid4().hex[:12]
    path = os.path.join(uploads_dir(), rid)
    os.makedirs(path, exist_ok=True)
    return rid, path


def add_run(rid: str, run, folder: str, filename: str) -> None:
    with LOCK:
        RUNS[rid] = {"run": run, "folder": folder, "filename": filename,
                     "opened": time.time(), "peaks": {}}
        while len(RUNS) > MAX_RUNS:
            oldest = min(RUNS, key=lambda k: RUNS[k]["opened"])
            drop_run(oldest)


def get_run(rid: str):
    with LOCK:
        return RUNS.get(rid)


def drop_run(rid: str) -> None:
    entry = RUNS.pop(rid, None)
    if not entry:
        return
    try:
        entry["run"].close()
    except Exception:  # noqa: BLE001 - fechar e' melhor esforco
        pass
    shutil.rmtree(entry["folder"], ignore_errors=True)


def clear_stale_uploads() -> None:
    """Na subida: apaga envios de execucoes anteriores (o cache e' em memoria)."""
    shutil.rmtree(uploads_dir(), ignore_errors=True)
