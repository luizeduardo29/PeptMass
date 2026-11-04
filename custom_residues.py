"""
custom_residues.py
==================
Gerenciamento de aminoácidos não-naturais / personalizados.

O resíduo é cadastrado pela fórmula molecular do AMINOÁCIDO LIVRE
(ex.: Aib = C4H9NO2). Internamente convertemos para a fórmula do RESÍDUO
(subtraindo H2O), de modo a ser usado de forma idêntica aos naturais.
"""

from dataclasses import dataclass

from formula_parser import (parse_formula, composition_mass, add_composition,
                            composition_to_string, FormulaError)
from i18n import t as _


# Catálogo embutido de resíduos não-naturais comuns.
# Tupla: (nome, abreviação, código, fórmula do AMINOÁCIDO LIVRE).
# Sempre disponíveis; na sequência usam-se entre colchetes, ex.: [Aib], [pGlu].
# O resíduo é calculado como livre − H2O (mesma convenção dos custom).
BUILTIN_RESIDUES = [
    ("alpha-Aminoisobutyric acid", "Aib", "Aib", "C4H9NO2"),
    ("Pyroglutamate (5-oxoproline)", "pGlu", "pGlu", "C5H7NO3"),
    ("3-Mercaptopropionic acid (N-terminal cap)", "Mpa", "Mpa", "C3H6O2S"),
    ("Ornithine", "Orn", "Orn", "C5H12N2O2"),
    ("Norleucine", "Nle", "Nle", "C6H13NO2"),
    ("Norvaline", "Nva", "Nva", "C5H11NO2"),
    ("4-Hydroxyproline", "Hyp", "Hyp", "C5H9NO3"),
    ("Citrulline", "Cit", "Cit", "C6H13N3O3"),
    ("Sarcosine (N-methylglycine)", "Sar", "Sar", "C3H7NO2"),
    ("2-Aminobutyric acid", "Abu", "Abu", "C4H9NO2"),
    ("2,4-Diaminobutyric acid", "Dab", "Dab", "C4H10N2O2"),
    ("2,3-Diaminopropionic acid", "Dap", "Dap", "C3H8N2O2"),
    ("Penicillamine", "Pen", "Pen", "C5H11NO2S"),
    ("alpha-methyl-Leucine", "aMeLeu", "aMeLeu", "C7H15NO2"),
    ("3-(2-Naphthyl)alanine (2-Nal)", "Nal", "Nal", "C13H13NO2"),
    ("2-methyl-Tryptophan", "MeW", "MeW", "C12H14N2O2"),
    ("O-tert-butyl-Serine", "SertBu", "SertBu", "C7H15NO3"),
    ("N-benzyl-Histidine", "HisBzl", "HisBzl", "C13H15N3O2"),
    ("tert-Leucine", "Tle", "Tle", "C6H13NO2"),
]


@dataclass
class CustomResidue:
    name: str
    three: str
    code: str            # código usado na sequência (1+ caracteres)
    free_formula: str    # fórmula do aminoácido livre
    db_id: int = None
    builtin: bool = False  # True = catálogo embutido (não editável/removível)

    @property
    def free_composition(self) -> dict:
        return parse_formula(self.free_formula)

    @property
    def residue_composition(self) -> dict:
        """Fórmula do resíduo = aminoácido livre - H2O."""
        return add_composition(self.free_composition,
                               {"H": 2, "O": 1}, factor=-1)

    @property
    def residue_formula(self) -> str:
        return composition_to_string(self.residue_composition)

    @property
    def mono_mass(self) -> float:
        """Massa monoisotópica do resíduo (sem água)."""
        return composition_mass(self.residue_composition, average=False)

    @property
    def avg_mass(self) -> float:
        return composition_mass(self.residue_composition, average=True)

    @property
    def free_mono_mass(self) -> float:
        """Massa monoisotópica do aminoácido livre."""
        return composition_mass(self.free_composition, average=False)


class CustomResidueManager:
    def __init__(self, db=None):
        self.db = db
        self._residues = {}
        self.reload()

    def reload(self):
        self._residues = {}
        # 1) catálogo embutido (sempre presente, antes dos personalizados)
        for name, three, code, formula in BUILTIN_RESIDUES:
            self._residues[code] = CustomResidue(
                name=name, three=three, code=code, free_formula=formula,
                builtin=True)
        # 2) personalizados do banco (não sobrescrevem os embutidos)
        if not self.db:
            return
        for row in self.db.list_residues():
            if row["code"] in self._residues:
                continue
            r = CustomResidue(name=row["name"], three=row["three"],
                              code=row["code"], free_formula=row["formula"],
                              db_id=row["id"])
            self._residues[r.code] = r

    @staticmethod
    def validate(name, three, code, formula, existing_codes):
        if not name.strip():
            raise ValueError(_("Nome obrigatório."))
        code = code.strip()
        if not (1 <= len(code) <= 10):
            raise ValueError(_("O código deve ter de 1 a 10 caracteres."))
        if not code.isalpha():
            raise ValueError(_("O código deve conter apenas letras (sem dígitos "
                               "ou símbolos). Ex.: Aib, Orn, Nle."))
        from constants import AMINO_ACIDS
        # códigos de 1 letra não podem colidir com um aminoácido natural;
        # multi-caractere é sempre usado entre colchetes, então não há colisão.
        if len(code) == 1 and code in AMINO_ACIDS:
            raise ValueError(_("O código '{c}' já pertence a um aminoácido "
                               "natural.").format(c=code))
        if code in existing_codes:
            raise ValueError(_("O código '{c}' já está em uso.").format(c=code))
        try:
            parse_formula(formula)
        except FormulaError as e:
            raise ValueError(_("Fórmula inválida: {e}").format(e=e))

    def add(self, name, three, code, formula):
        code = code.strip()
        self.validate(name, three, code, formula, self._residues.keys())
        rid = None
        if self.db:
            rid = self.db.add_residue(name, three, code, formula)
        r = CustomResidue(name, three, code, formula, db_id=rid)
        self._residues[code] = r
        return r

    def delete(self, code):
        r = self._residues.get(code)
        if not r or r.builtin:
            return  # embutidos não podem ser removidos
        if self.db and r.db_id:
            self.db.delete_residue(r.db_id)
        self._residues.pop(code, None)

    def get(self, code):
        return self._residues.get(code)

    def all(self):
        return list(self._residues.values())

    def codes(self):
        return set(self._residues.keys())


if __name__ == "__main__":
    mgr = CustomResidueManager()
    aib = mgr.add("Aminoisobutyric acid", "Aib", "U", "C4H9NO2")
    print(f"Aib  resíduo={aib.residue_formula}  "
          f"mono={aib.mono_mass:.6f}  livre={aib.free_mono_mass:.6f}")
    nle = mgr.add("Norleucine", "Nle", "J", "C6H13NO2")
    print(f"Nle  resíduo={nle.residue_formula}  mono={nle.mono_mass:.6f}")
    # Aib resíduo C4H7NO esperado 85.052764
    assert abs(aib.mono_mass - 85.052764) < 1e-4, aib.mono_mass
    print("OK")
