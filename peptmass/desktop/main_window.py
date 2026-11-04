"""Janela principal do PeptMass desktop."""

import sys

from PyQt6.QtGui import QAction, QFont
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QMessageBox, QStatusBar, QTabWidget, QToolBar)

from peptmass.core import i18n
from peptmass.core.constants import PROTON_MASS
from peptmass.core.formula_parser import FormulaError, parse_formula
from peptmass.core.i18n import t as _
from peptmass.core.workspace import Workspace
from peptmass.desktop.dialogs import CustomModDialog, CustomResidueDialog, PubChemDialog
from peptmass.desktop.experimental_tab import ExperimentalTab
from peptmass.desktop.fragment_tab import FragmentTab
from peptmass.desktop.mass_tab import MassTab
from peptmass.desktop.theme import DARK_QSS, LIGHT_QSS
from peptmass.desktop.translation import translate_tree
from peptmass.infra.database import Database


class AppState(Workspace):
    """Workspace do desktop: guarda tambem o peptideo que as abas compartilham."""

    def __init__(self):
        super().__init__(Database())
        self.last_mass_result = None
        self.on_mass_updated = None


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.state = AppState()
        # idioma escolhido fica no banco; aplica antes de construir a interface
        i18n.set_language(self.state.db.get_meta("language") or "pt")
        self.setWindowTitle(
            _("PeptMass 1.0 — Calculadora de Massas e Fragmentação"))
        self.resize(1240, 820)
        self.dark = True

        tabs = QTabWidget()
        self.mass_tab = MassTab(self.state)
        self.frag_tab = FragmentTab(self.state)
        self.exp_tab = ExperimentalTab(self.state)
        self.state.on_mass_updated = self.frag_tab.on_mass_updated
        tabs.addTab(self.mass_tab, _("  Massa Molecular  "))
        tabs.addTab(self.frag_tab, _("  Fragmentação MS/MS  "))
        tabs.addTab(self.exp_tab, _("  Dados experimentais  "))
        self.setCentralWidget(tabs)

        tb = QToolBar()
        self.addToolBar(tb)
        theme_act = QAction(_("☀ / ☾  Tema"), self)
        theme_act.triggered.connect(self._toggle_theme)
        tb.addAction(theme_act)
        mod_act = QAction(_("Nova modificação…"), self)
        mod_act.triggered.connect(self._new_modification)
        tb.addAction(mod_act)
        pubchem_act = QAction(_("🔍 PubChem"), self)
        pubchem_act.triggered.connect(self._pubchem_to_residue)
        tb.addAction(pubchem_act)
        about_act = QAction(_("Sobre"), self)
        about_act.triggered.connect(self._about)
        tb.addAction(about_act)
        # botão de idioma: mostra o idioma PARA O QUAL vai trocar
        lang_act = QAction(
            _("Idioma: EN") if i18n.get_language() == "pt"
            else _("Idioma: PT"), self)
        lang_act.triggered.connect(self._toggle_language)
        tb.addAction(lang_act)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage(
            _("Pronto.  Massa do próton = {p}  |  massas IUPAC").format(
                p=PROTON_MASS))
        self._apply_theme()
        # traduz todos os textos estáticos construídos acima (no-op em PT)
        translate_tree(self)

    def _toggle_language(self):
        new = "en" if i18n.get_language() == "pt" else "pt"
        self.state.db.set_meta("language", new)
        msg = ("Idioma alterado para Inglês. Reinicie o PeptMass para aplicar."
               if new == "en" else
               "Idioma alterado para Português. Reinicie o PeptMass para aplicar.")
        QMessageBox.information(self, _("Idioma"), _(msg))

    def _apply_theme(self):
        QApplication.instance().setStyleSheet(DARK_QSS if self.dark else LIGHT_QSS)

    def _toggle_theme(self):
        self.dark = not self.dark
        self._apply_theme()

    def _pubchem_to_residue(self):
        """Busca no PubChem e abre o cadastro de aminoácido já preenchido."""
        dlg = PubChemDialog(self)
        if dlg.exec() and dlg.result_formula:
            res_dlg = CustomResidueDialog(self)
            res_dlg.formula.setText(dlg.result_formula)
            if dlg.result_name:
                res_dlg.name.setText(dlg.result_name)
            if res_dlg.exec():
                name, three, code, formula = res_dlg.values()
                try:
                    self.state.custom_manager.add(name, three, code, formula)
                    self.state.calc.refresh_table()
                    self.mass_tab.refresh_custom_table()
                    QMessageBox.information(
                        self, _("Sucesso"),
                        _("Aminoácido '{c}' criado a partir do PubChem.")
                        .format(c=code))
                except ValueError as e:
                    QMessageBox.warning(self, _("Erro"), str(e))

    def _new_modification(self):
        dlg = CustomModDialog(self)
        if dlg.exec():
            name, formula, targets, position = dlg.values()
            try:
                parse_formula(formula)
            except FormulaError as e:
                QMessageBox.warning(self, _("Erro"),
                                    _("Fórmula inválida: {e}").format(e=e))
                return
            self.state.add_modification(name, formula, targets, position)
            self.mass_tab.refresh_modifications()
            QMessageBox.information(self, _("Sucesso"),
                                    _("Modificação '{n}' adicionada.")
                                    .format(n=name))

    def _about(self):
        QMessageBox.about(
            self, _("Sobre o PeptMass"),
            "<h3>PeptMass 1.0</h3>"
            "<p>" + _("Calculadora de massas moleculares e fragmentação MS/MS "
                      "de peptídeos e proteínas.") + "</p>"
            "<p>" + _("Massas monoisotópicas IUPAC · próton = 1.007276466812 · "
                      "precisão de 6 casas decimais.") + "</p>"
            "<p>" + _("Séries a/b/c/x/y/z, perdas neutras, multicarga, "
                      "modificações customizadas e aminoácidos não-naturais.")
            + "</p>")


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
