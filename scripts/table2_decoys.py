# -*- coding: utf-8 -*-
"""
table2_decoys.py
================
Reproduces Table 2 of the PeptMass manuscript (verification of predicted
fragment ions by LC-PRM on a Q Exactive Plus), including the decoy estimate
of random matches described in Section 4.6.

For each analyte of the seven-peptide panel the script:
  1. takes the PRM scans of its isolation center and picks the apex
     (highest total ion current), plus the two scans before and after it;
  2. centroids profile scans with the PeptMass centroiding routine;
  3. matches the predicted a/b/c/x/y/z series (NH3, H2O and CO losses,
     fragment charges 1+ up to min(3, precursor charge)) within 5 ppm,
     assigning each experimental peak to the single closest theoretical ion;
  4. repeats the matching at the apex scan with ten decoy ion lists, in which
     every predicted neutral fragment mass is shifted by +/-7, +/-11, +/-13,
     +/-19 or +/-23 Da before the m/z is computed (same charges, same settings);
  5. reports matched ions, decoy matches (mean and range), explained TIC,
     median / max |error| and the Morpheus score (eq 2).

Human insulin is annotated on its B chain entered as a single chain, keeping
only the b1-b6 and y1-y11 ions, which contain no disulfide-bonded residue.

All chemistry comes from the PeptMass package itself (sequence presets,
mass calculator, fragment generator, mzML/.raw reader and centroider).

Usage (from the repository root):

    python scripts/table2_decoys.py PATH_TO_RAW_FOLDER [--out table2.json]
    python scripts/table2_decoys.py --self-test

PATH_TO_RAW_FOLDER must contain the four files listed in PANEL below.
Thermo .raw files are converted with ThermoRawFileParser, which must be
installed as for the PeptMass application; mzML files with the same base
name are used directly if present.

--self-test runs without data: it checks that the predicted ion lists and
the neutral masses of the seven analytes are those used for Table 2.
"""
import argparse
import json
import os
import re
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from peptmass.core.constants import PROTON_MASS              # noqa: E402
from peptmass.core.fragmentation import generate_fragments   # noqa: E402
from peptmass.core.presets import DOPING_PRESETS, GLP_PRESETS  # noqa: E402
from peptmass.core.workspace import Workspace               # noqa: E402
from peptmass.infra import spectra_io                        # noqa: E402
from peptmass.infra.database import Database                 # noqa: E402

TOL_PPM = 5.0
ALL6 = ["a", "b", "c", "x", "y", "z"]
LOSSES = ["-NH3", "-H2O", "-CO"]
DECOY_OFFSETS = [-23.0, -19.0, -13.0, -11.0, -7.0, 7.0, 11.0, 13.0, 19.0, 23.0]
INSULIN_B_CHAIN = "FVNQHLCGSHLVEALYLVCGERGFFYTPKT"


def insulin_keep(f):
    return ((f.ion_type == "b" and f.number <= 6)
            or (f.ion_type == "y" and f.number <= 11))


# label, data file, isolation center (m/z), precursor charge, preset name
# (None = B chain of human insulin), ion series, fragment filter
PANEL = [
    ("GHRP-2", "MIX_prm.raw", 818.43, 1, "GHRP-2 (pralmorelin)", ALL6, None),
    ("Ipamorelin", "MIX_prm.raw", 356.70, 2, "Ipamorelin", ALL6, None),
    ("Triptorelin", "MIX_prm.raw", 656.32, 2, "Triptorelin", ALL6, None),
    ("Semaglutide", "Semaglutida_10ug_mL_.raw", 1372.0, 3, "Semaglutide", ALL6, None),
    ("Tirzepatide", "Tizerpatida_10ug_mL_2.raw", 1605.0, 3, "Tirzepatide", ALL6, None),
    ("Desmopressin", "MIX_prm.raw", 1069.43, 1, "Desmopressin (dDAVP)", ALL6, None),
    ("Human insulin (B chain)", "INSULINA HUMANA.RAW", 1162.50, 5, None,
     ["b", "y"], insulin_keep),
]

# Values reported in Table 2 of the manuscript (apex scan), used by --check.
# label: (scan, matched, 5-scan mean, decoy mean, decoy min, decoy max,
#         explained TIC %, median ppm, max |ppm|, Morpheus)
TABLE2 = {
    "GHRP-2": (1281, 28, 27.0, 0.3, 0, 1, 53.9, -2.40, 4.96, 28.54),
    "Ipamorelin": (312, 27, 22.0, 0.5, 0, 1, 51.2, -1.90, 4.81, 27.51),
    "Triptorelin": (1105, 39, 38.0, 1.4, 0, 4, 70.7, -2.41, 4.51, 39.71),
    "Semaglutide": (2297, 85, 85.6, 24.3, 10, 52, 18.3, -0.85, 4.72, 85.18),
    "Tirzepatide": (2479, 64, 63.6, 13.0, 7, 39, 44.8, -0.48, 4.89, 64.45),
    "Desmopressin": (686, 9, 7.8, 0.2, 0, 1, 19.5, -0.52, 4.27, 9.19),
    "Human insulin (B chain)": (47, 52, 54.0, 3.1, 0, 6, 2.3, -3.28, 4.85, 52.02),
}

# Size of the predicted ion list and neutral monoisotopic mass of each analyte
# as used for Table 2 (checked by --self-test).
EXPECTED_THEORY = {
    "GHRP-2": (120, 817.427531),
    "Ipamorelin": (192, 711.385666),
    "Triptorelin": (432, 1310.630875),
    "Semaglutide": (2160, 4111.115377),
    "Tirzepatide": (2736, 4810.524858),
    "Desmopressin": (192, 1068.426955),
    "Human insulin (B chain)": (204, 3427.684573),
}


# ---------------------------------------------------------------------------
def make_calculator():
    """Mass calculator with the built-in residues and modifications, using a
    throw-away database so that the user's own library is never touched."""
    tmp = tempfile.mkdtemp(prefix="peptmass_t2_")
    return Workspace(Database(os.path.join(tmp, "peptmass.db"))).calc


def build_peptide(calc, preset_name):
    if preset_name is None:
        return calc.parse(INSULIN_B_CHAIN)
    for entry in list(GLP_PRESETS) + list(DOPING_PRESETS):
        if entry[0] == preset_name:
            residue_mods = {}
            if len(entry) >= 5 and entry[4]:
                residue_mods = {int(i): m for i, m in json.loads(entry[4])}
            return calc.parse(entry[1], n_term_mod=entry[2] or None,
                              c_term_mod=entry[3] or None,
                              residue_mods=residue_mods)
    raise KeyError(f"Preset not found: {preset_name}")


def predicted_ions(pep, ions, precursor_charge, keep):
    """Same call as the annotation panel: terminal-group deltas are applied to
    the N- and C-terminal series; fragment charges up to min(3, z)."""
    nd = pep.n_term_mod.mono_delta if pep.n_term_mod else 0.0
    cd = pep.c_term_mod.mono_delta if pep.c_term_mod else 0.0
    charges = list(range(1, min(3, precursor_charge) + 1))
    frags = generate_fragments(pep, ion_types=ions, charges=charges,
                               neutral_losses=LOSSES, include_no_loss=True,
                               n_term_delta=nd, c_term_delta=cd)
    return [f for f in frags if keep(f)] if keep else frags


def closest_match(exp_mz, theo_mz, tol_ppm=TOL_PPM):
    """Index of the closest theoretical ion for each experimental peak
    (-1 if outside the tolerance) and the error in ppm."""
    order = np.argsort(theo_mz)
    t = theo_mz[order]
    i = np.clip(np.searchsorted(t, exp_mz), 1, len(t) - 1)
    left, right = t[i - 1], t[i]
    best = np.where(np.abs(exp_mz - left) <= np.abs(exp_mz - right), i - 1, i)
    err = (exp_mz - t[best]) / t[best] * 1e6
    return np.where(np.abs(err) <= tol_ppm, order[best], -1), err


def analyse_scan(mz, inten, frags):
    theo_mz = np.array([f.mz for f in frags])
    theo_neutral = np.array([f.neutral_mass for f in frags])
    theo_z = np.array([f.charge for f in frags])
    idx, err = closest_match(mz, theo_mz)
    ok = idx >= 0
    n = int(ok.sum())
    frac = float(inten[ok].sum() / inten.sum())
    decoys = []
    for off in DECOY_OFFSETS:
        d_idx, _ = closest_match(mz, (theo_neutral + off + theo_z * PROTON_MASS) / theo_z)
        decoys.append(int((d_idx >= 0).sum()))
    e = err[ok]
    labels = sorted({frags[k].label + (f"({frags[k].charge}+)" if frags[k].charge > 1 else "")
                     for k in idx[ok]})
    return dict(n=n, frac=frac, morpheus=n + frac,
                med=float(np.median(e)) if n else 0.0,
                maxabs=float(np.max(np.abs(e))) if n else 0.0,
                decoy=decoys, labels=labels)


def open_data(folder, name, cache):
    base = os.path.splitext(name)[0]
    for candidate in (base + ".mzML", base + ".mzml", name):
        path = os.path.join(folder, candidate)
        if os.path.exists(path):
            if path not in cache:
                cache[path] = spectra_io.open_run(path)
            return cache[path]
    raise FileNotFoundError(f"{name} not found in {folder}")


def scan_number(scan):
    m = re.search(r"scan=(\d+)", scan.scan_id or "")
    return int(m.group(1)) if m else scan.index + 1


def run_panel(folder):
    calc = make_calculator()
    cache, rows = {}, []
    for label, data_file, iso, zp, preset_name, ions, keep in PANEL:
        run = open_data(folder, data_file, cache)
        pep = build_peptide(calc, preset_name)
        frags = predicted_ions(pep, ions, zp, keep)
        targets = [s for s in run.scans if s.ms_level == 2 and s.precursor_mz
                   and abs(s.precursor_mz - iso) < 0.05]
        if not targets:
            raise RuntimeError(f"No MS2 scans at m/z {iso} in {data_file}")
        k = max(range(len(targets)), key=lambda i: targets[i].tic)
        per_scan = []
        for j in range(max(0, k - 2), min(len(targets), k + 3)):
            s = targets[j]
            mz, inten = run.spectrum(s.index)
            if s.profile:
                mz, inten = spectra_io.centroid_peaks(mz, inten)
            r = analyse_scan(np.asarray(mz, float), np.asarray(inten, float), frags)
            r.update(scan=scan_number(s), rt=s.rt, npk=len(mz), apex=(j == k))
            per_scan.append(r)
        apex = next(r for r in per_scan if r["apex"])
        counts = [r["n"] for r in per_scan]
        calc_mz = None if preset_name is None else (pep.mono_mass + zp * PROTON_MASS) / zp
        rows.append(dict(label=label, data_file=data_file, isolation_center=iso,
                         precursor_charge=zp, calc_mz=calc_mz, mono=pep.mono_mass,
                         n_theo=len(frags), apex=apex,
                         five_scans=counts, five_mean=float(np.mean(counts)),
                         five_sd=float(np.std(counts, ddof=1)) if len(counts) > 1 else 0.0))
    return rows


def print_rows(rows):
    print(f"{'Peptide':26s}{'Scan':>6s}{'RT':>7s}{'Matched':>9s}{'5-scan':>14s}"
          f"{'Decoys':>16s}{'TIC %':>7s}{'med/max ppm':>15s}{'Morpheus':>10s}")
    for r in rows:
        a, d = r["apex"], r["apex"]["decoy"]
        print(f"{r['label']:26s}{a['scan']:6d}{a['rt']:7.2f}{a['n']:9d}"
              f"{r['five_mean']:8.1f} ± {r['five_sd']:3.1f}"
              f"{np.mean(d):8.1f} ({min(d)}–{max(d)})"
              f"{100 * a['frac']:7.1f}{a['med']:8.2f} / {a['maxabs']:4.2f}{a['morpheus']:10.2f}")


def check_rows(rows):
    """Compares the recomputed values with Table 2 at the printed precision."""
    ok_all = True
    for r in rows:
        a, d = r["apex"], r["apex"]["decoy"]
        got = (a["scan"], a["n"], round(r["five_mean"], 1), round(float(np.mean(d)), 1),
               min(d), max(d), round(100 * a["frac"], 1), round(a["med"], 2),
               round(a["maxabs"], 2), round(a["morpheus"], 2))
        exp = TABLE2[r["label"]]
        same = all(abs(g - e) < 1e-9 for g, e in zip(got, exp))
        ok_all &= same
        print(f"{'OK  ' if same else 'DIFF'} {r['label']}" + ("" if same else f"\n     got {got}\n     exp {exp}"))
    return ok_all


def self_test():
    calc = make_calculator()
    ok_all = True
    for label, _f, _iso, zp, preset_name, ions, keep in PANEL:
        pep = build_peptide(calc, preset_name)
        n = len(predicted_ions(pep, ions, zp, keep))
        n_exp, mono_exp = EXPECTED_THEORY[label]
        same = n == n_exp and abs(pep.mono_mass - mono_exp) < 1e-6
        ok_all &= same
        print(f"{'OK  ' if same else 'DIFF'} {label:26s} ions {n:5d} (expected {n_exp:5d})  "
              f"mono {pep.mono_mass:.6f} (expected {mono_exp:.6f})")
    return ok_all


def main():
    ap = argparse.ArgumentParser(description="Reproduce Table 2 (PRM verification and decoys).")
    ap.add_argument("data_folder", nargs="?", help="folder with the .raw (or .mzML) files")
    ap.add_argument("--out", help="JSON file for the full results")
    ap.add_argument("--check", action="store_true", help="compare with the values in Table 2")
    ap.add_argument("--self-test", action="store_true", help="check predicted ion lists without data")
    args = ap.parse_args()
    if args.self_test:
        sys.exit(0 if self_test() else 1)
    if not args.data_folder:
        ap.error("data_folder is required (or use --self-test)")
    rows = run_panel(args.data_folder)
    print_rows(rows)
    for r in rows:
        print(f"  {r['label']}: {', '.join(r['apex']['labels'])}")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, indent=1)
    if args.check:
        sys.exit(0 if check_rows(rows) else 1)


if __name__ == "__main__":
    main()
