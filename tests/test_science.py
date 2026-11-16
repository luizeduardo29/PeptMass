"""
test_science.py
===============
Validação científica do PeptMass (sem interface gráfica).
Executa cálculos e compara com valores publicados de referência.

Uso:
    python tests/test_science.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from peptmass.core.mass_calculator import MassCalculator  # noqa: E402
from peptmass.core.fragmentation import generate_fragments  # noqa: E402
from peptmass.core.identification import evaluate_criteria  # noqa: E402
from peptmass.core.custom_residues import CustomResidueManager  # noqa: E402
from peptmass.infra.database import Database  # noqa: E402

PASS, FAIL = 0, 0


def check(label, got, expected, tol=1e-3):
    global PASS, FAIL
    ok = abs(got - expected) < tol
    PASS += ok
    FAIL += (not ok)
    print(f"  [{'OK ' if ok else 'ERRO'}] {label:34s} "
          f"{got:.6f}  (ref {expected:.6f})")


def check_criteria():
    """Estados de evaluate_criteria nos limites de cada criterio."""
    mono = 799.359964
    prec = calc_mz = MassCalculator.mz(mono, 2)

    def states(**kw):
        args = dict(precursor_mz=prec, charge=2, tolerance=5.0, ppm=True, scan_rt=10.0,
                    expected_rt=0.0, rt_window=0.2, n_ions=2, envelope_fit=None)
        args.update(kw)
        return {c["kind"]: c["state"] for c in evaluate_criteria(mono, **args)}

    def same(label, got, expected):
        check(label, float(got == expected), 1.0)

    same("precursor dentro da tolerância", states()["precursor"], "ok")
    same("precursor fora (6 ppm, tol 5)",
         states(precursor_mz=calc_mz * (1 + 6e-6))["precursor"], "bad")
    same("precursor em Da usa 20 ppm",
         states(precursor_mz=calc_mz * (1 + 19e-6), tolerance=0.02, ppm=False)["precursor"], "ok")
    same("sem precursor no scan", "precursor" in states(precursor_mz=None), False)
    same("RT não informado", "rt" in states(), False)
    same("RT no limite da janela", states(expected_rt=10.2)["rt"], "ok")
    same("RT fora da janela", states(expected_rt=10.5)["rt"], "bad")
    same("1 íon reprova", states(n_ions=1)["ions"], "bad")
    same("2 íons aprovam", states(n_ions=2)["ions"], "ok")
    same("cosseno 0.90 aprova", states(envelope_fit=(0.9, 2))["isotopes"], "ok")
    same("cosseno 0.89 só avisa", states(envelope_fit=(0.89, 2))["isotopes"], "warn")
    same("1 isótopo alinhado não avalia", "isotopes" in states(envelope_fit=(0.99, 1)), False)


def main():
    print("=" * 64)
    print("PeptMass — validação científica")
    print("=" * 64)

    calc = MassCalculator()

    print("\n• Massas de peptídeos (monoisotópica):")
    check("PEPTIDE", calc.parse("PEPTIDE").mono_mass, 799.359964)
    check("ACDEFGHIKLMNPQRSTVWY", calc.parse("ACDEFGHIKLMNPQRSTVWY").mono_mass,
          2394.125393, tol=1e-2)
    check("Bradykinin RPPGFSPFR", calc.parse("RPPGFSPFR").mono_mass, 1059.561456)
    check("Angiotensin II DRVYIHPF", calc.parse("DRVYIHPF").mono_mass, 1045.534)
    check("Substance P RPKPQQFFGLM-NH2",
          calc.parse("RPKPQQFFGLM", c_term_mod="Amidation").mono_mass,
          1346.728, tol=1e-2)

    print("\n• Modificações:")
    base = calc.parse("PEPTIDE").mono_mass
    check("Acetyl (+42.010565)",
          calc.parse("PEPTIDE", n_term_mod="Acetyl").mono_mass - base, 42.010565)
    check("Amidation (-0.984016)",
          calc.parse("PEPTIDE", c_term_mod="Amidation").mono_mass - base,
          -0.984016)
    check("Phospho inline (+79.966331)",
          calc.parse("PEPT(Phosphorylation)IDE").mono_mass - base, 79.966331)

    print("\n• m/z multicarga (PEPTIDE, M=799.359964):")
    check("[M+H]+",  calc.mz(799.359964, 1), 800.367241)
    check("[M+2H]2+", calc.mz(799.359964, 2), 400.687258)
    check("[M+3H]3+", calc.mz(799.359964, 3), 267.460748)

    print("\n• Fragmentação (PEPTIDE, singly charged):")
    frags = generate_fragments(calc.parse("PEPTIDE"),
                               ["a", "b", "c", "x", "y", "z"], [1])
    g = {f.label: f.mz for f in frags if not f.neutral_loss}
    check("a2", g["a2"], 199.10772)
    check("b2", g["b2"], 227.10263)
    check("c2", g["c2"], 244.12918)
    check("x2", g["x2"], 289.06663)
    check("y2", g["y2"], 263.08737)
    check("z2", g["z2"], 246.06082)

    print("\n• Aminoácido personalizado (Aib = C4H9NO2):")
    db = Database(":memory:")
    mgr = CustomResidueManager(db)
    mgr.add("Aminoisobutyric acid", "Aib", "U", "C4H9NO2")
    calc2 = MassCalculator(mgr)
    check("Resíduo Aib (mono)", mgr.get("U").mono_mass, 85.052764)
    check("Aib-Aib-Lys (UUK)", calc2.parse("UUK").mono_mass, 316.211056)
    db.close()

    print("\n• Critérios de identificação:")
    check_criteria()

    print("\n" + "=" * 64)
    print(f"Resultado: {PASS} aprovados, {FAIL} falhas")
    print("=" * 64)
    return FAIL == 0


if __name__ == "__main__":
    ok = main()
    raise SystemExit(0 if ok else 1)
