"""Estado de trabalho comum a web e desktop: banco, bibliotecas e calculadora."""

from peptmass.core.custom_residues import CustomResidueManager
from peptmass.core.formula_parser import FormulaError, parse_formula
from peptmass.core.mass_calculator import MassCalculator
from peptmass.core.modifications import (DEFAULT_MODIFICATIONS, Modification,
                                         ModificationLibrary)
from peptmass.core.presets import DOPING_PRESETS, GLP_PRESETS, migrate_preset_names

# Presets renomeados ou corrigidos: nome antigo -> sequencia semeada. Sao
# removidos so se o usuario nao os editou.
_OBSOLETE_PRESETS = {
    # TB-500 e' o fragmento 17-23, nao a timosina beta-4 inteira.
    "Timosina beta-4 (TB-500)":
        "SDKPDMAEIEKFDKSKLKKTETQEKNPLPSKETIEQEKQAGES",
}


def _targets(targets, position):
    return frozenset(targets) if targets else frozenset({position})


def _modification_from_row(row):
    return Modification(
        name=row["name"], composition=parse_formula(row["formula"]),
        targets=_targets(row["targets"], row["position"]),
        position=row["position"], description=row.get("description") or "")


class Workspace:
    def __init__(self, db):
        self.db = db
        self.custom_manager = CustomResidueManager(db)
        self.mod_library = ModificationLibrary(custom=self._load_custom_mods())
        self.calc = MassCalculator(self.custom_manager, self.mod_library)
        self._seed_presets()

    def _seed_presets(self):
        """Semeia os peptideos-exemplo uma unica vez por grupo: flags em `meta`
        respeitam o que o usuario apagar depois."""
        for name, sequence in _OBSOLETE_PRESETS.items():
            row = self.db.get_peptide(name)
            if row and row["sequence"] == sequence:
                self.db.delete_peptide(name)
        migrate_preset_names(self.db)
        for flag, presets in (("glp_presets_seeded", GLP_PRESETS),
                              ("doping_presets_seeded_v9", DOPING_PRESETS)):
            if self.db.get_meta(flag):
                continue
            for entry in presets:
                name, sequence, n_term, c_term = entry[:4]
                residue_mods = entry[4] if len(entry) > 4 else "[]"
                if not self.db.get_peptide(name):
                    self.db.save_peptide(name, sequence, n_term, c_term, residue_mods)
            self.db.set_meta(flag, "1")

    def _load_custom_mods(self):
        mods = []
        for row in self.db.list_modifications():
            try:
                mods.append(_modification_from_row(row))
            except FormulaError:
                pass  # formula antiga invalida nao impede a abertura
        return mods

    def custom_mod_ids(self):
        """{nome: id} das modificacoes criadas pelo usuario (as do banco)."""
        return {row["name"]: row["id"] for row in self.db.list_modifications()}

    def add_modification(self, name, formula, targets, position):
        self.db.add_modification(name, formula, targets, position)
        self.mod_library.add(Modification(
            name=name, composition=parse_formula(formula),
            targets=_targets(targets, position), position=position))

    def delete_modification(self, name):
        mod_id = self.custom_mod_ids().get(name)
        if mod_id is None:
            return False
        self.db.delete_modification(mod_id)
        self.mod_library.remove(name)
        # uma custom antiga pode ter sombreado uma padrao de mesmo nome
        for mod in DEFAULT_MODIFICATIONS:
            if mod.name == name:
                self.mod_library.add(mod)
        return True
