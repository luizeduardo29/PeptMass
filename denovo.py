"""
denovo.py
=========
Sequenciamento de peptídeos a partir de um espectro MS/MS.

Dois modos:

1. `library_identify()` — pontua o espectro contra uma lista de peptídeos
   conhecidos (a biblioteca salva) e rankeia os candidatos. Confiável: só
   reconhece o que já está na biblioteca, mas com cobertura de íons e erro
   de massa do precursor.

2. `denovo_sequence()` — tenta deduzir a sequência do zero pelo método do
   grafo de espectro (best-effort). Limites intrínsecos: Ile/Leu são
   idênticos (rótulo "I/L"), Lys/Gln quase; lacunas por picos ausentes;
   ruído. Bom em espectros limpos de alta resolução.
"""

from constants import AMINO_ACIDS, PROTON_MASS
from formula_parser import parse_formula, composition_mass
from fragmentation import generate_fragments, match_experimental

_H2O = 18.0105646


def standard_residue_masses(collapse_il=True):
    """Massas monoisotópicas dos resíduos dos 20 aminoácidos naturais.
    Com collapse_il=True, Ile/Leu viram um único rótulo 'I/L'."""
    m = {}
    for code, info in AMINO_ACIDS.items():
        m[code] = composition_mass(parse_formula(info["formula"]), average=False)
    if collapse_il and "I" in m and "L" in m:
        m.pop("I", None)
        m["I/L"] = m.pop("L")
    return m


def _tol_da(mass, tol, ppm):
    return mass * tol / 1e6 if ppm else tol


# ---------------------------------------------------------------------------
# Modo 1 — identificação por biblioteca
# ---------------------------------------------------------------------------
def library_identify(calc, peptides, peak_mzs, prec_mz, prec_charge,
                     tol=10.0, ppm=True, ion_types=("b", "y"), max_charge=2):
    """Rankeia `peptides` (lista de dicts com name/sequence/n_term_mod/
    c_term_mod/residue_mods) pela explicação do espectro.

    Retorna lista de dicts ordenada por score (desc):
      name, mono_mass, prec_err_ppm, matched, total_by, coverage, score, seq
    """
    import json
    proton = PROTON_MASS
    prec_neutral = prec_mz * prec_charge - prec_charge * proton
    charges = list(range(1, max(1, min(max_charge, prec_charge)) + 1))
    results = []
    for p in peptides:
        seq = p["sequence"]
        nt = p.get("n_term_mod") or None
        ct = p.get("c_term_mod") or None
        try:
            rm = json.loads(p.get("residue_mods") or "[]")
        except (ValueError, TypeError):
            rm = []
        try:
            res = calc.parse(seq, n_term_mod=nt, c_term_mod=ct,
                             residue_mods={i: m for i, m in rm})
        except Exception:
            continue
        mono = res.mono_mass
        prec_err = (prec_neutral - mono) / mono * 1e6 if mono else 9e9
        matched = 0
        total_by = 0
        if getattr(res, "n_chains", 1) == 1:
            n_delta = res.n_term_mod.mono_delta if res.n_term_mod else 0.0
            c_delta = res.c_term_mod.mono_delta if res.c_term_mod else 0.0
            frags = generate_fragments(
                res, ion_types=list(ion_types), charges=charges,
                n_term_delta=n_delta, c_term_delta=c_delta)
            noloss = [f for f in frags if not f.neutral_loss]
            m = match_experimental(noloss, peak_mzs, tolerance=tol, ppm=ppm)
            matched = len(m)
            n_res = len(res.residues)
            total_by = len(ion_types) * max(1, n_res - 1) * len(charges)
        cov = 100.0 * matched / total_by if total_by else 0.0
        # score: prioriza precursor compatível e muitos íons casados
        prec_ok = abs(prec_err) <= (tol if ppm else 50.0)
        score = matched + (1000 if prec_ok else 0)
        results.append(dict(name=p["name"], mono_mass=mono,
                            prec_err_ppm=prec_err, matched=matched,
                            total_by=total_by, coverage=cov, score=score,
                            seq=seq))
    results.sort(key=lambda r: (-r["score"], abs(r["prec_err_ppm"])))
    return results


# ---------------------------------------------------------------------------
# Modo 2 — de novo por grafo de espectro
# ---------------------------------------------------------------------------
def denovo_sequence(peak_mzs, prec_mz, prec_charge, peak_int=None,
                    tol=0.02, ppm=False, residue_masses=None):
    """De novo por grafo de espectro (íons b/y de carga 1).

    Retorna dict:
      sequence (str, N->C), score, residues (lista de códigos),
      coverage (fração da massa explicada), complete (bool),
      precursor_neutral_mass.
    """
    proton = PROTON_MASS
    M = prec_mz * prec_charge - prec_charge * proton   # massa neutra do peptídeo
    Mres = M - _H2O                                     # soma das massas dos resíduos
    rmass = residue_masses or standard_residue_masses(collapse_il=True)
    peak_int = peak_int or [1.0] * len(peak_mzs)

    # candidatos de posição na régua [0, Mres]: cada pico como b e como y
    cand = [(0.0, 0.0), (Mres, 0.0)]
    for mz, inten in zip(peak_mzs, peak_int):
        b_prefix = mz - proton                          # b: prefixo direto
        y_prefix = Mres - (mz - proton - _H2O)          # y: complemento do sufixo
        for pm in (b_prefix, y_prefix):
            if -tol <= pm <= Mres + tol:
                cand.append((pm, float(inten)))
    cand.sort()
    # funde nós próximos, somando os scores (intensidades)
    nodes = []
    for m, inten in cand:
        if nodes and abs(m - nodes[-1][0]) <= tol:
            m0, s0 = nodes[-1]
            nodes[-1] = ((m0 * s0 + m * inten) / (s0 + inten) if (s0 + inten) else m0,
                         s0 + inten)
        else:
            nodes.append((m, inten))
    n = len(nodes)
    # garante nó inicial (~0) e final (~Mres)
    start = min(range(n), key=lambda i: abs(nodes[i][0] - 0.0))
    end = min(range(n), key=lambda i: abs(nodes[i][0] - Mres))

    ritems = sorted(rmass.items(), key=lambda kv: kv[1])

    def match_res(delta):
        best, bestd = None, tol
        for code, mm in ritems:
            d = abs(delta - mm)
            if d < bestd:
                bestd, best = d, code
        return best

    NEG = float("-inf")
    best = [NEG] * n
    back = [-1] * n
    lbl = [None] * n
    best[start] = 0.0
    order = sorted(range(n), key=lambda i: nodes[i][0])
    for jpos, j in enumerate(order):
        if best[j] == NEG:
            continue
        for k in order[jpos + 1:]:
            delta = nodes[k][0] - nodes[j][0]
            if delta <= tol:
                continue
            code = match_res(delta)
            if code:
                s = best[j] + nodes[k][1]
                if s > best[k]:
                    best[k] = s
                    back[k] = j
                    lbl[k] = code
    # reconstrói do fim (ou do nó alcançável de maior massa, se incompleto)
    target = end if best[end] > NEG else max(
        (i for i in range(n) if best[i] > NEG), key=lambda i: nodes[i][0],
        default=start)
    seq = []
    node = target
    while back[node] != -1:
        seq.append(lbl[node])
        node = back[node]
    seq.reverse()
    complete = (target == end)
    coverage = nodes[target][0] / Mres if Mres else 0.0
    return dict(sequence="-".join(seq), residues=seq, score=best[target],
                coverage=coverage, complete=complete,
                precursor_neutral_mass=M)
