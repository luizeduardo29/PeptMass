"""Massa, estados de carga e distribuicao isotopica."""

from __future__ import annotations

from peptmass.core.formula_parser import FormulaError
from peptmass.core.mass_calculator import SequenceError
from peptmass.web.state import LOCK, get_state

from . import bp
from .common import bounded_int, json_body, ok, peptide_definition, peptide_summary


@bp.post("/api/mass")
def mass():
    data = json_body()
    seq, nterm, cterm, rmods = peptide_definition(data)
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
            return ok(**out)
        try:
            r = calc.parse(seq, n_term_mod=nterm, c_term_mod=cterm,
                           residue_mods=rmods)
        except (SequenceError, FormulaError) as exc:
            out.update(valid=False, message=str(exc))
            return ok(**out)
        zmin = bounded_int(data.get("zmin"), 1, 1, 200)
        zmax = bounded_int(data.get("zmax"), 10, 1, 200)
        charges = set(range(zmin, max(zmin, zmax) + 1))
        for tok in str(data.get("zextra") or "").split(","):
            tok = tok.strip()
            if tok.isdigit() and 0 < int(tok) <= 1000:
                charges.add(int(tok))
        out["result"] = peptide_summary(r)
        out["charges"] = [[z, mz] for z, mz in calc.charge_table(
            r.mono_mass, sorted(charges))]
        out["isotopes"] = [[m, i] for m, i in calc.isotopic_distribution(
            r.composition, max_peaks=12)]
    return ok(**out)
