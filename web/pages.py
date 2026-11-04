"""Telas: Inicio, Massa, Fragmentacao, Dados experimentais e Biblioteca.

As telas sao HTML do servidor (Jinja) com o comportamento em JavaScript
(static/*.js) falando com a API (api.py). A Aba 4 do desktop
(Sequenciamento) continua oculta, como na v1.0.
"""

from __future__ import annotations

import json

from flask import Blueprint, render_template

from formula_parser import FormulaError
from mass_calculator import SequenceError

from .state import LOCK, get_state

bp = Blueprint("pages", __name__)


def _saved_peptides(st):
    """Peptideos salvos com a massa monoisotopica (o "-" se nao calcular)."""
    out = []
    for row in st.db.list_peptides():
        try:
            rmods = {int(i): str(m) for i, m in json.loads(row["residue_mods"] or "[]")}
        except (TypeError, ValueError):
            rmods = {}
        mono = None
        try:
            ok, _msg = st.calc.validate_sequence(row["sequence"])
            if ok:
                mono = st.calc.parse(row["sequence"], n_term_mod=row["n_term_mod"] or None,
                                     c_term_mod=row["c_term_mod"] or None,
                                     residue_mods=rmods).mono_mass
        except (SequenceError, FormulaError):
            mono = None
        out.append({"name": row["name"], "sequence": row["sequence"],
                    "nterm": row["n_term_mod"] or "", "cterm": row["c_term_mod"] or "",
                    "n_mods": len(rmods), "mono": mono})
    return out


@bp.get("/")
def home():
    with LOCK:
        st = get_state()
        residues = st.custom_manager.all()
        mods = st.mod_library.all()
        custom_mods = st.custom_mod_rows()
        peptides = _saved_peptides(st)
    stats = {
        "peptides": len(peptides),
        "residues": len(residues),
        "residues_builtin": sum(1 for r in residues if r.builtin),
        "mods": len(mods),
        "mods_custom": len(custom_mods),
    }
    return render_template("home.html", stats=stats, peptides=peptides)


@bp.get("/massa")
def mass():
    with LOCK:
        st = get_state()
        lib = st.mod_library
        nterm = [m.name for m in lib.for_position("N-term")]
        cterm = [m.name for m in lib.for_position("C-term")]
        peptides = [row["name"] for row in st.db.list_peptides()]
    return render_template("mass.html", nav_active="mass", nterm_mods=nterm,
                           cterm_mods=cterm, peptides=peptides)


@bp.get("/fragmentacao")
def fragments():
    return render_template("fragments.html", nav_active="fragments")


@bp.get("/experimental")
def experimental():
    return render_template("experimental.html", nav_active="experimental")


@bp.get("/biblioteca")
def library():
    with LOCK:
        st = get_state()
        residues = sorted(st.custom_manager.all(), key=lambda r: (r.builtin, r.code.lower()))
        custom = set(st.custom_mod_rows())
        mods = sorted(st.mod_library.all(),
                      key=lambda m: (m.name not in custom, m.position, m.name.lower()))
    return render_template("library.html", nav_active="library", residues=residues,
                           mods=mods, custom_mods=custom)
