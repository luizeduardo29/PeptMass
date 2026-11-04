"""Estado do servidor: banco, bibliotecas e calculadora (o AppState do desktop).

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

from database import Database
from custom_residues import CustomResidueManager
from modifications import (ModificationLibrary, Modification,
                           DEFAULT_MODIFICATIONS)
from formula_parser import parse_formula, FormulaError
from mass_calculator import MassCalculator
from presets import GLP_PRESETS, DOPING_PRESETS, migrate_preset_names

LOCK = threading.RLock()

# Presets nossos renomeados/corrigidos (o mesmo do gui.AppState): removidos so
# se o usuario nao os editou.
_OBSOLETE_PRESETS = {
    "Timosina beta-4 (TB-500)":
        "SDKPDMAEIEKFDKSKLKKTETQEKNPLPSKETIEQEKQAGES",
}


def data_dir() -> str:
    """PEPTMASS_DATA_DIR manda (container: /data); senao ~/.peptmass, a mesma
    pasta do desktop, entao os dois enxergam o mesmo banco."""
    path = os.environ.get("PEPTMASS_DATA_DIR") or os.path.join(
        os.path.expanduser("~"), ".peptmass")
    os.makedirs(path, exist_ok=True)
    return path


class AppState:
    def __init__(self, path: str):
        self.db = Database(os.path.join(path, "peptmass.db"))
        self.custom_manager = CustomResidueManager(self.db)
        self.mod_library = ModificationLibrary(custom=self._load_custom_mods())
        self.calc = MassCalculator(self.custom_manager, self.mod_library)
        self._seed_presets()

    def _seed_presets(self):
        for name, seq in _OBSOLETE_PRESETS.items():
            row = self.db.get_peptide(name)
            if row and row["sequence"] == seq:
                self.db.delete_peptide(name)
        migrate_preset_names(self.db)
        for flag, presets in (("glp_presets_seeded", GLP_PRESETS),
                              ("doping_presets_seeded_v9", DOPING_PRESETS)):
            if self.db.get_meta(flag):
                continue
            for entry in presets:
                name, seq, nt, ct = entry[:4]
                rmods = entry[4] if len(entry) > 4 else "[]"
                if not self.db.get_peptide(name):
                    self.db.save_peptide(name, seq, nt, ct, rmods)
            self.db.set_meta(flag, "1")

    def _load_custom_mods(self):
        mods = []
        for row in self.db.list_modifications():
            try:
                mods.append(_mod_from_row(row))
            except FormulaError:
                pass
        return mods

    def custom_mod_rows(self):
        """{nome: id} das modificacoes criadas pelo usuario (as do banco)."""
        return {row["name"]: row["id"] for row in self.db.list_modifications()}

    def add_modification(self, name, formula, targets, position):
        self.db.add_modification(name, formula, targets, position)
        tset = frozenset(targets) if targets else frozenset({position})
        self.mod_library.add(Modification(
            name=name, composition=parse_formula(formula), targets=tset,
            position=position))

    def delete_modification(self, name):
        mid = self.custom_mod_rows().get(name)
        if mid is None:
            return False
        self.db.delete_modification(mid)
        self.mod_library.remove(name)
        # uma custom antiga pode ter sombreado uma padrao de mesmo nome
        for mod in DEFAULT_MODIFICATIONS:
            if mod.name == name:
                self.mod_library.add(mod)
        return True


def _mod_from_row(row):
    targets = (frozenset(row["targets"]) if row["targets"]
               else frozenset({row["position"]}))
    return Modification(
        name=row["name"], composition=parse_formula(row["formula"]),
        targets=targets, position=row["position"],
        description=row.get("description") or "")


_STATE: AppState | None = None


def get_state() -> AppState:
    global _STATE
    with LOCK:
        if _STATE is None:
            _STATE = AppState(data_dir())
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
