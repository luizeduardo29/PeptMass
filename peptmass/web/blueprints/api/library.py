"""Peptideos salvos, aminoacidos, modificacoes, PubChem e FASTA."""

from __future__ import annotations

import io
import json
import re

from flask import g, request, send_file

from peptmass.core.formula_parser import FormulaError, composition_mass, parse_formula
from peptmass.infra import exporters, pubchem
from peptmass.web.state import LOCK, get_state

from . import bp
from .common import ApiError, json_body, ok, peptide_definition

POSITIONS = ("residue", "N-term", "C-term")


def _rmods_list(raw) -> list:
    try:
        items = json.loads(raw or "[]")
    except (TypeError, ValueError):
        return []
    return [[int(i), str(m)] for i, m in items] if isinstance(items, list) else []


@bp.get("/api/peptides")
def peptides():
    with LOCK:
        rows = get_state().db.list_peptides()
    return ok(peptides=[row["name"] for row in rows])


@bp.get("/api/peptide")
def peptide_get():
    name = request.args.get("name", "")
    with LOCK:
        row = get_state().db.get_peptide(name)
    if not row:
        raise ApiError(g._("peptide.not_found", n=name), 404)
    return ok(name=row["name"], peptide={
        "sequence": row["sequence"], "nterm": row["n_term_mod"] or "",
        "cterm": row["c_term_mod"] or "", "rmods": _rmods_list(row["residue_mods"])})


@bp.post("/api/peptide")
def peptide_save():
    data = json_body()
    name = str(data.get("name") or "").strip()
    seq, nterm, cterm, rmods = peptide_definition(data)
    if not seq.strip():
        raise ApiError(g._("peptide.empty"))
    if not name:
        raise ApiError(g._("peptide.name_required"))
    with LOCK:
        db = get_state().db
        if db.get_peptide(name) and not data.get("overwrite"):
            raise ApiError(g._("peptide.exists", n=name), 409, exists=True)
        db.save_peptide(name, seq.strip(), nterm or "", cterm or "",
                        json.dumps([[i, m] for i, m in rmods.items()]))
    return ok(message=g._("peptide.saved", n=name))


@bp.delete("/api/peptide")
def peptide_delete():
    name = request.args.get("name", "")
    with LOCK:
        get_state().db.delete_peptide(name)
    return ok()


@bp.post("/api/residues")
def residue_add():
    data = json_body()
    fields = [str(data.get(k) or "").strip() for k in ("name", "three", "code", "formula")]
    with LOCK:
        st = get_state()
        try:
            st.custom_manager.add(*fields)
        except ValueError as exc:
            raise ApiError(str(exc)) from exc
        st.calc.refresh_table()
    return ok(message=g._("library.residue.added", c=fields[2]))


@bp.delete("/api/residues/<code>")
def residue_delete(code: str):
    with LOCK:
        st = get_state()
        res = st.custom_manager.get(code)
        if res is None:
            raise ApiError(g._("error.not_found"), 404)
        if res.builtin:
            raise ApiError(g._("library.residue.builtin", c=code))
        st.custom_manager.delete(code)
        st.calc.refresh_table()
    return ok()


def _mod_json(m, custom: set) -> dict:
    return {"name": m.name, "position": m.position,
            "targets": sorted(t for t in m.targets if t not in POSITIONS),
            "formula": m.formula_str, "delta": m.mono_delta,
            "custom": m.name in custom, "description": m.description}


@bp.get("/api/modifications")
def modifications():
    residue = request.args.get("residue")
    with LOCK:
        st = get_state()
        lib = st.mod_library
        if residue:
            mods = lib.for_residue(residue) or [
                m for m in lib.all() if m.position == "residue"]
        else:
            mods = lib.all()
        custom = set(st.custom_mod_ids())
        return ok(modifications=[_mod_json(m, custom) for m in mods])


@bp.post("/api/modifications")
def modification_add():
    data = json_body()
    name = str(data.get("name") or "").strip()
    formula = str(data.get("formula") or "").strip()
    position = str(data.get("position") or "residue")
    targets = re.sub(r"[^A-Za-z]", "", str(data.get("targets") or "")).upper()
    if not name:
        raise ApiError(g._("library.mod.name_required"))
    if position not in POSITIONS:
        raise ApiError(g._("library.mod.bad_position"))
    try:
        parse_formula(formula)
    except FormulaError as exc:
        raise ApiError(g._("library.invalid_formula", e=exc)) from exc
    with LOCK:
        st = get_state()
        if st.mod_library.get(name):
            raise ApiError(g._("library.mod.exists", n=name))
        st.add_modification(name, formula, targets, position)
    return ok(message=g._("library.mod.added", n=name))


@bp.delete("/api/modifications")
def modification_delete():
    name = request.args.get("name", "")
    with LOCK:
        if not get_state().delete_modification(name):
            raise ApiError(g._("library.mod.not_custom", n=name))
    return ok()


@bp.post("/api/formula")
def formula_preview():
    """Massa monoisotopica de uma formula: do residuo (livre - H2O) ou delta."""
    data = json_body()
    try:
        comp = parse_formula(str(data.get("formula") or ""))
        if data.get("mode") == "residue":
            comp = dict(comp)
            comp["H"] = comp.get("H", 0) - 2
            comp["O"] = comp.get("O", 0) - 1
        return ok(mono=composition_mass(comp, average=False))
    except FormulaError as exc:
        raise ApiError(str(exc)) from exc


@bp.post("/api/pubchem")
def pubchem_search():
    data = json_body()
    kind = data.get("kind", "name")
    query = str(data.get("query") or "").strip()
    if not query:
        raise ApiError(g._("pubchem.empty"))
    try:
        if kind == "cid":
            try:
                comp = pubchem.search_by_cid(int(query))
            except ValueError as exc:
                raise ApiError(g._("pubchem.bad_cid")) from exc
        elif kind == "formula":
            cids = pubchem.search_by_formula(query, max_results=1)
            if not cids:
                raise ApiError(g._("pubchem.no_formula"))
            comp = pubchem.search_by_cid(cids[0])
        else:
            comp = pubchem.search_by_name(query)
    except pubchem.PubChemError as exc:
        raise ApiError(str(exc), 502) from exc
    return ok(compound={
        "cid": comp.cid, "name": comp.name, "iupac": comp.iupac_name,
        "formula": comp.clean_formula, "mono": comp.free_mono_mass,
        "pubchem_mono": comp.pubchem_monoisotopic, "avg": comp.free_avg_mass})


@bp.get("/api/pubchem/<int:cid>.png")
def pubchem_png(cid: int):
    try:
        data = pubchem.fetch_structure_png(cid)
    except pubchem.PubChemError as exc:
        raise ApiError(str(exc), 502) from exc
    return send_file(io.BytesIO(data), mimetype="image/png", max_age=86400)


@bp.post("/api/fasta")
def fasta():
    entries = exporters.parse_fasta(str(json_body().get("text") or ""))
    return ok(entries=[{"header": h, "sequence": s} for h, s in entries])
