"""Dados experimentais: abrir arquivo, cromatograma, XIC, scan e anotacao."""

from __future__ import annotations

import os
import shutil

from flask import g, request

from peptmass.core import identification, scoring
from peptmass.core.fragmentation import NEUTRAL_LOSSES, match_experimental
from peptmass.infra import spectra_io
from peptmass.web import state
from peptmass.web.state import LOCK, get_state

from . import bp
from .common import (ION_TYPES, ApiError, bounded_float, bounded_int, build_fragments,
                     json_body, ok, parse_peptide)

_ALLOWED_MS = (".mzml", ".mzxml", ".raw")


def _run_entry(rid: str) -> dict:
    entry = state.get_run(rid)
    if not entry:
        raise ApiError(g._("ms.run_gone"), 404, code="run_gone")
    return entry


def _selection(data: dict) -> dict:
    level = data.get("ms_level")
    return {"ms_level": bounded_int(level, 0) or None,
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
    return ok(run_id=rid, filename=filename, n_scans=len(run.scans),
               levels=run.ms_levels())


@bp.get("/api/ms/<rid>/filters")
def ms_filters(rid: str):
    run = _run_entry(rid)["run"]
    grouped = request.args.get("grouped", "1") == "1"
    return ok(filters=[[f, n] for f, n in run.filters(grouped=grouped)])


@bp.post("/api/ms/<rid>/chromatogram")
def ms_chromatogram(rid: str):
    run = _run_entry(rid)["run"]
    rts, ints = run.chromatogram(**_selection(json_body()))
    return ok(rt=rts, intensity=ints)


@bp.post("/api/ms/<rid>/xic")
def ms_xic(rid: str):
    data = json_body()
    run = _run_entry(rid)["run"]
    target = bounded_float(data.get("mz"), 0.0)
    if target <= 0:
        raise ApiError(g._("ms.xic.bad_mz"))
    tol = bounded_float(data.get("tol"), 0.02, 1e-4, 10)
    rts, ints = run.xic(target, tol=tol, ppm=False, **_selection(data))
    return ok(rt=rts, intensity=ints, mz=target)


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
    data = json_body()
    entry = _run_entry(rid)
    run = entry["run"]
    if data.get("index") is not None:
        scan = _scan_by_index(run, bounded_int(data.get("index"), -1))
    else:
        scan = run.scan_at_rt(bounded_float(data.get("rt"), 0.0), **_selection(data))
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
    return ok(scan={
        "index": scan.index, "label": scan.label, "rt": scan.rt,
        "ms_level": scan.ms_level, "filter": scan.filter_string or "",
        "precursor_mz": scan.precursor_mz, "precursor_charge": pz,
        "charge_estimated": estimated, "profile": bool(scan.profile),
        "n_peaks": len(peaks[0])},
        spectrum={"mz": [round(float(x), 5) for x in mz],
                  "intensity": [float(x) for x in inten]})


def _criteria(data, run, scan, peptide, distribution, n_ions, tol, ppm):
    """Criterios do nucleo com o texto no idioma da tela."""
    _ = g._
    charge = bounded_int(data.get("prec_charge"), 2, 1, 20)
    envelope = identification.ms1_envelope_fit(
        run, scan, distribution, charge, bounded_float(data.get("xic_tol"), 0.02))
    texts = {
        "precursor": lambda v: _("ms.crit.precursor", e=f"{v:+.1f}", z=charge),
        "rt": lambda v: _("ms.crit.rt", d=f"{v:.2f}"),
        "ions": lambda v: _("ms.crit.ions", n=v),
        "isotopes": lambda v: _("ms.crit.isotopes", f=f"{v:.2f}"),
    }
    results = identification.evaluate_criteria(
        peptide.mono_mass, scan.precursor_mz, charge, tol, ppm, scan.rt,
        bounded_float(data.get("rt_exp"), 0.0, 0.0),
        bounded_float(data.get("rt_win"), 0.2, 0.01), n_ions, envelope)
    return [{"state": c["state"], "text": texts[c["kind"]](c["value"])} for c in results]


@bp.post("/api/ms/<rid>/match")
def ms_match(rid: str):
    data = json_body()
    _ = g._
    entry = _run_entry(rid)
    run = entry["run"]
    scan = _scan_by_index(run, bounded_int(data.get("index"), -1))
    with LOCK:
        r = parse_peptide(data)
        if r.n_chains > 1:
            raise ApiError(_("frag.multi_chain"))
        series = [i for i in data.get("series") or [] if i in ION_TYPES] or ["b", "y"]
        charges = sorted({bounded_int(z, 1, 1, 10) for z in data.get("charges") or []}) or [1]
        losses = list(NEUTRAL_LOSSES) if data.get("losses") else []
        frags = build_fragments(r, series, charges, losses, True)
        peak_mz, peak_int = _peaks_for(entry, scan)
        calc = get_state().calc
        dist = calc.isotopic_distribution(r.composition, max_peaks=8)
    ppm = bool(data.get("ppm", True))
    tol = bounded_float(data.get("tol"), 10.0, 1e-6, 1e6)
    unit = "ppm" if ppm else "Da"
    matches = match_experimental(frags, peak_mz, tolerance=tol, ppm=ppm)
    base = max(peak_int) if peak_int else 1.0
    inten_by = dict(zip(peak_mz, peak_int))
    rows = [{"exp": e, "label": f.label, "type": f.ion_type, "z": f.charge,
             "theo": f.mz, "err": err, "rel": 100.0 * inten_by.get(e, 0.0) / base,
             "seq": f.sequence}
            for e, f, err in matches]
    sc = scoring.score_spectrum(matches, peak_mz, peak_int, n_theoretical=len(frags))

    criteria = _criteria(data, run, scan, r, dist, len(matches), tol, ppm)
    me = sc["mass_error"]
    return ok(matches=rows, unit=unit, n_theoretical=len(frags),
               score={"score": sc["score"], "n": sc["n_matched"],
                      "tic": sc["tic_fraction"] * 100, "coverage": sc["coverage"],
                      "median": me["median"], "max": me["max_abs"], "rmse": me["rmse"]},
               criteria=criteria)
