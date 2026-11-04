"""
mass_calculator.py
==================
Núcleo de cálculo de massas de peptídeos/proteínas.

Funcionalidades:
  - Tabela unificada de resíduos (naturais + personalizados)
  - Parsing de sequência com modificações inline  X(Mod)
  - Aplicação de modificações N-term / C-term / por resíduo
  - Massa monoisotópica e média
  - Composição elementar completa
  - Tabela de m/z para múltiplos estados de carga
  - Distribuição isotópica teórica
"""

import re
from dataclasses import dataclass, field
from collections import defaultdict

from peptmass.core.constants import (AMINO_ACIDS, PROTON_MASS, ELEMENTS_MONO, ISOTOPES)
from peptmass.core.formula_parser import (parse_formula, composition_mass, add_composition,
                            composition_to_string)
from peptmass.core.modifications import ModificationLibrary
from peptmass.core.custom_residues import CustomResidue, BUILTIN_RESIDUES
from peptmass.core.i18n import t as _


@dataclass
class ResidueInfo:
    code: str
    name: str
    three: str
    composition: dict          # composição do resíduo (sem água)


def build_residue_table(custom_manager=None):
    """Dicionário {código: ResidueInfo} com naturais + embutidos + custom."""
    table = {}
    for code, info in AMINO_ACIDS.items():
        table[code] = ResidueInfo(code, info["name"], info["three"],
                                  parse_formula(info["formula"]))
    # resíduos não-naturais embutidos (sempre disponíveis, como os naturais)
    for name, three, code, free_formula in BUILTIN_RESIDUES:
        res = CustomResidue(name, three, code, free_formula, builtin=True)
        table[code] = ResidueInfo(code, name, three,
                                  res.residue_composition)
    if custom_manager:
        for r in custom_manager.all():
            table[r.code] = ResidueInfo(r.code, r.name, r.three,
                                        r.residue_composition)
    return table


@dataclass
class PeptideResult:
    sequence: str
    residues: list                  # lista de (código, ResidueInfo, [mods])
    composition: dict
    mono_mass: float
    avg_mass: float
    n_term_mod: object = None
    c_term_mod: object = None
    warnings: list = field(default_factory=list)
    n_chains: int = 1               # >1 para proteínas de múltiplas cadeias

    @property
    def formula(self):
        return composition_to_string(self.composition)


class SequenceError(ValueError):
    pass


# Separador de cadeias independentes (ex.: insulina = cadeia A / cadeia B).
# Cada cadeia contribui com sua própria água terminal.
CHAIN_SEP = "/"


def _split_chains(cleaned_seq):
    return [c for c in cleaned_seq.split(CHAIN_SEP) if c]


# Um token é UM resíduo opcionalmente seguido de uma modificação inline (...):
#   - letra solta            -> aminoácido natural (1 caractere)
#   - [Codigo] entre colchetes -> resíduo de código multi-caractere (não-natural)
# Ex.: "A[Orn]G(Acetyl)" -> A , Orn , G(Acetyl)
_TOKEN_RE = re.compile(
    r"(?:\[(?P<multi>[A-Za-z]{1,10})\]|(?P<single>[A-Za-z]))"
    r"(?:\((?P<mod>[^)]*)\))?")


def _code_from_match(m):
    """Código do resíduo a partir de um match do tokenizer.

    Letra solta é normalizada para maiúscula (como os naturais); código entre
    colchetes é usado literalmente (preserva caixa, ex.: 'Aib')."""
    multi = m.group("multi")
    return multi if multi is not None else m.group("single").upper()


class MassCalculator:
    def __init__(self, custom_manager=None, mod_library=None):
        self.custom_manager = custom_manager
        self.mod_library = mod_library or ModificationLibrary()
        self.refresh_table()

    def refresh_table(self):
        self.residue_table = build_residue_table(self.custom_manager)

    # ------------------------------------------------------------------
    def validate_sequence(self, sequence: str):
        """Retorna (ok, mensagem). Caracteres inválidos são reportados."""
        seq = self._clean(sequence)
        invalid = []
        residual = ""
        n_tokens = 0
        for chain in _split_chains(seq):
            for m in _TOKEN_RE.finditer(chain):
                n_tokens += 1
                code = _code_from_match(m)
                if code not in self.residue_table:
                    invalid.append(code)
            # detecta lixo que não casa com o tokenizer (por cadeia)
            residual += _TOKEN_RE.sub("", chain)
        if invalid:
            return False, _("Resíduo(s) desconhecido(s): {x}").format(
                x=', '.join(sorted(set(invalid))))
        if residual.strip():
            return False, _("Caractere(s) inválido(s): {x}").format(x=residual)
        if n_tokens == 0:
            return False, _("Sequência vazia.")
        return True, _("Sequência válida.")

    def unknown_codes(self, sequence: str):
        """
        Lista (na ordem de aparição, sem duplicatas) os códigos de resíduo
        de 1 letra que NÃO estão na tabela atual — naturais ou personalizados.

        Usado pela interface para oferecer o cadastro assistido via PubChem
        dos aminoácidos não-convencionais presentes na sequência.
        """
        seq = self._clean(sequence)
        result, seen = [], set()
        for chain in _split_chains(seq):
            for m in _TOKEN_RE.finditer(chain):
                code = _code_from_match(m)
                if code not in self.residue_table and code not in seen:
                    seen.add(code)
                    result.append(code)
        return result

    def residue_codes(self, sequence: str):
        """Lista ordenada dos códigos de resíduo da sequência (tokenizada),
        contínua através das cadeias.

        Usada pela interface para mapear posições reais de resíduo, já que com
        códigos multi-caractere não dá para indexar a string crua."""
        seq = self._clean(sequence)
        return [_code_from_match(m)
                for chain in _split_chains(seq)
                for m in _TOKEN_RE.finditer(chain)]

    @staticmethod
    def _clean(sequence: str) -> str:
        # remove espaços, quebras de linha, números e pontuação solta
        return re.sub(r"[\s\d]+", "", sequence or "")

    # ------------------------------------------------------------------
    def parse(self, sequence, n_term_mod=None, c_term_mod=None,
              residue_mods=None):
        """
        Faz o parsing e aplica modificações.

        residue_mods: dict {indice_0based: nome_modificacao} para mods
                      aplicadas via interface (além das inline X(Mod)).
        Retorna PeptideResult.
        """
        seq = self._clean(sequence)
        residue_mods = residue_mods or {}
        warnings = []

        chains = _split_chains(seq)
        parsed = []   # (code, ResidueInfo, [Modification])
        idx = 0
        for chain in chains:
            for m in _TOKEN_RE.finditer(chain):
                code = _code_from_match(m)
                inline_mod_name = m.group("mod")
                info = self.residue_table.get(code)
                if not info:
                    raise SequenceError(
                        _("Resíduo desconhecido: '{c}'").format(c=code))
                mods = []
                if inline_mod_name:
                    mod = self.mod_library.get(inline_mod_name)
                    if not mod:
                        raise SequenceError(
                            _("Modificação desconhecida: '{m}'").format(
                                m=inline_mod_name))
                    if mod.position == "residue" and not mod.applies_to(code):
                        warnings.append(
                            _("'{m}' normalmente não se aplica a {c}.").format(
                                m=inline_mod_name, c=code))
                    mods.append(mod)
                if idx in residue_mods:
                    mod = self.mod_library.get(residue_mods[idx])
                    if mod:
                        if mod.position == "residue" and not mod.applies_to(code):
                            warnings.append(
                                _("'{m}' normalmente não se aplica a {c} "
                                  "(posição {p}).").format(
                                      m=mod.name, c=code, p=idx + 1))
                        mods.append(mod)
                parsed.append((code, info, mods))
                idx += 1

        if not parsed:
            raise SequenceError(_("Sequência vazia."))
        if len(chains) > 1:
            warnings.append(
                _("{n} cadeias independentes: a fragmentação MS/MS não se "
                  "aplica a múltiplas cadeias.").format(n=len(chains)))

        # composição = Σ(resíduos) + UMA água terminal POR CADEIA + deltas
        comp = defaultdict(int)
        comp = add_composition(comp, {"H": 2 * len(chains), "O": len(chains)})
        for code, info, mods in parsed:
            comp = add_composition(comp, info.composition)
            for mod in mods:
                comp = add_composition(comp, mod.composition)

        n_mod_obj = self.mod_library.get(n_term_mod) if n_term_mod else None
        c_mod_obj = self.mod_library.get(c_term_mod) if c_term_mod else None
        if n_mod_obj:
            comp = add_composition(comp, n_mod_obj.composition)
        if c_mod_obj:
            comp = add_composition(comp, c_mod_obj.composition)

        # verifica composição negativa (erro de modificação)
        for el, c in comp.items():
            if c < 0:
                warnings.append(
                    _("Composição com {el} negativo: verifique as "
                      "modificações.").format(el=el))

        mono = composition_mass(comp, average=False)
        avg = composition_mass(comp, average=True)

        return PeptideResult(
            sequence=seq, residues=parsed, composition=dict(comp),
            mono_mass=mono, avg_mass=avg,
            n_term_mod=n_mod_obj, c_term_mod=c_mod_obj, warnings=warnings,
            n_chains=len(chains))

    # ------------------------------------------------------------------
    @staticmethod
    def mz(neutral_mass: float, charge: int) -> float:
        """m/z = (M + z·próton) / z"""
        if charge == 0:
            return neutral_mass
        return (neutral_mass + charge * PROTON_MASS) / abs(charge)

    def charge_table(self, neutral_mass: float, charges):
        """Retorna lista de (z, m/z) para os estados de carga pedidos."""
        return [(z, self.mz(neutral_mass, z)) for z in charges]

    # ------------------------------------------------------------------
    def isotopic_distribution(self, composition: dict, max_peaks: int = 12,
                              prune: float = 1e-6):
        """
        Distribuição isotópica teórica por convolução dos padrões elementares.

        Retorna lista de (massa, intensidade_relativa) normalizada (pico
        base = 100). Adequado para peptídeos e, com poda, proteínas grandes.
        """
        # cada distribuição: lista de (massa, prob), começando com monômero
        dist = [(0.0, 1.0)]

        def convolve(d, isotopes):
            new = defaultdict(float)
            masses = {}
            # agrupar por massa nominal (inteiro) para limitar explosão
            for m1, p1 in d:
                for m2, p2 in isotopes:
                    key = round((m1 + m2))   # bucket por unidade de massa
                    prob = p1 * p2
                    if prob < prune:
                        continue
                    # média ponderada de massa dentro do bucket
                    if key in new:
                        old_p = new[key]
                        old_m = masses[key]
                        total = old_p + prob
                        masses[key] = (old_m * old_p + (m1 + m2) * prob) / total
                        new[key] = total
                    else:
                        new[key] = prob
                        masses[key] = m1 + m2
            # poda e ordenação
            items = [(masses[k], new[k]) for k in new]
            items.sort(key=lambda x: x[0])
            # mantém apenas picos relevantes
            mx = max(p for _, p in items)
            items = [(m, p) for m, p in items if p >= mx * prune]
            return items[: max_peaks + 8]

        for el, count in composition.items():
            if count <= 0 or el not in ISOTOPES:
                # elementos sem dados isotópicos: trata como monoisotópico
                if el in ELEMENTS_MONO and count > 0:
                    dist = convolve(dist, [(ELEMENTS_MONO[el] * count, 1.0)])
                continue
            # exponenciação por quadrados para n átomos
            power = ISOTOPES[el]
            remaining = count
            elem = [(0.0, 1.0)]
            while remaining:
                if remaining & 1:
                    elem = convolve(elem, power)
                remaining >>= 1
                if remaining:
                    power = convolve(power, power)
            dist = convolve(dist, elem)

        # normaliza para o pico base = 100
        if not dist:
            return []
        mx = max(p for _, p in dist)
        result = [(m, 100.0 * p / mx) for m, p in dist if p / mx >= prune]
        result.sort(key=lambda x: x[0])
        return result[:max_peaks]
