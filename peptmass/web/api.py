"""API JSON das telas (e as exportacoes, que devolvem arquivo).

Cada tela manda a definicao do peptideo em edicao:
    {"peptide": {"sequence": "...", "nterm": "Acetyl", "cterm": "",
                 "rmods": [[indice_0, "Oxidation"], ...]}}
e o servidor recalcula com o mesmo nucleo do desktop (mass_calculator,
fragmentation, scoring, identification). Erros de entrada voltam como
{"ok": false, "error": "<mensagem no idioma da tela>"}.
"""

from __future__ import annotations

import io
import json
import math
import os
import re
import shutil
import tempfile

from flask import Blueprint, g, jsonify, request, send_file

from peptmass.infra import exporters
from peptmass.core import identification
from peptmass.infra import pubchem
from peptmass.core import scoring
from peptmass.infra import spectra_io
from peptmass.core.constants import PROTON_MASS
from peptmass.core.formula_parser import parse_formula, composition_mass, FormulaError
from peptmass.core.fragmentation import generate_fragments, match_experimental, NEUTRAL_LOSSES
from peptmass.core.mass_calculator import SequenceError

from . import state
from .state import LOCK, get_state

bp = Blueprint("api", __name__)

ION_TYPES = ("a", "b", "c", "x", "y", "z", "z+1")
POSITIONS = ("residue", "N-term", "C-term")
EXPORT_FORMATS = ("csv", "xlsx", "pdf", "txt", "skyline")


class ApiError(Exception):
    def __init__(self, message: str, status: int = 400, **extra):
        super().__init__(message)
        self.message = message
        self.status = status
        self.extra = extra


@bp.errorhandler(ApiError)
def _api_error(exc: ApiError):
    return jsonify(ok=False, error=exc.message, **exc.extra), exc.status


def _ok(**payload):
    return jsonify(ok=True, **payload)


def _body() -> dict:
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _float(value, default: float, lo: float | None = None,
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


def _int(value, default: int, lo: int | None = None, hi: int | None = None) -> int:
    try:
        out = int(value)
    except (TypeError, ValueError):
        return default
    if lo is not None:
        out = max(lo, out)
    if hi is not None:
        out = min(hi, out)
    return out


def _numbers(raw) -> list[float]:
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


# ---------------------------------------------------------------------------
# Peptideo
# ---------------------------------------------------------------------------
def _peptide_def(data: dict):
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


def _parse_peptide(data: dict):
    """PeptideResult do peptideo enviado, ou ApiError com a mensagem."""
    st = get_state()
    seq, nterm, cterm, rmods = _peptide_def(data)
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


def _summary(r) -> dict:
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


@bp.post("/api/mass")
def mass():
    data = _body()
    seq, nterm, cterm, rmods = _peptide_def(data)
    with LOCK:
        st = get_state()
        calc = st.calc
        valid, msg = calc.validate_sequence(seq)
        out = {
            "valid": valid,
            "message": msg,
            "codes": calc.residue_codes(seq),
            "unknown": [] if valid else calc.unknown_codes(seq),
        }
        if not valid:
            return _ok(**out)
        try:
            r = calc.parse(seq, n_term_mod=nterm, c_term_mod=cterm,
                           residue_mods=rmods)
        except (SequenceError, FormulaError) as exc:
            out.update(valid=False, message=str(exc))
            return _ok(**out)
        zmin = _int(data.get("zmin"), 1, 1, 200)
        zmax = _int(data.get("zmax"), 10, 1, 200)
        charges = set(range(zmin, max(zmin, zmax) + 1))
        for tok in str(data.get("zextra") or "").split(","):
            tok = tok.strip()
            if tok.isdigit() and 0 < int(tok) <= 1000:
                charges.add(int(tok))
        out["result"] = _summary(r)
        out["charges"] = [[z, mz] for z, mz in calc.charge_table(
            r.mono_mass, sorted(charges))]
        out["isotopes"] = [[m, i] for m, i in calc.isotopic_distribution(
            r.composition, max_peaks=12)]
    return _ok(**out)


# ---------------------------------------------------------------------------
# Fragmentacao MS/MS
# ---------------------------------------------------------------------------
def _frag_options(data: dict):
    ions = [i for i in data.get("ions") or [] if i in ION_TYPES]
    losses = [nl for nl in data.get("losses") or [] if nl in NEUTRAL_LOSSES]
    charges = sorted({_int(z, 1, 1, 10) for z in data.get("charges") or []}) or [1]
    no_loss = bool(data.get("no_loss", True))
    return ions, losses, charges, no_loss


def _fragments_for(r, ions, charges, losses, no_loss):
    return generate_fragments(
        r, ion_types=ions, charges=charges, neutral_losses=losses,
        include_no_loss=no_loss,
        n_term_delta=r.n_term_mod.mono_delta if r.n_term_mod else 0.0,
        c_term_delta=r.c_term_mod.mono_delta if r.c_term_mod else 0.0)


def _frag_json(i: int, f) -> dict:
    return {"i": i, "ion": f"{f.ion_type}{f.number}", "type": f.ion_type,
            "label": f.label, "z": f.charge, "mz": f.mz,
            "loss": f.neutral_loss, "neutral": f.neutral_mass, "seq": f.sequence}


@bp.post("/api/fragments")
def fragments():
    data = _body()
    with LOCK:
        r = _parse_peptide(data)
        out = {"peptide": _summary(r), "multi_chain": r.n_chains > 1,
               "fragments": [], "matches": None}
        if r.n_chains > 1:
            return _ok(**out)
        ions, losses, charges, no_loss = _frag_options(data)
        frags = _fragments_for(r, ions, charges, losses, no_loss)
    out["fragments"] = [_frag_json(i, f) for i, f in enumerate(frags)]
    exp = _numbers(data.get("exp"))
    if data.get("match"):
        if not exp or not frags:
            raise ApiError(g._("frag.match.need_input"))
        ppm = bool(data.get("ppm"))
        tol = _float(data.get("tol"), 0.02, 1e-6, 1e6)
        index = {id(f): i for i, f in enumerate(frags)}
        out["matches"] = [
            {"exp": e, "i": index[id(f)], "label": f.label, "z": f.charge,
             "err": err}
            for e, f, err in match_experimental(frags, exp, tolerance=tol, ppm=ppm)]
        out["n_exp"] = len(exp)
        out["unit"] = "ppm" if ppm else "Da"
    return _ok(**out)


@bp.post("/export/fragments/<fmt>")
def export_fragments(fmt: str):
    """Exportacao: o formulario manda `payload` (o mesmo JSON de /api/fragments)."""
    if fmt not in EXPORT_FORMATS:
        raise ApiError(g._("error.not_found"), 404)
    try:
        data = json.loads(request.form.get("payload") or "{}")
    except ValueError:
        data = {}
    _ = g._
    with LOCK:
        r = _parse_peptide(data)
        if r.n_chains > 1:
            raise ApiError(_("frag.multi_chain"))
        ions, losses, charges, no_loss = _frag_options(data)
        frags = _fragments_for(r, ions, charges, losses, no_loss)
        prec_mz = get_state().calc.mz(r.mono_mass, 2)
    if not frags:
        raise ApiError(_("frag.export.empty"))
    headers = [_("frag.col.ion"), "z", "m/z", _("frag.col.loss"),
               _("frag.col.neutral"), _("frag.col.seq")]
    rows = [[f"{f.ion_type}{f.number}", f.charge, f"{f.mz:.6f}",
             f.neutral_loss or "", f"{f.neutral_mass:.6f}", f.sequence]
            for f in frags]
    ext = "csv" if fmt == "skyline" else fmt
    name = f"{_('frag.export.filename')}.{ext}"
    tmp = tempfile.mkdtemp(prefix="peptmass-export-")
    path = os.path.join(tmp, name)
    try:
        if fmt == "csv":
            exporters.to_csv(path, headers, rows)
        elif fmt == "txt":
            exporters.to_txt(path, headers, rows,
                             title=_("frag.export.title_seq", s=r.sequence))
        elif fmt == "xlsx":
            exporters.to_xlsx(path, headers, rows, title=_("frag.export.sheet"))
        elif fmt == "pdf":
            exporters.to_pdf(path, headers, rows, title=_("frag.export.pdf_title"),
                             subtitle=_("frag.export.pdf_sub", s=r.sequence,
                                        m=f"{r.mono_mass:.6f}"))
        else:
            exporters.to_skyline_transition_list(
                path, r.sequence, frags, precursor_charge=2, precursor_mz=prec_mz)
        with open(path, "rb") as fh:
            payload = fh.read()
    except ImportError as exc:
        raise ApiError(_("error.missing_dep", e=exc), 500) from exc
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return send_file(io.BytesIO(payload), as_attachment=True, download_name=name)


# ---------------------------------------------------------------------------
# Peptideos salvos
# ---------------------------------------------------------------------------
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
    return _ok(peptides=[row["name"] for row in rows])


@bp.get("/api/peptide")
def peptide_get():
    name = request.args.get("name", "")
    with LOCK:
        row = get_state().db.get_peptide(name)
    if not row:
        raise ApiError(g._("peptide.not_found", n=name), 404)
    return _ok(name=row["name"], peptide={
        "sequence": row["sequence"], "nterm": row["n_term_mod"] or "",
        "cterm": row["c_term_mod"] or "", "rmods": _rmods_list(row["residue_mods"])})


@bp.post("/api/peptide")
def peptide_save():
    data = _body()
    name = str(data.get("name") or "").strip()
    seq, nterm, cterm, rmods = _peptide_def(data)
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
    return _ok(message=g._("peptide.saved", n=name))


@bp.delete("/api/peptide")
def peptide_delete():
    name = request.args.get("name", "")
    with LOCK:
        get_state().db.delete_peptide(name)
    return _ok()


# ---------------------------------------------------------------------------
# Aminoacidos personalizados e modificacoes
# ---------------------------------------------------------------------------
@bp.post("/api/residues")
def residue_add():
    data = _body()
    fields = [str(data.get(k) or "").strip() for k in ("name", "three", "code", "formula")]
    with LOCK:
        st = get_state()
        try:
            st.custom_manager.add(*fields)
        except ValueError as exc:
            raise ApiError(str(exc)) from exc
        st.calc.refresh_table()
    return _ok(message=g._("library.residue.added", c=fields[2]))


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
    return _ok()


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
        return _ok(modifications=[_mod_json(m, custom) for m in mods])


@bp.post("/api/modifications")
def modification_add():
    data = _body()
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
    return _ok(message=g._("library.mod.added", n=name))


@bp.delete("/api/modifications")
def modification_delete():
    name = request.args.get("name", "")
    with LOCK:
        if not get_state().delete_modification(name):
            raise ApiError(g._("library.mod.not_custom", n=name))
    return _ok()


@bp.post("/api/formula")
def formula_preview():
    """Massa monoisotopica de uma formula: do residuo (livre - H2O) ou delta."""
    data = _body()
    try:
        comp = parse_formula(str(data.get("formula") or ""))
        if data.get("mode") == "residue":
            comp = dict(comp)
            comp["H"] = comp.get("H", 0) - 2
            comp["O"] = comp.get("O", 0) - 1
        return _ok(mono=composition_mass(comp, average=False))
    except FormulaError as exc:
        raise ApiError(str(exc)) from exc


# ---------------------------------------------------------------------------
# PubChem e FASTA
# ---------------------------------------------------------------------------
@bp.post("/api/pubchem")
def pubchem_search():
    data = _body()
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
    return _ok(compound={
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
    entries = exporters.parse_fasta(str(_body().get("text") or ""))
    return _ok(entries=[{"header": h, "sequence": s} for h, s in entries])


# ---------------------------------------------------------------------------
# Dados experimentais (mzML / mzXML / .raw)
# ---------------------------------------------------------------------------
_ALLOWED_MS = (".mzml", ".mzxml", ".raw")


def _run_entry(rid: str) -> dict:
    entry = state.get_run(rid)
    if not entry:
        raise ApiError(g._("ms.run_gone"), 404, code="run_gone")
    return entry


def _selection(data: dict) -> dict:
    level = data.get("ms_level")
    return {"ms_level": _int(level, 0) or None,
            "scan_filter": str(data.get("filter") or "") or None,
            "grouped": bool(data.get("grouped", True))}


@bp.post("/api/ms/open")
def ms_open():
    upload = request.files.get("file")
    if not upload or not upload.filename:
        raise ApiError(g._("ms.no_file"))
    filename = os.path.basename(upload.filename.replace("\\", "/"))
    ext = os.path.splitext(filename)[1].lower()
    if ext not in _ALLOWED_MS:
        raise ApiError(g._("ms.bad_ext"))
    rid, folder = state.new_upload_dir()
    path = os.path.join(folder, "dados" + ext)
    upload.save(path)
    try:
        run = spectra_io.open_run(path, profile=request.form.get("profile") == "1")
    except Exception as exc:  # noqa: BLE001 - qualquer falha de leitura vira aviso
        shutil.rmtree(folder, ignore_errors=True)
        raise ApiError(g._("ms.open_error", e=exc)) from exc
    state.add_run(rid, run, folder, filename)
    return _ok(run_id=rid, filename=filename, n_scans=len(run.scans),
               levels=run.ms_levels())


@bp.get("/api/ms/<rid>/filters")
def ms_filters(rid: str):
    run = _run_entry(rid)["run"]
    grouped = request.args.get("grouped", "1") == "1"
    return _ok(filters=[[f, n] for f, n in run.filters(grouped=grouped)])


@bp.post("/api/ms/<rid>/chromatogram")
def ms_chromatogram(rid: str):
    run = _run_entry(rid)["run"]
    rts, ints = run.chromatogram(**_selection(_body()))
    return _ok(rt=rts, intensity=ints)


@bp.post("/api/ms/<rid>/xic")
def ms_xic(rid: str):
    data = _body()
    run = _run_entry(rid)["run"]
    target = _float(data.get("mz"), 0.0)
    if target <= 0:
        raise ApiError(g._("ms.xic.bad_mz"))
    tol = _float(data.get("tol"), 0.02, 1e-4, 10)
    rts, ints = run.xic(target, tol=tol, ppm=False, **_selection(data))
    return _ok(rt=rts, intensity=ints, mz=target)


def _peaks_for(entry: dict, scan):
    """Lista de picos do scan para o matching (centroidada se em perfil)."""
    cached = entry["peaks"].get(scan.index)
    if cached:
        return cached
    mz, inten = entry["run"].spectrum(scan.index)
    if scan.profile:
        pmz, pint = spectra_io.centroid_peaks(mz, inten)
        peaks = ([float(x) for x in pmz], [float(x) for x in pint])
    else:
        peaks = ([float(x) for x in mz], [float(x) for x in inten])
    entry["peaks"] = {scan.index: peaks}  # so o scan atual
    return peaks


def _scan_by_index(run, index: int):
    for s in run.scans:
        if s.index == index:
            return s
    raise ApiError(g._("ms.scan_not_found"), 404)


@bp.post("/api/ms/<rid>/scan")
def ms_scan(rid: str):
    data = _body()
    entry = _run_entry(rid)
    run = entry["run"]
    if data.get("index") is not None:
        scan = _scan_by_index(run, _int(data.get("index"), -1))
    else:
        scan = run.scan_at_rt(_float(data.get("rt"), 0.0), **_selection(data))
        if scan is None:
            raise ApiError(g._("ms.scan_not_found"), 404)
    try:
        mz, inten = run.spectrum(scan.index)
    except Exception as exc:  # noqa: BLE001
        raise ApiError(g._("ms.scan_error", e=exc)) from exc
    with LOCK:
        peaks = _peaks_for(entry, scan)
    # carga do precursor: do arquivo ou estimada pelo cluster do MS1 anterior
    pz, estimated = scan.precursor_charge, False
    if not pz and scan.precursor_mz:
        ms1 = run.ms1_before(scan)
        if ms1 is not None:
            try:
                mz1, i1 = run.spectrum(ms1.index)
                pz, _n = identification.estimate_charge(mz1, i1, scan.precursor_mz)
                estimated = bool(pz)
            except Exception:  # noqa: BLE001 - estimativa e' opcional
                pz = None
    return _ok(scan={
        "index": scan.index, "label": scan.label, "rt": scan.rt,
        "ms_level": scan.ms_level, "filter": scan.filter_string or "",
        "precursor_mz": scan.precursor_mz, "precursor_charge": pz,
        "charge_estimated": estimated, "profile": bool(scan.profile),
        "n_peaks": len(peaks[0])},
        spectrum={"mz": [round(float(x), 5) for x in mz],
                  "intensity": [float(x) for x in inten]})


@bp.post("/api/ms/<rid>/match")
def ms_match(rid: str):
    data = _body()
    _ = g._
    entry = _run_entry(rid)
    run = entry["run"]
    scan = _scan_by_index(run, _int(data.get("index"), -1))
    with LOCK:
        r = _parse_peptide(data)
        if r.n_chains > 1:
            raise ApiError(_("frag.multi_chain"))
        series = [i for i in data.get("series") or [] if i in ION_TYPES] or ["b", "y"]
        charges = sorted({_int(z, 1, 1, 10) for z in data.get("charges") or []}) or [1]
        losses = list(NEUTRAL_LOSSES) if data.get("losses") else []
        frags = _fragments_for(r, series, charges, losses, True)
        peak_mz, peak_int = _peaks_for(entry, scan)
        calc = get_state().calc
        dist = calc.isotopic_distribution(r.composition, max_peaks=8)
    ppm = bool(data.get("ppm", True))
    tol = _float(data.get("tol"), 10.0, 1e-6, 1e6)
    unit = "ppm" if ppm else "Da"
    matches = match_experimental(frags, peak_mz, tolerance=tol, ppm=ppm)
    base = max(peak_int) if peak_int else 1.0
    inten_by = dict(zip(peak_mz, peak_int))
    rows = [{"exp": e, "label": f.label, "type": f.ion_type, "z": f.charge,
             "theo": f.mz, "err": err, "rel": 100.0 * inten_by.get(e, 0.0) / base,
             "seq": f.sequence}
            for e, f, err in matches]
    sc = scoring.score_spectrum(matches, peak_mz, peak_int, n_theoretical=len(frags))

    # criterios de identificacao (estilo WADA)
    criteria = []
    pz = _int(data.get("prec_charge"), 2, 1, 20)
    if scan.precursor_mz and pz:
        neutral = scan.precursor_mz * pz - pz * PROTON_MASS
        err = (neutral - r.mono_mass) / r.mono_mass * 1e6
        limit = tol if ppm else 20.0
        criteria.append({"state": "ok" if abs(err) <= limit else "bad",
                         "text": _("ms.crit.precursor", e=f"{err:+.1f}", z=pz)})
    rt_exp = _float(data.get("rt_exp"), 0.0, 0.0)
    if rt_exp > 0:
        drt = abs(scan.rt - rt_exp)
        win = _float(data.get("rt_win"), 0.2, 0.01)
        criteria.append({"state": "ok" if drt <= win else "bad",
                         "text": _("ms.crit.rt", d=f"{drt:.2f}")})
    criteria.append({"state": "ok" if len(matches) >= 2 else "bad",
                     "text": _("ms.crit.ions", n=len(matches))})
    try:
        ms1 = run.ms1_before(scan)
        if ms1 is not None:
            mz1, i1 = run.spectrum(ms1.index)
            fit, nfit = identification.isotope_fit(
                mz1, i1, dist, pz, tol=max(_float(data.get("xic_tol"), 0.02), 0.02))
            if nfit >= 2:
                criteria.append({"state": "ok" if fit >= 0.9 else "warn",
                                 "text": _("ms.crit.isotopes", f=f"{fit:.2f}")})
    except Exception:  # noqa: BLE001 - o ajuste isotopico e' complementar
        pass

    me = sc["mass_error"]
    return _ok(matches=rows, unit=unit, n_theoretical=len(frags),
               score={"score": sc["score"], "n": sc["n_matched"],
                      "tic": sc["tic_fraction"] * 100, "coverage": sc["coverage"],
                      "median": me["median"], "max": me["max_abs"], "rmse": me["rmse"]},
               criteria=criteria)
