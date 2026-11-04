"""
modifications.py
================
Biblioteca de modificações químicas (PTMs e derivatizações).

Cada modificação é definida por sua composição elementar (delta), o que
garante consistência entre massa monoisotópica e massa média. O alvo indica
onde a modificação pode ser aplicada: 'N-term', 'C-term' ou um conjunto de
resíduos.
"""

from dataclasses import dataclass
from typing import Optional

from peptmass.core.formula_parser import parse_formula, composition_mass, composition_to_string


@dataclass
class Modification:
    name: str
    composition: dict                 # delta elementar (pode ter negativos)
    targets: frozenset                # resíduos OU {'N-term'} / {'C-term'}
    position: str = "residue"         # 'residue' | 'N-term' | 'C-term'
    description: str = ""

    @property
    def mono_delta(self) -> float:
        return composition_mass(self.composition, average=False)

    @property
    def formula_str(self) -> str:
        return composition_to_string(self.composition)

    def applies_to(self, residue: str) -> bool:
        return residue in self.targets


def _mk(name, formula, targets, position="residue", description=""):
    """Atalho: cria modificação a partir de string de fórmula (delta)."""
    # fórmula pode trazer contagens negativas, ex. 'N-1H-1O1' via dict
    if isinstance(formula, dict):
        comp = formula
    else:
        comp = parse_formula(formula)
    return Modification(name=name, composition=comp,
                        targets=frozenset(targets), position=position,
                        description=description)


# ---------------------------------------------------------------------------
# Biblioteca padrão
# ---------------------------------------------------------------------------
DEFAULT_MODIFICATIONS = [
    # ---- N-terminal ----
    _mk("Acetyl",   {"C": 2, "H": 2, "O": 1}, ["N-term"], "N-term",
        "N-terminal acetylation (+42.010565)"),
    _mk("Formyl",   {"C": 1, "O": 1}, ["N-term"], "N-term",
        "Formylation (+27.994915)"),
    _mk("PyroGlu (from Q)", {"N": -1, "H": -3}, ["N-term"], "N-term",
        "Pyroglutamate from N-terminal Gln (-17.026549)"),
    _mk("PyroGlu (from E)", {"H": -2, "O": -1}, ["N-term"], "N-term",
        "Pyroglutamate from N-terminal Glu (-18.010565)"),
    _mk("Myristoyl", {"C": 14, "H": 26, "O": 1}, ["N-term"], "N-term",
        "N-terminal myristoylation (+210.198366)"),
    _mk("3-Hexenoyl", {"C": 6, "H": 8, "O": 1}, ["N-term"], "N-term",
        "N-terminal trans-3-hexenoyl (+96.057515). E.g.: tesamorelin."),
    _mk("Methyl (N-term)", {"C": 1, "H": 2}, ["N-term"], "N-term",
        "N-terminal methylation (+14.015650)"),

    # ---- C-terminal ----
    _mk("Amidation", {"N": 1, "H": 1, "O": -1}, ["C-term"], "C-term",
        "C-terminal amidation (-0.984016)"),
    _mk("Methyl ester", {"C": 1, "H": 2}, ["C-term"], "C-term",
        "C-terminal methyl esterification (+14.015650)"),
    _mk("Ethylamide", {"C": 2, "H": 5, "N": 1, "O": -1}, ["C-term"], "C-term",
        "C-terminal ethylamide / -NHEt (+27.047285). E.g.: leuprolide, buserelin."),
    _mk("Azaglycinamide", {"C": 1, "H": 3, "N": 3, "O": 0}, ["C-term"], "C-term",
        "C-terminal azaglycinamide / -AzaGly-NH2 (+57.032363). E.g.: goserelin."),

    # ---- Resíduo-específicas ----
    _mk("Oxidation", {"O": 1}, ["M", "W", "H", "P"], "residue",
        "Oxidation (+15.994915)"),
    _mk("Phosphorylation", {"H": 1, "P": 1, "O": 3}, ["S", "T", "Y"], "residue",
        "Phosphorylation (+79.966331)"),
    _mk("Carbamidomethyl", {"C": 2, "H": 3, "N": 1, "O": 1}, ["C"], "residue",
        "Carbamidomethylation / Cys alkylation (+57.021464)"),
    _mk("Deamidation", {"N": -1, "H": -1, "O": 1}, ["N", "Q"], "residue",
        "Deamidation N/Q -> D/E (+0.984016)"),
    _mk("Sulfation", {"S": 1, "O": 3}, ["Y", "S", "T"], "residue",
        "Sulfation (+79.956815)"),
    _mk("Methylation", {"C": 1, "H": 2}, ["K", "R", "E", "D"], "residue",
        "Methylation (+14.015650)"),
    _mk("Dimethyl", {"C": 2, "H": 4}, ["K", "R", "N-term"], "residue",
        "Dimethylation (+28.031300)"),
    _mk("Trimethyl", {"C": 3, "H": 6}, ["K"], "residue",
        "Trimethylation (+42.046950)"),
    _mk("Acetyl (K)", {"C": 2, "H": 2, "O": 1}, ["K"], "residue",
        "Lysine acetylation (+42.010565)"),
    _mk("Hydroxylation", {"O": 1}, ["P", "K"], "residue",
        "Hydroxylation (+15.994915)"),
    _mk("Nitration", {"H": -1, "N": 1, "O": 2}, ["Y", "W"], "residue",
        "Nitration (+44.985078)"),
    _mk("Dehydration", {"H": -2, "O": -1}, ["S", "T", "D", "E"], "residue",
        "Dehydration (-18.010565)"),
    _mk("Disulfide (-2H)", {"H": -2}, ["C"], "residue",
        "Disulfide bond formation (-2.015650 per pair)"),

    # ---- Acilações de lisina dos análogos de GLP-1/GIP/GCG ----
    # Cadeia lateral acilada no Nε da Lys. Cada delta foi validado
    # reconstruindo a fórmula do fármaco inteiro (ver descrição).
    _mk("Liraglutide", {"C": 21, "H": 37, "N": 1, "O": 4}, ["K"],
        "residue", "Liraglutide side chain on Lys: γGlu + palmitic "
        "acid (C16). +367.272233. Validates liraglutide C172H265N43O51."),
    _mk("Semaglutide", {"C": 35, "H": 61, "N": 3, "O": 12}, ["K"],
        "residue", "Semaglutide side chain on Lys: 2×AEEA + γGlu + "
        "C18 diacid. +715.425476. Validates semaglutide C187H291N45O59."),
    _mk("Tirzepatide", {"C": 37, "H": 65, "N": 3, "O": 12}, ["K"],
        "residue", "Tirzepatide side chain on Lys: 2×AEEA + γGlu + "
        "C20 diacid. +743.456776. Validates tirzepatide C225H348N48O68."),
    _mk("Retatrutide", {"C": 31, "H": 54, "N": 2, "O": 9}, ["K"],
        "residue", "Retatrutide side chain on Lys: 1×AEEA + γGlu + "
        "C20 diacid. +598.382932. Validates retatrutide C221H342N46O68."),

    # ---- Outras acilações / pontes usadas em fármacos peptídicos ----
    _mk("Degludec", {"C": 21, "H": 35, "N": 1, "O": 6}, ["K"], "residue",
        "Insulin degludec side chain on LysB29: γGlu + C16 diacid "
        "(+397.246438). Validates degludec C274H411N65O81S6."),
    _mk("Myristoyl (K)", {"C": 14, "H": 26, "O": 1}, ["K"], "residue",
        "Lysine myristoylation (C14) (+210.198366). "
        "E.g.: insulin detemir on LysB29."),
    _mk("Octanoyl", {"C": 8, "H": 14, "O": 1}, ["S", "T", "K"], "residue",
        "Octanoylation (C8), hydroxyl/amino acylation (+126.104465). "
        "E.g.: ghrelin on Ser3."),
    _mk("Maleimidopropionyl (DAC)", {"C": 7, "H": 5, "N": 1, "O": 3}, ["K"],
        "residue", "3-maleimidopropionyl on Lys (+151.026943). "
        "E.g.: CJC-1295 with DAC."),
    _mk("Lactam bridge", {"H": -2, "O": -1}, ["D", "E", "K"], "residue",
        "Lactam bridge (side chain to side chain cyclization, -18.010565). "
        "E.g.: melanotan II (Asp-Lys)."),
]


class ModificationLibrary:
    """Coleção de modificações padrão + customizadas (do banco)."""

    def __init__(self, custom=None):
        self._mods = {}
        for m in DEFAULT_MODIFICATIONS:
            self._mods[m.name] = m
        if custom:
            for m in custom:
                self._mods[m.name] = m

    def add(self, mod: Modification):
        self._mods[mod.name] = mod

    def remove(self, name: str):
        self._mods.pop(name, None)

    def get(self, name: str) -> Optional[Modification]:
        return self._mods.get(name)

    def all(self):
        return list(self._mods.values())

    def names(self):
        return list(self._mods.keys())

    def for_position(self, position: str):
        return [m for m in self._mods.values() if m.position == position]

    def for_residue(self, residue: str):
        return [m for m in self._mods.values()
                if m.position == "residue" and residue in m.targets]
