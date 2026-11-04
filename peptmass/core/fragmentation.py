"""
fragmentation.py
================
Geração de séries teóricas de fragmentação MS/MS.

Íons N-terminais:  a, b, c
Íons C-terminais:  x, y, z   (z = Biemann; z• radical para ETD/ECD opcional)

Offsets neutros relativos à soma das massas dos resíduos do fragmento
(verificados contra valores publicados para o peptídeo PEPTIDE):

  a = Σ(N) - CO
  b = Σ(N)
  c = Σ(N) + NH3
  x = Σ(C) + H2O + CO - H2
  y = Σ(C) + H2O
  z = Σ(C) + H2O - NH3
  z•= Σ(C) + H2O - NH3 + H     (radical, z+1)

m/z multicarga: (massa_neutra + z·próton) / z
"""

from dataclasses import dataclass

from peptmass.core.constants import PROTON_MASS
from peptmass.core.formula_parser import add_composition, composition_mass, formula_mass

# deltas neutros monoisotópicos
_CO = formula_mass("CO")      # 27.994915
_H2O = formula_mass("H2O")    # 18.010565
_NH3 = formula_mass("NH3")    # 17.026549
_H2 = formula_mass("H2")      # 2.015650
_H = formula_mass("H")        # 1.007825

# offsets (somados à soma de massas dos resíduos do fragmento)
ION_OFFSETS = {
    "a": -_CO,
    "b": 0.0,
    "c": _NH3,
    "x": _H2O + _CO - _H2,
    "y": _H2O,
    "z": _H2O - _NH3,
    "z+1": _H2O - _NH3 + _H,     # z radical (z-dot)
}

N_TERMINAL_IONS = ("a", "b", "c")

NEUTRAL_LOSSES = {
    "-NH3": _NH3,
    "-H2O": _H2O,
    "-CO": _CO,
}


@dataclass
class Fragment:
    ion_type: str        # 'b', 'y', ...
    number: int          # índice (b5 -> 5)
    charge: int
    neutral_loss: str    # '' ou '-H2O' etc.
    neutral_mass: float  # massa neutra do fragmento (já com perda)
    mz: float
    sequence: str        # subsequência que compõe o fragmento

    @property
    def label(self):
        base = f"{self.ion_type}{self.number}"
        if self.neutral_loss:
            base += self.neutral_loss
        return base


def _fmt_codes(codes):
    """Junta códigos numa subsequência legível, recolocando colchetes nos
    códigos multi-caractere (ex.: ['A','Orn'] -> 'A[Orn]')."""
    return "".join(c if len(c) == 1 else f"[{c}]" for c in codes)


def _residue_masses(peptide_result):
    """Lista das massas monoisotópicas de cada resíduo (com modificações)."""
    masses = []
    seq_codes = []
    for code, info, mods in peptide_result.residues:
        comp = dict(info.composition)
        for mod in mods:
            comp = add_composition(comp, mod.composition)
        masses.append(composition_mass(comp, average=False))
        seq_codes.append(code)
    return masses, seq_codes


def generate_fragments(peptide_result, ion_types, charges,
                       neutral_losses=None, include_no_loss=True,
                       n_term_delta=0.0, c_term_delta=0.0):
    """
    Gera todos os fragmentos solicitados.

    ion_types       : iterável com tipos em {'a','b','c','x','y','z','z+1'}
    charges         : iterável de estados de carga (1..n)
    neutral_losses  : lista de chaves em NEUTRAL_LOSSES (ou None)
    include_no_loss : inclui o fragmento sem perda neutra
    n_term_delta    : massa extra na ponta N (ex.: modificação N-terminal)
    c_term_delta    : massa extra na ponta C (ex.: modificação C-terminal)

    Retorna lista de Fragment.
    """
    masses, codes = _residue_masses(peptide_result)
    n = len(masses)
    if n < 1:
        return []

    neutral_losses = neutral_losses or []
    loss_set = []
    if include_no_loss:
        loss_set.append(("", 0.0))
    for nl in neutral_losses:
        loss_set.append((nl, NEUTRAL_LOSSES[nl]))

    # somas prefixadas (N-terminal) e sufixadas (C-terminal)
    prefix = [0.0] * (n + 1)
    for i in range(n):
        prefix[i + 1] = prefix[i] + masses[i]
    suffix = [0.0] * (n + 1)
    for j in range(n):
        suffix[j + 1] = suffix[j] + masses[n - 1 - j]

    fragments = []

    for ion in ion_types:
        if ion not in ION_OFFSETS:
            continue
        offset = ION_OFFSETS[ion]
        is_n = ion in N_TERMINAL_IONS
        term_delta = n_term_delta if is_n else c_term_delta

        for k in range(1, n):  # 1..n-1 (fragmentos parciais)
            if is_n:
                base = prefix[k] + offset + term_delta
                subseq = _fmt_codes(codes[:k])
            else:
                base = suffix[k] + offset + term_delta
                subseq = _fmt_codes(codes[n - k:])

            for loss_name, loss_mass in loss_set:
                neutral = base - loss_mass
                for z in charges:
                    mz = (neutral + z * PROTON_MASS) / z
                    fragments.append(Fragment(
                        ion_type=ion, number=k, charge=z,
                        neutral_loss=loss_name, neutral_mass=neutral,
                        mz=mz, sequence=subseq))

    return fragments


def match_experimental(fragments, exp_mz_list, tolerance=0.02, ppm=False):
    """
    Casa lista experimental de m/z com fragmentos teóricos.

    tolerance : Da (se ppm=False) ou ppm (se ppm=True)
    Retorna lista de (exp_mz, Fragment, erro) para os casamentos encontrados.
    """
    matches = []
    for exp in exp_mz_list:
        best = None
        best_err = None
        for frag in fragments:
            if ppm:
                err = (exp - frag.mz) / frag.mz * 1e6
                ok = abs(err) <= tolerance
            else:
                err = exp - frag.mz
                ok = abs(err) <= tolerance
            if ok and (best is None or abs(err) < abs(best_err)):
                best, best_err = frag, err
        if best is not None:
            matches.append((exp, best, best_err))
    return matches
