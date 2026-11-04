"""Fragmentacao MS/MS, comparacao com uma lista de m/z e exportacoes."""

from __future__ import annotations

import io
import json
import os
import shutil
import tempfile

from flask import g, request, send_file

from peptmass.core.fragmentation import match_experimental
from peptmass.infra import exporters
from peptmass.web.state import LOCK, get_state

from . import bp
from .common import (ApiError, bounded_float, build_fragments, fragment_options,
                     json_body, ok, parse_numbers, parse_peptide, peptide_summary)

EXPORT_FORMATS = ("csv", "xlsx", "pdf", "txt", "skyline")


def _frag_json(i: int, f) -> dict:
    return {"i": i, "ion": f"{f.ion_type}{f.number}", "type": f.ion_type,
            "label": f.label, "z": f.charge, "mz": f.mz,
            "loss": f.neutral_loss, "neutral": f.neutral_mass, "seq": f.sequence}


@bp.post("/api/fragments")
def fragments():
    data = json_body()
    with LOCK:
        r = parse_peptide(data)
        out = {"peptide": peptide_summary(r), "multi_chain": r.n_chains > 1,
               "fragments": [], "matches": None}
        if r.n_chains > 1:
            return ok(**out)
        ions, losses, charges, no_loss = fragment_options(data)
        frags = build_fragments(r, ions, charges, losses, no_loss)
    out["fragments"] = [_frag_json(i, f) for i, f in enumerate(frags)]
    exp = parse_numbers(data.get("exp"))
    if data.get("match"):
        if not exp or not frags:
            raise ApiError(g._("frag.match.need_input"))
        ppm = bool(data.get("ppm"))
        tol = bounded_float(data.get("tol"), 0.02, 1e-6, 1e6)
        index = {id(f): i for i, f in enumerate(frags)}
        out["matches"] = [
            {"exp": e, "i": index[id(f)], "label": f.label, "z": f.charge,
             "err": err}
            for e, f, err in match_experimental(frags, exp, tolerance=tol, ppm=ppm)]
        out["n_exp"] = len(exp)
        out["unit"] = "ppm" if ppm else "Da"
    return ok(**out)


def _write_export(fmt, path, headers, rows, r, frags, prec_mz):
    _ = g._
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
        r = parse_peptide(data)
        if r.n_chains > 1:
            raise ApiError(_("frag.multi_chain"))
        ions, losses, charges, no_loss = fragment_options(data)
        frags = build_fragments(r, ions, charges, losses, no_loss)
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
        _write_export(fmt, path, headers, rows, r, frags, prec_mz)
        with open(path, "rb") as fh:
            payload = fh.read()
    except ImportError as exc:
        raise ApiError(_("error.missing_dep", e=exc), 500) from exc
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return send_file(io.BytesIO(payload), as_attachment=True, download_name=name)
