"""Base da API: erro padrao, leitura segura da entrada e o peptideo em edicao.

Cada tela manda a definicao do peptideo:
    {"peptide": {"sequence": "...", "nterm": "Acetyl", "cterm": "",
                 "rmods": [[indice_0, "Oxidation"], ...]}}
e o servidor recalcula. Erros de entrada voltam como
{"ok": false, "error": "<mensagem no idioma da tela>"}.
"""

from __future__ import annotations

import math

from flask import g, jsonify, request

from peptmass.core.formula_parser import FormulaError
from peptmass.core.fragmentation import NEUTRAL_LOSSES, generate_fragments
from peptmass.core.mass_calculator import SequenceError
from peptmass.web.state import get_state

ION_TYPES = ("a", "b", "c", "x", "y", "z", "z+1")


class ApiError(Exception):
    def __init__(self, message: str, status: int = 400, **extra):
        super().__init__(message)
        self.message = message
        self.status = status
        self.extra = extra


def ok(**payload):
    return jsonify(ok=True, **payload)


def json_body() -> dict:
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def bounded_float(value, default: float, lo: float | None = None,
           hi: float | None = None) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(out):
        return default
    if lo is not None:
        out = max(lo, out)
    if hi is not None:
        out = min(hi, out)
    return out


def bounded_int(value, default: int, lo: int | None = None, hi: int | None = None) -> int:
    try:
        out = int(value)
    except (TypeError, ValueError):
        return default
    if lo is not None:
        out = max(lo, out)
    if hi is not None:
        out = min(hi, out)
    return out


def parse_numbers(raw) -> list[float]:
    """Lista de m/z colada: um por linha ou separados por virgula/espaco."""
    if isinstance(raw, list):
        items = raw
    else:
        items = str(raw or "").replace(",", " ").replace(";", " ").split()
    out = []
    for tok in items:
        try:
            val = float(tok)
        except (TypeError, ValueError):
            continue
        if math.isfinite(val):
            out.append(val)
    return out


def peptide_definition(data: dict):
    p = data.get("peptide") if isinstance(data.get("peptide"), dict) else {}
    seq = str(p.get("sequence") or "")
    nterm = str(p.get("nterm") or "") or None
    cterm = str(p.get("cterm") or "") or None
    rmods = {}
    for item in p.get("rmods") or []:
        try:
            rmods[int(item[0])] = str(item[1])
        except (TypeError, ValueError, IndexError):
            continue
    return seq, nterm, cterm, rmods


def parse_peptide(data: dict):
    """PeptideResult do peptideo enviado, ou ApiError com a mensagem."""
    st = get_state()
    seq, nterm, cterm, rmods = peptide_definition(data)
    if not seq.strip():
        raise ApiError(g._("peptide.none"), code="no_peptide")
    valid, msg = st.calc.validate_sequence(seq)
    if not valid:
        raise ApiError(msg)
    try:
        return st.calc.parse(seq, n_term_mod=nterm, c_term_mod=cterm,
                             residue_mods=rmods)
    except (SequenceError, FormulaError) as exc:
        raise ApiError(str(exc)) from exc


def peptide_summary(r) -> dict:
    return {
        "sequence": r.sequence,
        "mono": r.mono_mass,
        "avg": r.avg_mass,
        "formula": r.formula,
        "nterm": r.n_term_mod.name if r.n_term_mod else "",
        "cterm": r.c_term_mod.name if r.c_term_mod else "",
        "n_chains": getattr(r, "n_chains", 1),
        "n_residues": len(r.residues),
        "warnings": list(r.warnings),
    }


def fragment_options(data: dict):
    ions = [i for i in data.get("ions") or [] if i in ION_TYPES]
    losses = [nl for nl in data.get("losses") or [] if nl in NEUTRAL_LOSSES]
    charges = sorted({bounded_int(z, 1, 1, 10) for z in data.get("charges") or []}) or [1]
    no_loss = bool(data.get("no_loss", True))
    return ions, losses, charges, no_loss


def build_fragments(r, ions, charges, losses, no_loss):
    return generate_fragments(
        r, ion_types=ions, charges=charges, neutral_losses=losses,
        include_no_loss=no_loss,
        n_term_delta=r.n_term_mod.mono_delta if r.n_term_mod else 0.0,
        c_term_delta=r.c_term_mod.mono_delta if r.c_term_mod else 0.0)
