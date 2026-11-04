"""
test_suite.py
=============
Validação científica do PeptMass (sem interface gráfica).
Executa cálculos e compara com valores publicados de referência.

Uso:
    python test_suite.py
"""

from mass_calculator import MassCalculator
from fragmentation import generate_fragments
from custom_residues import CustomResidueManager
from database import Database

PASS, FAIL = 0, 0


def check(label, got, expected, tol=1e-3):
    global PASS, FAIL
    ok = abs(got - expected) < tol
    PASS += ok
    FAIL += (not ok)
    print(f"  [{'OK ' if ok else 'ERRO'}] {label:34s} "
          f"{got:.6f}  (ref {expected:.6f})")


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

    print("\n" + "=" * 64)
    print(f"Resultado: {PASS} aprovados, {FAIL} falhas")
    print("=" * 64)
    return FAIL == 0


if __name__ == "__main__":
    ok = main()
    raise SystemExit(0 if ok else 1)
