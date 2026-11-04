"""
formula_parser.py
=================
Parser de fórmulas moleculares.

Suporta:
  - Elementos de 1 ou 2 letras  (C, H, Na, Cl, Se ...)
  - Multiplicadores             (C6H12O6)
  - Parênteses aninhados        (CH3(CH2)4COOH, (PEG)3 ...)
  - Composições negativas       (para deltas de modificação)

Retorna composição elementar (dict) e massas monoisotópica e média.
"""

import re
from collections import defaultdict

from constants import ELEMENTS_MONO, ELEMENTS_AVG
from i18n import t as _

_TOKEN_RE = re.compile(r"([A-Z][a-z]?|\(|\))(-?\d*)")


class FormulaError(ValueError):
    """Erro de fórmula molecular inválida."""


def parse_formula(formula: str) -> dict:
    """
    Converte uma fórmula molecular em um dicionário {elemento: contagem}.

    >>> parse_formula("C4H9NO2")
    {'C': 4, 'H': 9, 'N': 1, 'O': 2}
    """
    if formula is None:
        raise FormulaError(_("Fórmula vazia."))
    formula = formula.strip().replace(" ", "")
    if not formula:
        raise FormulaError(_("Fórmula vazia."))

    stack = [defaultdict(int)]
    i = 0
    n = len(formula)

    while i < n:
        ch = formula[i]
        if ch == "(":
            stack.append(defaultdict(int))
            i += 1
        elif ch == ")":
            # lê multiplicador após o parêntese
            i += 1
            m = re.match(r"\d+", formula[i:])
            mult = int(m.group()) if m else 1
            if m:
                i += len(m.group())
            if len(stack) < 2:
                raise FormulaError(_("Parênteses desbalanceados."))
            group = stack.pop()
            for el, count in group.items():
                stack[-1][el] += count * mult
        else:
            m = re.match(r"([A-Z][a-z]?)(-?\d*)", formula[i:])
            if not m or not m.group(1):
                raise FormulaError(_("Caractere inesperado em '{f}' posição {i}: "
                                     "'{c}'").format(f=formula, i=i,
                                                     c=formula[i]))
            el = m.group(1)
            if el not in ELEMENTS_MONO:
                raise FormulaError(_("Elemento desconhecido: '{el}'").format(el=el))
            count = int(m.group(2)) if m.group(2) not in ("", "-") else 1
            stack[-1][el] += count
            i += len(m.group(0))

    if len(stack) != 1:
        raise FormulaError(_("Parênteses desbalanceados."))

    return {el: c for el, c in stack[0].items() if c != 0}


def composition_mass(composition: dict, average: bool = False) -> float:
    """Massa de uma composição elementar (monoisotópica por padrão)."""
    table = ELEMENTS_AVG if average else ELEMENTS_MONO
    total = 0.0
    for el, count in composition.items():
        if el not in table:
            raise FormulaError(
                _("Elemento sem massa tabelada: '{el}'").format(el=el))
        total += table[el] * count
    return total


def formula_mass(formula: str, average: bool = False) -> float:
    """Massa direta a partir de uma string de fórmula."""
    return composition_mass(parse_formula(formula), average=average)


def add_composition(a: dict, b: dict, factor: int = 1) -> dict:
    """Soma duas composições (b multiplicada por `factor`)."""
    out = defaultdict(int, a)
    for el, c in b.items():
        out[el] += c * factor
    return {el: c for el, c in out.items() if c != 0}


def composition_to_string(composition: dict) -> str:
    """Formata composição em string legível, ordem de Hill (C, H, demais)."""
    if not composition:
        return ""
    parts = []
    order = []
    if "C" in composition:
        order.append("C")
    if "H" in composition:
        order.append("H")
    order += sorted(el for el in composition if el not in ("C", "H"))
    for el in order:
        c = composition[el]
        if c == 0:
            continue
        parts.append(el if c == 1 else f"{el}{c}")
    return "".join(parts)
