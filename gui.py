"""
gui.py
======
Interface gráfica (PyQt6) do PeptMass.

Duas abas principais:
  ABA 1 — Massa Molecular
  ABA 2 — Fragmentação MS/MS

Recursos: tema claro/escuro, tabelas ordenáveis, cópia para a área de
transferência, busca rápida, cálculo automático, gráficos teóricos,
banco de aminoácidos personalizados, importação FASTA e exportações.
"""

import sys
import os

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import (QAction, QFont, QGuiApplication, QKeySequence,
                         QShortcut, QPixmap)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QFormLayout, QLineEdit, QPlainTextEdit, QPushButton, QLabel,
    QComboBox, QCheckBox, QSpinBox, QDoubleSpinBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QGroupBox, QDialog, QDialogButtonBox,
    QMessageBox, QFileDialog, QSplitter, QListWidget, QListWidgetItem,
    QAbstractItemView, QToolBar, QStatusBar, QScrollArea, QMenu,
)

from constants import AMINO_ACIDS, PROTON_MASS
from database import Database
from custom_residues import CustomResidueManager
from modifications import ModificationLibrary, Modification
from formula_parser import parse_formula, composition_mass, FormulaError
from mass_calculator import MassCalculator, SequenceError
from fragmentation import (generate_fragments, match_experimental,
                           N_TERMINAL_IONS, C_TERMINAL_IONS, NEUTRAL_LOSSES)
import exporters
import pubchem
import denovo
import scoring
import identification
import i18n
from i18n import t as _


# ===========================================================================
# Temas
# ===========================================================================
DARK_QSS = """
* { font-family: 'Segoe UI', 'Helvetica Neue', Arial; font-size: 10pt; }
QMainWindow, QWidget { background: #1e2228; color: #e6e9ef; }
QGroupBox { border: 1px solid #333a44; border-radius: 7px; margin-top: 10px;
            padding-top: 8px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px;
                   color: #8fb4ff; }
QLineEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background: #262b33; border: 1px solid #3a414d; border-radius: 5px;
    padding: 5px; color: #e6e9ef; selection-background-color: #3d6fd6; }
QLineEdit:focus, QPlainTextEdit:focus { border: 1px solid #5b8bff; }
QPushButton { background: #2f3640; border: 1px solid #424b58; border-radius: 6px;
              padding: 7px 14px; color: #e6e9ef; }
QPushButton:hover { background: #3a4250; }
QPushButton:pressed { background: #2a303a; }
QPushButton#accent { background: #3d6fd6; border: none; font-weight: 600; }
QPushButton#accent:hover { background: #4d7fe6; }
QTabWidget::pane { border: 1px solid #333a44; border-radius: 6px; }
QTabBar::tab { background: #262b33; padding: 9px 18px; border-top-left-radius: 6px;
               border-top-right-radius: 6px; color: #aeb6c2; margin-right: 2px; }
QTabBar::tab:selected { background: #3d6fd6; color: white; font-weight: 600; }
QTableWidget { background: #20252c; gridline-color: #2f3640;
               border: 1px solid #333a44; border-radius: 6px; }
QHeaderView::section { background: #2c333d; color: #cfd6e2; padding: 6px;
                       border: none; border-right: 1px solid #1e2228;
                       font-weight: 600; }
QTableWidget::item:selected { background: #3d6fd6; color: white; }
QCheckBox { spacing: 6px; }
QLabel#result { font-size: 15pt; font-weight: 700; color: #7fe3a0; }
QLabel#resultavg { font-size: 13pt; font-weight: 600; color: #f0c674; }
QLabel#formula { font-size: 11pt; color: #8fb4ff; font-family: monospace; }
QStatusBar { background: #181c22; color: #8a93a0; }
QToolBar { background: #181c22; border: none; spacing: 4px; padding: 4px; }
QScrollArea { border: none; }
"""

LIGHT_QSS = """
* { font-family: 'Segoe UI', 'Helvetica Neue', Arial; font-size: 10pt; }
QMainWindow, QWidget { background: #f4f6f9; color: #1f2733; }
QGroupBox { border: 1px solid #d4dae3; border-radius: 7px; margin-top: 10px;
            padding-top: 8px; font-weight: 600; background: #ffffff; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px;
                   color: #2c5fb8; }
QLineEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background: #ffffff; border: 1px solid #ccd4de; border-radius: 5px;
    padding: 5px; color: #1f2733; selection-background-color: #cfe0ff; }
QLineEdit:focus, QPlainTextEdit:focus { border: 1px solid #2c5fb8; }
QPushButton { background: #ffffff; border: 1px solid #ccd4de; border-radius: 6px;
              padding: 7px 14px; }
QPushButton:hover { background: #eef2f8; }
QPushButton#accent { background: #2c5fb8; border: none; color: white;
                     font-weight: 600; }
QPushButton#accent:hover { background: #3a6fc8; }
QTabWidget::pane { border: 1px solid #d4dae3; border-radius: 6px;
                   background: #ffffff; }
QTabBar::tab { background: #e6ebf2; padding: 9px 18px; border-top-left-radius: 6px;
               border-top-right-radius: 6px; color: #5a6473; margin-right: 2px; }
QTabBar::tab:selected { background: #2c5fb8; color: white; font-weight: 600; }
QTableWidget { background: #ffffff; gridline-color: #e3e8ef;
               border: 1px solid #d4dae3; border-radius: 6px; }
QHeaderView::section { background: #eef2f8; color: #3a4757; padding: 6px;
                       border: none; border-right: 1px solid #d4dae3;
                       font-weight: 600; }
QTableWidget::item:selected { background: #cfe0ff; color: #1f2733; }
QLabel#result { font-size: 15pt; font-weight: 700; color: #1a7f3c; }
QLabel#resultavg { font-size: 13pt; font-weight: 600; color: #b5811a; }
QLabel#formula { font-size: 11pt; color: #2c5fb8; font-family: monospace; }
QStatusBar { background: #e6ebf2; color: #5a6473; }
QToolBar { background: #e6ebf2; border: none; spacing: 4px; padding: 4px; }
QScrollArea { border: none; }
"""


# ===========================================================================
# Utilidades de tabela
# ===========================================================================
class NumericItem(QTableWidgetItem):
    """Item de tabela que ordena numericamente."""
    def __init__(self, value, text=None):
        super().__init__(text if text is not None else str(value))
        self._value = value
        self.setFlags(self.flags() & ~Qt.ItemFlag.ItemIsEditable)

    def __lt__(self, other):
        try:
            return self._value < other._value
        except AttributeError:
            return super().__lt__(other)


class _HoverTip:
    """Tooltip de hover para figuras matplotlib (sticks/picos).

    Detecta o ponto mais próximo do cursor (em pixels, no eixo x) e mostra uma
    anotação. A conexão de evento é feita uma vez no canvas; a cada replot
    chame rebind(ax) e depois set_points([(x, y, texto), ...])."""

    def __init__(self, canvas):
        self.canvas = canvas
        self.ax = None
        self.ann = None
        self.points = []
        canvas.mpl_connect("motion_notify_event", self._on_move)

    def rebind(self, ax):
        self.ax = ax
        self.points = []
        self.ann = ax.annotate(
            "", xy=(0, 0), xytext=(10, 12), textcoords="offset points",
            fontsize=8, visible=False, zorder=20,
            bbox=dict(boxstyle="round,pad=0.4", fc="#ffffcc", ec="#888888",
                      alpha=0.95))

    def set_points(self, points):
        self.points = points

    def _on_move(self, event):
        if self.ann is None:
            return
        if event.inaxes is not self.ax or not self.points or event.x is None:
            if self.ann.get_visible():
                self.ann.set_visible(False)
                self.canvas.draw_idle()
            return
        trans = self.ax.transData
        best, best_d = None, 1e9
        for x, y, text in self.points:
            px, _py = trans.transform((x, y))
            d = abs(px - event.x)
            if d < best_d:
                best_d, best = d, (x, y, text)
        if best and best_d < 12:
            self.ann.xy = (best[0], best[1])
            self.ann.set_text(best[2])
            self.ann.set_visible(True)
        elif self.ann.get_visible():
            self.ann.set_visible(False)
        else:
            return
        self.canvas.draw_idle()


def make_table(headers):
    t = QTableWidget()
    t.setColumnCount(len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.setSortingEnabled(True)
    t.setAlternatingRowColors(True)
    t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    t.verticalHeader().setVisible(False)
    t.horizontalHeader().setSectionResizeMode(
        QHeaderView.ResizeMode.Stretch)
    t.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    return t


def copy_table_selection(table):
    sel = table.selectedRanges()
    if not sel:
        return
    rng = sel[0]
    lines = []
    for r in range(rng.topRow(), rng.bottomRow() + 1):
        cells = []
        for c in range(rng.leftColumn(), rng.rightColumn() + 1):
            item = table.item(r, c)
            cells.append(item.text() if item else "")
        lines.append("\t".join(cells))
    QGuiApplication.clipboard().setText("\n".join(lines))


# ===========================================================================
# Diálogo: aminoácido personalizado
# ===========================================================================
class CustomResidueDialog(QDialog):
    def __init__(self, parent=None, initial_code="", initial_name="",
                 lock_code=False):
        super().__init__(parent)
        self.setWindowTitle("Novo aminoácido personalizado")
        self.setMinimumWidth(420)
        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.name = QLineEdit(initial_name)
        self.three = QLineEdit()
        self.code = QLineEdit(); self.code.setMaxLength(10)
        self.code.setPlaceholderText("ex.: Aib, Orn (use [Aib] na sequência)")
        if initial_code:
            self.code.setText(initial_code)
        if lock_code:
            # código vem da sequência digitada — não deixa alterar
            self.code.setReadOnly(True)
        self.formula = QLineEdit()
        self.formula.setPlaceholderText("ex.: C4H9NO2 (aminoácido livre)")
        form.addRow("Nome:", self.name)
        form.addRow("Abreviação:", self.three)
        form.addRow("Código (1–3 letras):", self.code)
        form.addRow("Fórmula molecular:", self.formula)
        lay.addLayout(form)

        pc_btn = QPushButton("🔍  Buscar no PubChem…")
        pc_btn.clicked.connect(self._search_pubchem)
        lay.addWidget(pc_btn)

        self.preview = QLabel("Massa monoisotópica do resíduo: —")
        self.preview.setObjectName("formula")
        lay.addWidget(self.preview)
        self.formula.textChanged.connect(self._update_preview)

        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                              QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        i18n.translate_tree(self)

    def _update_preview(self):
        try:
            comp = parse_formula(self.formula.text())
            comp_res = dict(comp)
            comp_res["H"] = comp_res.get("H", 0) - 2
            comp_res["O"] = comp_res.get("O", 0) - 1
            mono = composition_mass(comp_res, average=False)
            self.preview.setText(
                _("Massa monoisotópica do resíduo: {m} Da").format(
                    m=f"{mono:.6f}"))
        except FormulaError:
            self.preview.setText(
                _("Massa monoisotópica do resíduo: (fórmula inválida)"))

    def values(self):
        return (self.name.text().strip(), self.three.text().strip(),
                self.code.text().strip(), self.formula.text().strip())

    def _search_pubchem(self):
        dlg = PubChemDialog(self, initial=self.name.text().strip())
        if dlg.exec() and dlg.result_formula:
            self.formula.setText(dlg.result_formula)
            if not self.name.text().strip() and dlg.result_name:
                self.name.setText(dlg.result_name)


# ===========================================================================
# Diálogo: modificação customizada
# ===========================================================================
class CustomModDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nova modificação customizada")
        self.setMinimumWidth(440)
        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.name = QLineEdit()
        self.formula = QLineEdit()
        self.formula.setPlaceholderText("delta elementar, ex.: C2H2O ou H-1N-1O")
        self.position = QComboBox()
        self.position.addItems(["residue", "N-term", "C-term"])
        self.targets = QLineEdit()
        self.targets.setPlaceholderText("resíduos alvo, ex.: STY  (vazio = qualquer)")
        form.addRow("Nome:", self.name)
        form.addRow("Fórmula (delta):", self.formula)
        form.addRow("Posição:", self.position)
        form.addRow("Alvos:", self.targets)
        lay.addLayout(form)
        pc_btn = QPushButton("🔍  Buscar fórmula no PubChem…")
        pc_btn.clicked.connect(self._search_pubchem)
        lay.addWidget(pc_btn)
        self.preview = QLabel("Delta monoisotópico: —")
        self.preview.setObjectName("formula")
        lay.addWidget(self.preview)
        self.formula.textChanged.connect(self._upd)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                              QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        i18n.translate_tree(self)

    def _upd(self):
        try:
            mono = composition_mass(parse_formula(self.formula.text()))
            self.preview.setText(
                _("Delta monoisotópico: {m} Da").format(m=f"{mono:+.6f}"))
        except FormulaError:
            self.preview.setText(_("Delta monoisotópico: (fórmula inválida)"))

    def values(self):
        return (self.name.text().strip(), self.formula.text().strip(),
                self.targets.text().strip().upper(),
                self.position.currentText())

    def _search_pubchem(self):
        dlg = PubChemDialog(self, initial=self.name.text().strip())
        if dlg.exec() and dlg.result_formula:
            self.formula.setText(dlg.result_formula)
            if not self.name.text().strip() and dlg.result_name:
                self.name.setText(dlg.result_name)


# ===========================================================================
# Busca no PubChem (thread + diálogo)
# ===========================================================================
class PubChemWorker(QThread):
    """Executa a busca no PubChem fora da thread da interface."""
    found = pyqtSignal(object)        # PubChemCompound
    failed = pyqtSignal(str)
    png_ready = pyqtSignal(bytes)

    def __init__(self, query, kind="name", fetch_png=True):
        super().__init__()
        self.query = query
        self.kind = kind
        self.fetch_png = fetch_png

    def run(self):
        try:
            if self.kind == "cid":
                comp = pubchem.search_by_cid(int(self.query))
            elif self.kind == "formula":
                cids = pubchem.search_by_formula(self.query, max_results=1)
                if not cids:
                    raise pubchem.PubChemError("Nenhum composto com essa fórmula.")
                comp = pubchem.search_by_cid(cids[0])
            else:
                comp = pubchem.search_by_name(self.query)
            self.found.emit(comp)
            if self.fetch_png and comp.cid:
                try:
                    self.png_ready.emit(pubchem.fetch_structure_png(comp.cid))
                except pubchem.PubChemError:
                    pass
        except pubchem.PubChemError as e:
            self.failed.emit(str(e))
        except Exception as e:
            self.failed.emit(f"Erro inesperado: {e}")


class PubChemDialog(QDialog):
    """
    Busca uma molécula no PubChem e devolve a fórmula (e o nome).
    Use `result_formula` e `result_name` após exec().
    """
    def __init__(self, parent=None, initial=""):
        super().__init__(parent)
        self.setWindowTitle("Buscar molécula no PubChem")
        self.setMinimumWidth(480)
        self.compound = None
        self.result_formula = None
        self.result_name = None
        self._worker = None

        lay = QVBoxLayout(self)
        srow = QHBoxLayout()
        self.kind = QComboBox(); self.kind.addItems(["Nome", "CID", "Fórmula"])
        srow.addWidget(self.kind)
        self.query = QLineEdit(initial)
        self.query.setPlaceholderText("ex.: ornithine, citrulline, 6262, C5H12N2O2")
        self.query.returnPressed.connect(self._search)
        srow.addWidget(self.query)
        self.search_btn = QPushButton("Buscar"); self.search_btn.setObjectName("accent")
        self.search_btn.clicked.connect(self._search)
        srow.addWidget(self.search_btn)
        lay.addLayout(srow)

        self.status = QLabel("Digite um termo e clique em Buscar.")
        self.status.setWordWrap(True)
        lay.addWidget(self.status)

        body = QHBoxLayout()
        self.image = QLabel()
        self.image.setFixedSize(180, 180)
        self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image.setStyleSheet("border:1px solid #555; border-radius:6px;")
        body.addWidget(self.image)

        info_box = QGroupBox("Resultado")
        ig = QFormLayout(info_box)
        self.l_name = QLabel("—"); self.l_name.setWordWrap(True)
        self.l_cid = QLabel("—")
        self.l_formula = QLabel("—"); self.l_formula.setObjectName("formula")
        self.l_mono = QLabel("—")
        self.l_pcmono = QLabel("—")
        self.l_avg = QLabel("—")
        ig.addRow("Nome IUPAC:", self.l_name)
        ig.addRow("CID:", self.l_cid)
        ig.addRow("Fórmula:", self.l_formula)
        ig.addRow("Mono (PeptMass):", self.l_mono)
        ig.addRow("Mono (PubChem):", self.l_pcmono)
        ig.addRow("Massa média:", self.l_avg)
        body.addWidget(info_box, stretch=1)
        lay.addLayout(body)

        bb = QDialogButtonBox()
        self.use_btn = bb.addButton("Usar esta fórmula",
                                    QDialogButtonBox.ButtonRole.AcceptRole)
        self.use_btn.setObjectName("accent")
        self.use_btn.setEnabled(False)
        bb.addButton(QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self._accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        i18n.translate_tree(self)

    def _search(self):
        q = self.query.text().strip()
        if not q:
            return
        kind = ("name", "cid", "formula")[self.kind.currentIndex()]
        self.search_btn.setEnabled(False)
        self.use_btn.setEnabled(False)
        self.status.setText(_("Consultando o PubChem…"))
        self.image.clear()
        self._worker = PubChemWorker(q, kind=kind)
        self._worker.found.connect(self._on_found)
        self._worker.failed.connect(self._on_failed)
        self._worker.png_ready.connect(self._on_png)
        self._worker.start()

    def _on_found(self, comp):
        self.compound = comp
        self.l_name.setText(comp.iupac_name or "—")
        self.l_cid.setText(str(comp.cid))
        self.l_formula.setText(comp.clean_formula)
        self.l_mono.setText(f"{comp.free_mono_mass:.6f} Da")
        self.l_pcmono.setText(
            f"{comp.pubchem_monoisotopic:.6f} Da" if comp.pubchem_monoisotopic
            else "—")
        self.l_avg.setText(f"{comp.free_avg_mass:.4f} Da")
        self.status.setText(_("✓ Encontrado. Revise e clique em "
                            "'Usar esta fórmula'."))
        self.status.setStyleSheet("color:#2ec27e;")
        self.use_btn.setEnabled(True)
        self.search_btn.setEnabled(True)

    def _on_failed(self, msg):
        self.status.setText("✗ " + msg)
        self.status.setStyleSheet("color:#e06c6c;")
        self.search_btn.setEnabled(True)

    def _on_png(self, data):
        pix = QPixmap()
        if pix.loadFromData(data):
            self.image.setPixmap(pix.scaled(
                176, 176, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))

    def _accept(self):
        if self.compound:
            self.result_formula = self.compound.clean_formula
            self.result_name = self.compound.iupac_name or self.compound.name
            self.accept()


# ===========================================================================
# ABA 1 — Massa Molecular
# ===========================================================================
class MassTab(QWidget):
    def __init__(self, app_state, parent=None):
        super().__init__(parent)
        self.state = app_state
        self.result = None
        self._build()
        self._timer = QTimer(self); self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.recalculate)

    def _build(self):
        root = QHBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter)

        # ---------- painel esquerdo: entrada ----------
        left = QWidget(); lv = QVBoxLayout(left)

        seq_box = QGroupBox("Sequência de aminoácidos")
        sb = QVBoxLayout(seq_box)
        self.seq_input = QPlainTextEdit()
        self.seq_input.setPlaceholderText(
            "ex.: ACDEFGHIKLMNPQRSTVWY\n"
            "Não-naturais entre colchetes: A[Orn]G[Nle]K\n"
            "Modificações inline: PEPT(Phosphorylation)IDE")
        self.seq_input.setFixedHeight(90)
        self.seq_input.textChanged.connect(self._schedule)
        sb.addWidget(self.seq_input)
        self.valid_label = QLabel("—")
        sb.addWidget(self.valid_label)
        self.define_btn = QPushButton("Definir resíduo(s) desconhecido(s)…")
        self.define_btn.setObjectName("accent")
        self.define_btn.clicked.connect(self._define_unknown_residues)
        self.define_btn.hide()
        sb.addWidget(self.define_btn)
        row = QHBoxLayout()
        fasta_btn = QPushButton("Importar FASTA…")
        fasta_btn.clicked.connect(self._import_fasta)
        row.addWidget(fasta_btn)
        row.addStretch()
        sb.addLayout(row)
        lv.addWidget(seq_box)

        # modificações terminais
        mod_box = QGroupBox("Modificações")
        mg = QFormLayout(mod_box)
        self.nterm_combo = QComboBox(); self.cterm_combo = QComboBox()
        self.nterm_combo.currentTextChanged.connect(self._schedule)
        self.cterm_combo.currentTextChanged.connect(self._schedule)
        mg.addRow("N-terminal:", self.nterm_combo)
        mg.addRow("C-terminal:", self.cterm_combo)
        self.residue_mod_list = QListWidget()
        self.residue_mod_list.setMaximumHeight(90)
        mg.addRow("Mod. por resíduo:", self.residue_mod_list)
        addmod_row = QHBoxLayout()
        add_res_mod = QPushButton("Adicionar mod. a resíduo…")
        add_res_mod.clicked.connect(self._add_residue_mod)
        clr_res_mod = QPushButton("Limpar")
        clr_res_mod.clicked.connect(self._clear_residue_mods)
        addmod_row.addWidget(add_res_mod); addmod_row.addWidget(clr_res_mod)
        mg.addRow(addmod_row)
        lv.addWidget(mod_box)

        # aminoácidos personalizados
        custom_box = QGroupBox("Custom Amino Acids")
        cv = QVBoxLayout(custom_box)
        self.custom_table = make_table(["Código", "Abrev.", "Nome",
                                        "Fórmula", "Mono (Da)", "Tipo"])
        self.custom_table.setMaximumHeight(150)
        cv.addWidget(self.custom_table)
        crow = QHBoxLayout()
        add_aa = QPushButton("Novo…"); add_aa.clicked.connect(self._add_custom_aa)
        del_aa = QPushButton("Remover"); del_aa.clicked.connect(self._del_custom_aa)
        crow.addWidget(add_aa); crow.addWidget(del_aa); crow.addStretch()
        cv.addLayout(crow)
        lv.addWidget(custom_box)

        # peptídeos salvos (biblioteca do usuário)
        saved_box = QGroupBox("Peptídeos salvos")
        sb2 = QVBoxLayout(saved_box)
        self.saved_combo = QComboBox()
        sb2.addWidget(self.saved_combo)
        prow = QHBoxLayout()
        save_pep = QPushButton("Salvar atual…")
        save_pep.clicked.connect(self._save_peptide)
        load_pep = QPushButton("Carregar")
        load_pep.clicked.connect(self._load_peptide)
        del_pep = QPushButton("Remover")
        del_pep.clicked.connect(self._del_peptide)
        prow.addWidget(save_pep); prow.addWidget(load_pep); prow.addWidget(del_pep)
        sb2.addLayout(prow)
        lv.addWidget(saved_box)

        lv.addStretch()
        splitter.addWidget(left)

        # ---------- painel direito: resultados ----------
        right = QWidget(); rv = QVBoxLayout(right)

        res_box = QGroupBox("Resultado de massa")
        rb = QVBoxLayout(res_box)
        self.mono_label = QLabel("Massa monoisotópica: —")
        self.mono_label.setObjectName("result")
        self.avg_label = QLabel("Massa média: —")
        self.avg_label.setObjectName("resultavg")
        self.formula_label = QLabel("Fórmula: —")
        self.formula_label.setObjectName("formula")
        self.warn_label = QLabel("")
        self.warn_label.setWordWrap(True)
        rb.addWidget(self.mono_label)
        rb.addWidget(self.avg_label)
        rb.addWidget(self.formula_label)
        rb.addWidget(self.warn_label)
        rv.addWidget(res_box)

        # tabela de estados de carga
        cs_box = QGroupBox("Estados de carga (m/z)")
        cb = QVBoxLayout(cs_box)
        cfg = QHBoxLayout()
        cfg.addWidget(QLabel("z de"))
        self.zmin = QSpinBox(); self.zmin.setRange(1, 200); self.zmin.setValue(1)
        cfg.addWidget(self.zmin)
        cfg.addWidget(QLabel("até"))
        self.zmax = QSpinBox(); self.zmax.setRange(1, 200); self.zmax.setValue(10)
        cfg.addWidget(self.zmax)
        self.zextra = QLineEdit("15, 20")
        self.zextra.setPlaceholderText("extras: 15, 20")
        cfg.addWidget(QLabel("extras:")); cfg.addWidget(self.zextra)
        upd = QPushButton("Atualizar"); upd.clicked.connect(self._update_charge_table)
        cfg.addWidget(upd)
        cb.addLayout(cfg)
        self.charge_table = make_table(["z", "m/z"])
        self.charge_table.customContextMenuRequested.connect(
            lambda p: copy_table_selection(self.charge_table))
        cb.addWidget(self.charge_table)
        rv.addWidget(cs_box)

        # distribuição isotópica
        iso_box = QGroupBox("Distribuição isotópica teórica")
        ib = QVBoxLayout(iso_box)
        izr = QHBoxLayout()
        izr.addWidget(QLabel("Carga do envelope:"))
        self.iso_charge = QSpinBox()
        self.iso_charge.setRange(0, 100)
        self.iso_charge.setValue(0)
        self.iso_charge.setPrefix("+")
        self.iso_charge.setSpecialValueText(_("M (neutro)"))
        self.iso_charge.valueChanged.connect(self._plot_isotopes)
        izr.addWidget(self.iso_charge)
        self.iso_labels = QCheckBox("m/z sobre os picos")
        self.iso_labels.setChecked(True)
        self.iso_labels.stateChanged.connect(self._plot_isotopes)
        izr.addWidget(self.iso_labels)
        izr.addStretch()
        ib.addLayout(izr)
        self.fig = Figure(figsize=(5, 2.2), tight_layout=True)
        self.canvas = FigureCanvas(self.fig)
        ib.addWidget(self.canvas)
        ib.addWidget(NavigationToolbar(self.canvas, self))
        self.iso_hover = _HoverTip(self.canvas)
        rv.addWidget(iso_box)
        splitter.addWidget(right)
        splitter.setSizes([460, 620])

        self.refresh_modifications()
        self.refresh_custom_table()
        self.refresh_saved_peptides()

    # -------------------- helpers de estado --------------------
    def _schedule(self):
        self._timer.start(250)

    def refresh_modifications(self):
        lib = self.state.mod_library
        for combo, pos in ((self.nterm_combo, "N-term"),
                           (self.cterm_combo, "C-term")):
            cur = combo.currentText()
            combo.blockSignals(True); combo.clear()
            combo.addItem(_("(nenhuma)"))
            for m in lib.for_position(pos):
                combo.addItem(m.name)
            i = combo.findText(cur)
            combo.setCurrentIndex(i if i >= 0 else 0)
            combo.blockSignals(False)

    def refresh_custom_table(self):
        mgr = self.state.custom_manager
        self.custom_table.setSortingEnabled(False)
        self.custom_table.setRowCount(0)
        for r in mgr.all():
            row = self.custom_table.rowCount()
            self.custom_table.insertRow(row)
            self.custom_table.setItem(row, 0, QTableWidgetItem(r.code))
            self.custom_table.setItem(row, 1, QTableWidgetItem(r.three))
            self.custom_table.setItem(row, 2, QTableWidgetItem(r.name))
            self.custom_table.setItem(row, 3, QTableWidgetItem(r.residue_formula))
            self.custom_table.setItem(row, 4, NumericItem(
                r.mono_mass, f"{r.mono_mass:.6f}"))
            self.custom_table.setItem(row, 5, QTableWidgetItem(
                "embutido" if r.builtin else "custom"))
        self.custom_table.setSortingEnabled(True)

    # -------------------- ações --------------------
    def _residue_mods_dict(self):
        d = {}
        for i in range(self.residue_mod_list.count()):
            it = self.residue_mod_list.item(i)
            data = it.data(Qt.ItemDataRole.UserRole)
            if data:
                d[data[0]] = data[1]
        return d

    def recalculate(self):
        seq = self.seq_input.toPlainText()
        ok, msg = self.state.calc.validate_sequence(seq)
        self.valid_label.setText(("✓ " if ok else "✗ ") + msg)
        self.valid_label.setStyleSheet(
            "color:#2ec27e;" if ok else "color:#e06c6c;")
        # oferece cadastro assistido dos resíduos não-convencionais
        unknown = [] if ok else self.state.calc.unknown_codes(seq)
        if unknown:
            self.define_btn.setText(
                _("Definir resíduo(s) desconhecido(s): {x} …").format(
                    x=", ".join(unknown)))
            self.define_btn.show()
        else:
            self.define_btn.hide()
        if not ok:
            return
        nterm = None if self.nterm_combo.currentIndex() == 0 \
            else self.nterm_combo.currentText()
        cterm = None if self.cterm_combo.currentIndex() == 0 \
            else self.cterm_combo.currentText()
        try:
            self.result = self.state.calc.parse(
                seq, n_term_mod=nterm, c_term_mod=cterm,
                residue_mods=self._residue_mods_dict())
        except (SequenceError, FormulaError) as e:
            self.valid_label.setText("✗ " + str(e))
            self.valid_label.setStyleSheet("color:#e06c6c;")
            return
        r = self.result
        self.mono_label.setText(
            _("Massa monoisotópica: {m} Da").format(m=f"{r.mono_mass:.6f}"))
        self.avg_label.setText(
            _("Massa média: {m} Da").format(m=f"{r.avg_mass:.6f}"))
        self.formula_label.setText(_("Fórmula: {f}").format(f=r.formula))
        self.warn_label.setText(
            ("⚠ " + " | ".join(r.warnings)) if r.warnings else "")
        self.warn_label.setStyleSheet("color:#e0a96c;")
        self._update_charge_table()
        self._plot_isotopes()
        self.state.last_mass_result = r
        if self.state.on_mass_updated:
            self.state.on_mass_updated(r)

    def _update_charge_table(self):
        if not self.result:
            return
        charges = list(range(self.zmin.value(), self.zmax.value() + 1))
        for tok in self.zextra.text().split(","):
            tok = tok.strip()
            if tok.isdigit() and int(tok) not in charges:
                charges.append(int(tok))
        charges = sorted(set(charges))
        self.charge_table.setSortingEnabled(False)
        self.charge_table.setRowCount(0)
        for z, mz in self.state.calc.charge_table(self.result.mono_mass, charges):
            row = self.charge_table.rowCount()
            self.charge_table.insertRow(row)
            self.charge_table.setItem(row, 0, NumericItem(z, f"+{z}"))
            self.charge_table.setItem(row, 1, NumericItem(mz, f"{mz:.6f}"))
        self.charge_table.setSortingEnabled(True)

    def _plot_isotopes(self):
        if not self.result:
            return
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        self.iso_hover.rebind(ax)
        z = self.iso_charge.value()
        dist = self.state.calc.isotopic_distribution(
            self.result.composition, max_peaks=12)
        if dist:
            mz = lambda m: self.state.calc.mz(m, z)
            xs = [mz(m) for m, _ in dist]
            ints = [i for _, i in dist]
            ax.stem(xs, ints, basefmt=" ")
            if self.iso_labels.isChecked():
                for x, i in zip(xs, ints):
                    ax.text(x, i + 2, f"{x:.4f}", rotation=90, fontsize=6,
                            ha="center", va="bottom", color="#333333")
                ax.set_ylim(0, 150)
            ax.set_xlabel("m/z (neutro)" if z == 0 else f"m/z ({z}+)",
                          fontsize=8)
            ax.set_ylabel("Intensidade (%)", fontsize=8)
            ax.tick_params(labelsize=7)
            ztag = "" if z == 0 else f"  ({z}+)"
            self.iso_hover.set_points(
                [(mz(m), i, f"m/z {mz(m):.4f}{ztag}\n{i:.2f} %")
                 for m, i in dist])
        self.canvas.draw()

    def _import_fasta(self):
        path, _flt = QFileDialog.getOpenFileName(
            self, _("Importar FASTA"), "",
            _("FASTA (*.fasta *.fa *.txt);;Todos (*)"))
        if not path:
            return
        with open(path, encoding="utf-8") as f:
            entries = exporters.parse_fasta(f.read())
        if not entries:
            return
        if len(entries) == 1:
            self.seq_input.setPlainText(entries[0][1])
        else:
            items = [f"{h[:50]}  ({len(s)} aa)" for h, s in entries]
            from PyQt6.QtWidgets import QInputDialog
            choice, ok = QInputDialog.getItem(
                self, _("Selecionar sequência"), _("Entradas FASTA:"),
                items, 0, False)
            if ok:
                self.seq_input.setPlainText(entries[items.index(choice)][1])

    def _add_residue_mod(self):
        codes = self.state.calc.residue_codes(self.seq_input.toPlainText())
        if not codes:
            QMessageBox.information(self, _("Aviso"),
                                    _("Insira a sequência primeiro."))
            return
        from PyQt6.QtWidgets import QInputDialog
        positions = [f"{i+1}: {c}" for i, c in enumerate(codes)]
        pos_choice, ok = QInputDialog.getItem(
            self, _("Posição"), _("Resíduo a modificar:"), positions, 0, False)
        if not ok:
            return
        idx = positions.index(pos_choice)
        residue = codes[idx]
        mods = [m.name for m in self.state.mod_library.for_residue(residue)]
        if not mods:
            mods = [m.name for m in self.state.mod_library.all()
                    if m.position == "residue"]
        mod_choice, ok = QInputDialog.getItem(
            self, _("Modificação"),
            _("Modificação para {r}:").format(r=f"{residue}{idx+1}"),
            mods, 0, False)
        if not ok:
            return
        it = QListWidgetItem(f"{residue}{idx+1} → {mod_choice}")
        it.setData(Qt.ItemDataRole.UserRole, (idx, mod_choice))
        self.residue_mod_list.addItem(it)
        self._schedule()

    def _clear_residue_mods(self):
        self.residue_mod_list.clear()
        self._schedule()

    def _define_unknown_residues(self):
        """
        Para cada código de resíduo desconhecido na sequência, abre o diálogo
        de aminoácido personalizado (com busca no PubChem) já travado naquele
        código. O que for cadastrado é salvo na base e fica disponível.
        """
        seq = self.seq_input.toPlainText()
        unknown = self.state.calc.unknown_codes(seq)
        if not unknown:
            return
        added = []
        for code in unknown:
            dlg = CustomResidueDialog(self, initial_code=code, lock_code=True)
            dlg.setWindowTitle(
                _("Definir resíduo '{c}' (via PubChem)").format(c=code))
            if not dlg.exec():
                break  # cancelou: interrompe a fila
            name, three, c, formula = dlg.values()
            try:
                self.state.custom_manager.add(name, three, c, formula)
                added.append(c)
            except ValueError as e:
                QMessageBox.warning(self, _("Erro"), str(e))
                break
        if added:
            self.state.calc.refresh_table()
            self.refresh_custom_table()
            QMessageBox.information(
                self, _("Resíduos cadastrados"),
                _("Salvos na base de dados e disponíveis nas sequências:\n{x}")
                .format(x=", ".join(added)))
            self.recalculate()

    def _add_custom_aa(self):
        dlg = CustomResidueDialog(self)
        if dlg.exec():
            name, three, code, formula = dlg.values()
            try:
                self.state.custom_manager.add(name, three, code, formula)
                self.state.calc.refresh_table()
                self.refresh_custom_table()
                QMessageBox.information(
                    self, _("Sucesso"),
                    _("Aminoácido '{c}' cadastrado e disponível nas "
                      "sequências.").format(c=code))
            except ValueError as e:
                QMessageBox.warning(self, _("Erro"), str(e))

    def _del_custom_aa(self):
        row = self.custom_table.currentRow()
        if row < 0:
            return
        code = self.custom_table.item(row, 0).text()
        r = self.state.custom_manager.get(code)
        if r and r.builtin:
            QMessageBox.information(
                self, _("Aviso"),
                _("'{c}' é um resíduo embutido e não pode ser removido.")
                .format(c=code))
            return
        self.state.custom_manager.delete(code)
        self.state.calc.refresh_table()
        self.refresh_custom_table()

    # -------------------- peptídeos salvos --------------------
    def refresh_saved_peptides(self):
        cur = self.saved_combo.currentText()
        self.saved_combo.blockSignals(True)
        self.saved_combo.clear()
        for row in self.state.db.list_peptides():
            self.saved_combo.addItem(row["name"])
        i = self.saved_combo.findText(cur)
        if i >= 0:
            self.saved_combo.setCurrentIndex(i)
        self.saved_combo.blockSignals(False)

    def _save_peptide(self):
        seq = self.seq_input.toPlainText().strip()
        if not seq:
            QMessageBox.information(self, _("Aviso"),
                                   _("A sequência está vazia — nada a salvar."))
            return
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(
            self, _("Salvar peptídeo"), _("Nome:"),
            text=self.saved_combo.currentText())
        name = name.strip()
        if not ok or not name:
            return
        if self.state.db.get_peptide(name):
            r = QMessageBox.question(
                self, _("Sobrescrever"),
                _("Já existe '{n}'. Substituir?").format(n=name))
            if r != QMessageBox.StandardButton.Yes:
                return
        import json
        nterm = "" if self.nterm_combo.currentIndex() == 0 \
            else self.nterm_combo.currentText()
        cterm = "" if self.cterm_combo.currentIndex() == 0 \
            else self.cterm_combo.currentText()
        rmods = json.dumps([[i, m] for i, m in self._residue_mods_dict().items()])
        self.state.db.save_peptide(name, seq, nterm, cterm, rmods)
        self.refresh_saved_peptides()
        i = self.saved_combo.findText(name)
        if i >= 0:
            self.saved_combo.setCurrentIndex(i)
        QMessageBox.information(self, _("Salvo"),
                               _("Peptídeo '{n}' salvo na base.").format(n=name))

    def _load_peptide(self):
        name = self.saved_combo.currentText()
        if not name:
            return
        row = self.state.db.get_peptide(name)
        if not row:
            return
        import json

        def set_combo(combo, val):
            if not val:
                combo.setCurrentIndex(0)   # "(nenhuma)" / "(none)"
                return
            i = combo.findText(val)
            combo.setCurrentIndex(i if i >= 0 else 0)

        self.seq_input.setPlainText(row["sequence"])
        set_combo(self.nterm_combo, row["n_term_mod"])
        set_combo(self.cterm_combo, row["c_term_mod"])
        self.residue_mod_list.clear()
        codes = self.state.calc.residue_codes(row["sequence"])
        try:
            rmods = json.loads(row["residue_mods"] or "[]")
        except (ValueError, TypeError):
            rmods = []
        for idx, mod in rmods:
            res = codes[idx] if 0 <= idx < len(codes) else "?"
            it = QListWidgetItem(f"{res}{idx + 1} → {mod}")
            it.setData(Qt.ItemDataRole.UserRole, (idx, mod))
            self.residue_mod_list.addItem(it)
        self.recalculate()

    def _del_peptide(self):
        name = self.saved_combo.currentText()
        if not name:
            return
        r = QMessageBox.question(self, _("Remover"),
                                 _("Remover '{n}' da base?").format(n=name))
        if r != QMessageBox.StandardButton.Yes:
            return
        self.state.db.delete_peptide(name)
        self.refresh_saved_peptides()


# ===========================================================================
# ABA 2 — Fragmentação MS/MS
# ===========================================================================
class FragmentTab(QWidget):
    def __init__(self, app_state, parent=None):
        super().__init__(parent)
        self.state = app_state
        self.fragments = []
        self._build()

    def _build(self):
        root = QHBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter)

        # ---------- esquerda: opções ----------
        left = QWidget(); lv = QVBoxLayout(left)

        info = QGroupBox("Peptídeo (da Aba 1)")
        iv = QVBoxLayout(info)
        self.pep_label = QLabel("Nenhum peptídeo calculado.")
        self.pep_label.setWordWrap(True)
        iv.addWidget(self.pep_label)
        lv.addWidget(info)

        ions_box = QGroupBox("Séries de íons")
        ig = QGridLayout(ions_box)
        self.ion_checks = {}
        ions = [("a", 0, 0), ("b", 0, 1), ("c", 0, 2),
                ("x", 1, 0), ("y", 1, 1), ("z", 1, 2), ("z+1 (z•)", 2, 0)]
        for label, r, c in ions:
            key = label.split()[0]
            cb = QCheckBox(f"{label} ions")
            if key in ("b", "y"):
                cb.setChecked(True)
            cb.stateChanged.connect(self.recalculate)
            self.ion_checks[key] = cb
            ig.addWidget(cb, r, c)
        lv.addWidget(ions_box)

        nl_box = QGroupBox("Perdas neutras")
        nlv = QVBoxLayout(nl_box)
        self.no_loss = QCheckBox("Sem perdas"); self.no_loss.setChecked(True)
        self.no_loss.stateChanged.connect(self.recalculate)
        nlv.addWidget(self.no_loss)
        self.loss_checks = {}
        for nl in ("-NH3", "-H2O", "-CO"):
            cb = QCheckBox(nl); cb.stateChanged.connect(self.recalculate)
            self.loss_checks[nl] = cb
            nlv.addWidget(cb)
        lv.addWidget(nl_box)

        cz_box = QGroupBox("Estados de carga dos fragmentos")
        czv = QHBoxLayout(cz_box)
        self.frag_charges = {}
        for z in range(1, 6):
            cb = QCheckBox(f"+{z}")
            if z == 1:
                cb.setChecked(True)
            cb.stateChanged.connect(self.recalculate)
            self.frag_charges[z] = cb
            czv.addWidget(cb)
        lv.addWidget(cz_box)

        # matching experimental
        match_box = QGroupBox("Matching com lista experimental de m/z")
        mv = QVBoxLayout(match_box)
        self.exp_input = QPlainTextEdit()
        self.exp_input.setPlaceholderText("Cole valores de m/z (um por linha "
                                          "ou separados por vírgula)")
        self.exp_input.setFixedHeight(70)
        mv.addWidget(self.exp_input)
        trow = QHBoxLayout()
        trow.addWidget(QLabel("Tolerância:"))
        self.tol = QDoubleSpinBox(); self.tol.setDecimals(4)
        self.tol.setRange(0.0001, 1000); self.tol.setValue(0.02)
        trow.addWidget(self.tol)
        self.ppm_check = QCheckBox("ppm")
        trow.addWidget(self.ppm_check)
        match_btn = QPushButton("Casar")
        match_btn.clicked.connect(self._do_match)
        trow.addWidget(match_btn)
        mv.addLayout(trow)
        lv.addWidget(match_box)
        lv.addStretch()
        splitter.addWidget(left)

        # ---------- direita: tabela + espectro ----------
        right = QWidget(); rv = QVBoxLayout(right)
        tools = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Busca rápida de fragmentos (ex.: b5, y, 2+)…")
        self.search.textChanged.connect(self._filter)
        tools.addWidget(self.search)
        copy_btn = QPushButton("Copiar seleção")
        copy_btn.clicked.connect(lambda: copy_table_selection(self.frag_table))
        tools.addWidget(copy_btn)
        for label, fmt in (("CSV", "csv"), ("Excel", "xlsx"),
                           ("PDF", "pdf"), ("TXT", "txt"),
                           ("Skyline", "skyline")):
            b = QPushButton(label)
            b.clicked.connect(lambda _, f=fmt: self._export(f))
            tools.addWidget(b)
        rv.addLayout(tools)

        self.frag_table = make_table(
            ["Íon", "z", "m/z", "Perda", "Massa neutra", "Sequência"])
        self.frag_table.customContextMenuRequested.connect(
            lambda p: copy_table_selection(self.frag_table))
        rv.addWidget(self.frag_table, stretch=3)

        spec_box = QGroupBox("Espectro teórico")
        sv = QVBoxLayout(spec_box)
        srow = QHBoxLayout()
        self.spec_labels = QCheckBox("m/z sobre os picos")
        self.spec_labels.setChecked(True)
        self.spec_labels.stateChanged.connect(
            lambda: self._plot_spectrum(self.fragments))
        srow.addWidget(self.spec_labels)
        srow.addStretch()
        sv.addLayout(srow)
        self.fig = Figure(figsize=(6, 2.6), tight_layout=True)
        self.canvas = FigureCanvas(self.fig)
        sv.addWidget(self.canvas)
        sv.addWidget(NavigationToolbar(self.canvas, self))
        self.spec_hover = _HoverTip(self.canvas)
        rv.addWidget(spec_box, stretch=2)
        splitter.addWidget(right)
        splitter.setSizes([380, 720])

    # -------------------- lógica --------------------
    def on_mass_updated(self, result):
        seq = result.sequence
        mods = []
        if result.n_term_mod:
            mods.append(f"N-term: {result.n_term_mod.name}")
        if result.c_term_mod:
            mods.append(f"C-term: {result.c_term_mod.name}")
        extra = ("  [" + "; ".join(mods) + "]") if mods else ""
        self.pep_label.setText(
            _("<b>{seq}</b>{extra}<br>Massa monoisotópica: {m} Da").format(
                seq=seq, extra=extra, m=f"{result.mono_mass:.6f}"))
        self.recalculate()

    def _selected_ions(self):
        return [k for k, cb in self.ion_checks.items() if cb.isChecked()]

    def _selected_charges(self):
        return [z for z, cb in self.frag_charges.items() if cb.isChecked()]

    def _selected_losses(self):
        return [nl for nl, cb in self.loss_checks.items() if cb.isChecked()]

    def recalculate(self):
        result = self.state.last_mass_result
        if not result:
            return
        if getattr(result, "n_chains", 1) > 1:
            # fragmentação a/b/c/x/y/z pressupõe uma única cadeia linear
            self.fragments = []
            self.state.last_fragments = []
            self._populate([])
            self._plot_spectrum([])
            return
        ions = self._selected_ions()
        charges = self._selected_charges() or [1]
        nterm_delta = result.n_term_mod.mono_delta if result.n_term_mod else 0.0
        cterm_delta = result.c_term_mod.mono_delta if result.c_term_mod else 0.0
        self.fragments = generate_fragments(
            result, ion_types=ions, charges=charges,
            neutral_losses=self._selected_losses(),
            include_no_loss=self.no_loss.isChecked(),
            n_term_delta=nterm_delta, c_term_delta=cterm_delta)
        self.state.last_fragments = self.fragments
        self._populate(self.fragments)
        self._plot_spectrum(self.fragments)

    def _populate(self, frags, highlight=None):
        highlight = highlight or set()
        self.frag_table.setSortingEnabled(False)
        self.frag_table.setRowCount(0)
        for f in frags:
            row = self.frag_table.rowCount()
            self.frag_table.insertRow(row)
            self.frag_table.setItem(row, 0, QTableWidgetItem(
                f"{f.ion_type}{f.number}"))
            self.frag_table.setItem(row, 1, NumericItem(f.charge, f"+{f.charge}"))
            self.frag_table.setItem(row, 2, NumericItem(f.mz, f"{f.mz:.6f}"))
            self.frag_table.setItem(row, 3, QTableWidgetItem(f.neutral_loss or "—"))
            self.frag_table.setItem(row, 4, NumericItem(
                f.neutral_mass, f"{f.neutral_mass:.6f}"))
            self.frag_table.setItem(row, 5, QTableWidgetItem(f.sequence))
            if id(f) in highlight:
                for c in range(6):
                    self.frag_table.item(row, c).setBackground(
                        Qt.GlobalColor.darkGreen)
        self.frag_table.setSortingEnabled(True)

    def _plot_spectrum(self, frags):
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        self.spec_hover.rebind(ax)
        colors = {"a": "#888", "b": "#3d6fd6", "c": "#28a", "x": "#a82",
                  "y": "#d65", "z": "#7a5", "z+1": "#5a7"}
        show = self.spec_labels.isChecked()
        points = []
        for f in frags:
            if f.neutral_loss:
                continue
            ax.vlines(f.mz, 0, 100, color=colors.get(f.ion_type, "#666"),
                      linewidth=0.9)
            if show:
                ax.text(f.mz, 102, f"{f.mz:.4f}", rotation=90, fontsize=6,
                        ha="center", va="bottom", color="#333333")
            points.append((f.mz, 100,
                           f"{f.label}  {f.charge}+\nm/z {f.mz:.4f}\n{f.sequence}"))
        ax.set_ylim(0, 175 if show else 110)
        ax.set_xlabel("m/z", fontsize=8)
        ax.set_ylabel("Intensidade rel.", fontsize=8)
        ax.tick_params(labelsize=7)
        self.spec_hover.set_points(points)
        self.canvas.draw()

    def _filter(self, text):
        text = text.strip().lower()
        for row in range(self.frag_table.rowCount()):
            ion = self.frag_table.item(row, 0).text().lower()
            z = self.frag_table.item(row, 1).text().lower()
            loss = self.frag_table.item(row, 3).text().lower()
            blob = f"{ion} {z} {loss}"
            self.frag_table.setRowHidden(row, bool(text) and text not in blob)

    def _do_match(self):
        raw = self.exp_input.toPlainText().replace(",", "\n")
        exp = []
        for tok in raw.split():
            try:
                exp.append(float(tok))
            except ValueError:
                pass
        if not exp or not self.fragments:
            QMessageBox.information(self, _("Aviso"),
                                    _("Forneça m/z experimentais e gere "
                                      "fragmentos."))
            return
        matches = match_experimental(
            self.fragments, exp, tolerance=self.tol.value(),
            ppm=self.ppm_check.isChecked())
        hl = {id(f) for _, f, _ in matches}
        self._populate(self.fragments, highlight=hl)
        unit = "ppm" if self.ppm_check.isChecked() else "Da"
        lines = [_("{e} → {lbl} ({z}+)  erro {err} {unit}").format(
                     e=f"{e:.4f}", lbl=f.label, z=f.charge,
                     err=f"{err:+.4f}", unit=unit)
                 for e, f, err in matches]
        QMessageBox.information(
            self, _("Matching"),
            _("{a}/{b} casamentos:").format(a=len(matches), b=len(exp)) +
            "\n\n" + ("\n".join(lines) if lines else _("nenhum")))

    def _export(self, fmt):
        if not self.fragments:
            QMessageBox.information(self, _("Aviso"),
                                    _("Nenhum fragmento para exportar."))
            return
        result = self.state.last_mass_result
        headers = ["Ion", "z", "m/z", "Perda", "Massa neutra", "Sequencia"]
        rows = [[f"{f.ion_type}{f.number}", f.charge, f"{f.mz:.6f}",
                 f.neutral_loss or "", f"{f.neutral_mass:.6f}", f.sequence]
                for f in self.fragments]
        filt = {"csv": "CSV (*.csv)", "xlsx": "Excel (*.xlsx)",
                "pdf": "PDF (*.pdf)", "txt": "Texto (*.txt)",
                "skyline": "Skyline CSV (*.csv)"}[fmt]
        ext = "csv" if fmt == "skyline" else fmt
        path, _flt = QFileDialog.getSaveFileName(
            self, _("Exportar"), f"fragmentos.{ext}", filt)
        if not path:
            return
        try:
            if fmt == "csv":
                exporters.to_csv(path, headers, rows)
            elif fmt == "txt":
                exporters.to_txt(path, headers, rows,
                                 title=_("Fragmentos — {s}").format(
                                     s=result.sequence))
            elif fmt == "xlsx":
                exporters.to_xlsx(path, headers, rows, title=_("Fragmentos"))
            elif fmt == "pdf":
                exporters.to_pdf(path, headers, rows,
                                 title=_("Fragmentos MS/MS"),
                                 subtitle=_("Peptídeo: {s}  M={m} Da").format(
                                     s=result.sequence,
                                     m=f"{result.mono_mass:.6f}"))
            elif fmt == "skyline":
                prec_mz = self.state.calc.mz(result.mono_mass, 2)
                exporters.to_skyline_transition_list(
                    path, result.sequence, self.fragments,
                    precursor_charge=2, precursor_mz=prec_mz)
            QMessageBox.information(self, _("Exportado"),
                                    _("Arquivo salvo:\n{p}").format(p=path))
        except Exception as e:
            QMessageBox.critical(self, _("Erro"), str(e))


# ===========================================================================
# ABA 3 — Dados experimentais (mzML / mzXML / .raw)
# ===========================================================================
class ExperimentalTab(QWidget):
    def __init__(self, app_state, parent=None):
        super().__init__(parent)
        self.state = app_state
        self.run = None
        self.current_scan = None
        self.exp_mz = []        # dados brutos do scan (perfil ou centroide)
        self.exp_int = []
        self.peak_mz = []       # lista de picos usada no matching
        self.peak_int = []
        self.matches = []
        self.match_fragments = []
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        top = QHBoxLayout()
        open_btn = QPushButton("Abrir arquivo…")
        open_btn.setObjectName("accent")
        open_btn.clicked.connect(self._open_file)
        top.addWidget(open_btn)
        self.raw_profile = QCheckBox("abrir .raw em perfil")
        self.raw_profile.setToolTip(
            "Converte o .raw sem peak picking (dados em perfil). "
            "Arquivos ficam bem maiores.")
        top.addWidget(self.raw_profile)
        self.file_label = QLabel("Nenhum arquivo aberto.")
        self.file_label.setWordWrap(True)
        top.addWidget(self.file_label, stretch=1)
        top.addWidget(QLabel("Nível MS:"))
        self.ms_combo = QComboBox()
        self.ms_combo.currentTextChanged.connect(self._plot_chromatogram)
        top.addWidget(self.ms_combo)
        root.addLayout(top)

        # filtro de scan (estilo Xcalibur): restringe cromatograma/XIC/scan
        frow = QHBoxLayout()
        frow.addWidget(QLabel("Filtro de scan:"))
        self.filter_combo = QComboBox()
        self.filter_combo.setMinimumWidth(420)
        self.filter_combo.currentIndexChanged.connect(self._plot_chromatogram)
        frow.addWidget(self.filter_combo, stretch=1)
        self.group_filters = QCheckBox("agrupar (ignorar m/z do precursor)")
        self.group_filters.setChecked(True)
        self.group_filters.stateChanged.connect(self._refresh_filters)
        frow.addWidget(self.group_filters)
        root.addLayout(frow)

        splitter = QSplitter(Qt.Orientation.Vertical)
        root.addWidget(splitter, stretch=1)

        chrom_box = QGroupBox("Cromatograma — clique para escolher o scan")
        cv = QVBoxLayout(chrom_box)
        xrow = QHBoxLayout()
        self.tic_btn = QPushButton("TIC")
        self.tic_btn.clicked.connect(self._plot_chromatogram)
        xrow.addWidget(self.tic_btn)
        xrow.addWidget(QLabel("XIC m/z:"))
        self.xic_mz = QLineEdit()
        self.xic_mz.setPlaceholderText("ex.: 800.3672")
        self.xic_mz.setFixedWidth(110)
        self.xic_mz.returnPressed.connect(self._plot_xic)
        xrow.addWidget(self.xic_mz)
        xrow.addWidget(QLabel("± Da:"))
        self.xic_tol = QDoubleSpinBox()
        self.xic_tol.setDecimals(4)
        self.xic_tol.setRange(0.0001, 10)
        self.xic_tol.setValue(0.02)
        xrow.addWidget(self.xic_tol)
        xic_btn = QPushButton("Mostrar XIC")
        xic_btn.clicked.connect(self._plot_xic)
        xrow.addWidget(xic_btn)
        xrow.addStretch()
        cv.addLayout(xrow)
        self.chrom_fig = Figure(figsize=(6, 2.0), tight_layout=True)
        self.chrom_canvas = FigureCanvas(self.chrom_fig)
        self.chrom_canvas.mpl_connect("button_press_event", self._on_chrom_click)
        cv.addWidget(self.chrom_canvas)
        cv.addWidget(NavigationToolbar(self.chrom_canvas, self))
        splitter.addWidget(chrom_box)

        lower = QWidget()
        lv = QVBoxLayout(lower)
        mrow = QHBoxLayout()
        self.scan_label = QLabel("Scan: —")
        mrow.addWidget(self.scan_label, stretch=1)
        mrow.addWidget(QLabel("Tol.:"))
        self.tol = QDoubleSpinBox()
        self.tol.setDecimals(4)
        self.tol.setRange(0.0001, 1000)
        self.tol.setValue(10.0)
        mrow.addWidget(self.tol)
        self.ppm = QCheckBox("ppm")
        self.ppm.setChecked(True)
        self.ppm.stateChanged.connect(self._on_match_opts)
        mrow.addWidget(self.ppm)
        match_btn = QPushButton("Casar com fragmentos")
        match_btn.setObjectName("accent")
        match_btn.clicked.connect(self._do_match)
        mrow.addWidget(match_btn)
        lv.addLayout(mrow)

        # seleção do que aparece na anotação: séries, perdas neutras e cargas
        srow = QHBoxLayout()
        srow.addWidget(QLabel("Séries:"))
        self.ser_checks = {}
        for ion in ("a", "b", "c", "x", "y", "z"):
            cb = QCheckBox(ion)
            cb.setChecked(ion in ("b", "y"))
            cb.stateChanged.connect(self._on_match_opts)
            self.ser_checks[ion] = cb
            srow.addWidget(cb)
        srow.addSpacing(14)
        self.use_losses = QCheckBox("perdas neutras")
        self.use_losses.stateChanged.connect(self._on_match_opts)
        srow.addWidget(self.use_losses)
        srow.addSpacing(14)
        srow.addWidget(QLabel("Cargas:"))
        self.z_checks = {}
        for z in (1, 2, 3):
            cb = QCheckBox(f"+{z}")
            cb.setChecked(z in (1, 2))
            cb.stateChanged.connect(self._on_match_opts)
            self.z_checks[z] = cb
            srow.addWidget(cb)
        srow.addSpacing(14)
        self.profile_view = QCheckBox("ver em perfil")
        self.profile_view.setToolTip(
            "Desenha o espectro como linha contínua (perfil) em vez de picos "
            "(centroide). Marcado automaticamente quando o scan é de perfil.")
        self.profile_view.stateChanged.connect(self._plot_spectrum)
        srow.addWidget(self.profile_view)
        srow.addStretch()
        lv.addLayout(srow)

        # critérios de identificação (estilo WADA): carga, RT, íons diagnósticos
        crow = QHBoxLayout()
        crow.addWidget(QLabel("Carga precursor:"))
        self.prec_charge = QSpinBox()
        self.prec_charge.setRange(1, 20); self.prec_charge.setValue(2)
        crow.addWidget(self.prec_charge)
        crow.addSpacing(14)
        crow.addWidget(QLabel("RT esperado (min):"))
        self.rt_exp = QDoubleSpinBox()
        self.rt_exp.setDecimals(2); self.rt_exp.setRange(0, 10000)
        self.rt_exp.setSpecialValueText("—")
        crow.addWidget(self.rt_exp)
        crow.addWidget(QLabel("± janela:"))
        self.rt_win = QDoubleSpinBox()
        self.rt_win.setDecimals(2); self.rt_win.setRange(0.01, 100)
        self.rt_win.setValue(0.20)
        crow.addWidget(self.rt_win)
        crow.addStretch()
        lv.addLayout(crow)

        self.crit_label = QLabel("—")
        self.crit_label.setWordWrap(True)
        lv.addWidget(self.crit_label)

        self.spec_fig = Figure(figsize=(6, 2.4), tight_layout=True)
        self.spec_canvas = FigureCanvas(self.spec_fig)
        lv.addWidget(self.spec_canvas)
        lv.addWidget(NavigationToolbar(self.spec_canvas, self))

        self.score_label = QLabel("—")
        self.score_label.setObjectName("result")
        self.score_label.setWordWrap(True)
        lv.addWidget(self.score_label)

        self.match_table = make_table(
            ["Exp m/z", "Íon", "z", "Teór m/z", "Erro", "Abund.%", "Subseq"])
        self.match_table.customContextMenuRequested.connect(
            lambda p: copy_table_selection(self.match_table))
        self.match_table.cellDoubleClicked.connect(self._xic_from_row)
        self.match_table.setMaximumHeight(170)
        lv.addWidget(self.match_table)
        splitter.addWidget(lower)
        splitter.setSizes([220, 470])

    # ---------------- ações ----------------
    def _open_file(self):
        path, _flt = QFileDialog.getOpenFileName(
            self, _("Abrir dados de MS"), "",
            _("Dados MS (*.mzML *.mzXML *.raw);;Todos (*)"))
        if not path:
            return
        try:
            import spectra_io
        except Exception as e:
            QMessageBox.critical(
                self, _("Dependência ausente"),
                _("A leitura de espectros requer pyteomics/psims/lxml.\n\n{e}")
                .format(e=e))
            return
        try:
            self.run = spectra_io.open_run(
                path, profile=self.raw_profile.isChecked())
        except Exception as e:
            QMessageBox.critical(self, _("Erro ao abrir"), str(e))
            return
        self.file_label.setText(
            _("{base} — {n} scans").format(
                base=os.path.basename(path), n=len(self.run.scans)))
        self.ms_combo.blockSignals(True)
        self.ms_combo.clear()
        for lvl in self.run.ms_levels():
            self.ms_combo.addItem(f"MS{lvl}")
        self.ms_combo.setCurrentIndex(self.ms_combo.count() - 1)  # maior nível
        self.ms_combo.blockSignals(False)
        self.matches = []
        self.exp_mz, self.exp_int = [], []
        self.peak_mz, self.peak_int = [], []
        self.scan_label.setText(_("Scan: —"))
        self.match_table.setRowCount(0)
        self.spec_fig.clear()
        self.spec_canvas.draw()
        self._refresh_filters()   # já redesenha o cromatograma

    def _refresh_filters(self):
        """Repopula o combo de filtros de scan a partir do arquivo aberto."""
        if not self.run:
            return
        grouped = self.group_filters.isChecked()
        self.filter_combo.blockSignals(True)
        self.filter_combo.clear()
        self.filter_combo.addItem(_("(todos os scans)"), None)
        for f, n in self.run.filters(grouped=grouped):
            self.filter_combo.addItem(
                _("{f}   —   {n} scans").format(f=f, n=n), f)
        self.filter_combo.setCurrentIndex(0)
        self.filter_combo.blockSignals(False)
        self._plot_chromatogram()

    def _current_filter(self):
        return self.filter_combo.currentData()

    def _grouped(self):
        return self.group_filters.isChecked()

    def _current_ms_level(self):
        t = self.ms_combo.currentText()
        return int(t[2:]) if t.startswith("MS") else None

    def _plot_chromatogram(self):
        if not self.run:
            return
        rts, ints = self.run.chromatogram(
            ms_level=self._current_ms_level(),
            scan_filter=self._current_filter(), grouped=self._grouped())
        self.chrom_fig.clear()
        ax = self.chrom_fig.add_subplot(111)
        if rts:
            ax.plot(rts, ints, lw=0.9, color="#3d6fd6")
        ax.set_xlabel("RT (min)", fontsize=8)
        ax.set_ylabel("TIC", fontsize=8)
        ax.tick_params(labelsize=7)
        self.chrom_canvas.draw()

    def _plot_xic(self):
        if not self.run:
            return
        try:
            target = float(self.xic_mz.text().strip())
        except ValueError:
            QMessageBox.information(self, _("Aviso"),
                                    _("Informe um m/z válido para o XIC."))
            return
        rts, ints = self.run.xic(target, tol=self.xic_tol.value(), ppm=False,
                                 ms_level=self._current_ms_level(),
                                 scan_filter=self._current_filter(),
                                 grouped=self._grouped())
        self.chrom_fig.clear()
        ax = self.chrom_fig.add_subplot(111)
        if rts:
            ax.plot(rts, ints, lw=0.9, color="#2e9e6b")
        ax.set_xlabel("RT (min)", fontsize=8)
        ax.set_ylabel(f"XIC {target:.4f}", fontsize=8)
        ax.tick_params(labelsize=7)
        self.chrom_canvas.draw()

    def _xic_from_row(self, row, _col):
        it = self.match_table.item(row, 0)
        if it:
            self.xic_mz.setText(it.text())
            self._plot_xic()

    def _on_chrom_click(self, event):
        if not self.run or event.inaxes is None or event.xdata is None:
            return
        scan = self.run.scan_at_rt(event.xdata,
                                   ms_level=self._current_ms_level(),
                                   scan_filter=self._current_filter(),
                                   grouped=self._grouped())
        if scan is not None:
            self._select_scan(scan)

    def _select_scan(self, scan):
        try:
            mz, inten = self.run.spectrum(scan.index)
        except Exception as e:
            QMessageBox.critical(self, _("Erro ao ler scan"), str(e))
            return
        import spectra_io
        self.current_scan = scan
        self.exp_mz = [float(x) for x in mz]
        self.exp_int = [float(x) for x in inten]
        # em perfil, o matching precisa de uma lista de picos (centroidagem)
        if scan.profile:
            pmz, pint = spectra_io.centroid_peaks(mz, inten)
            self.peak_mz, self.peak_int = list(pmz), list(pint)
        else:
            self.peak_mz, self.peak_int = self.exp_mz, self.exp_int
        self.profile_view.blockSignals(True)
        self.profile_view.setChecked(bool(scan.profile))
        self.profile_view.blockSignals(False)
        txt = _("Scan {lbl}").format(lbl=scan.label)
        if scan.profile:
            txt += _("  [perfil: {n} picos]").format(n=len(self.peak_mz))
        if scan.filter_string:
            short = scan.filter_string
            if len(short) > 46:
                short = short[:43] + "…"
            txt += "  |  " + short
        self.scan_label.setText(txt)
        self.scan_label.setToolTip(scan.filter_string or "")
        # carga do precursor: lê do arquivo ou estima pelo cluster do MS1
        pz = scan.precursor_charge
        if not pz and scan.precursor_mz and self.run:
            ms1 = self.run.ms1_before(scan)
            if ms1 is not None:
                try:
                    mz1, i1 = self.run.spectrum(ms1.index)
                    pz, _nz = identification.estimate_charge(
                        mz1, i1, scan.precursor_mz)
                except Exception:
                    pz = None
        if pz:
            self.prec_charge.setValue(pz)
        self.matches = []
        self.match_table.setRowCount(0)
        self.crit_label.setText("—")
        self._plot_spectrum()

    def _selected_series(self):
        s = [i for i, cb in self.ser_checks.items() if cb.isChecked()]
        return s or ["b", "y"]

    def _selected_charges(self):
        c = [z for z, cb in self.z_checks.items() if cb.isChecked()]
        return c or [1]

    def _on_match_opts(self):
        # re-casa automaticamente ao mudar séries/perdas/cargas, se já há scan
        if self.exp_mz and self.state.last_mass_result:
            self._do_match()

    def _build_match_fragments(self):
        """Fragmentos para o match, conforme as séries, perdas neutras e cargas
        selecionadas no painel da própria aba."""
        result = self.state.last_mass_result
        if not result:
            return []
        losses = ["-NH3", "-H2O", "-CO"] if self.use_losses.isChecked() else []
        n_delta = result.n_term_mod.mono_delta if result.n_term_mod else 0.0
        c_delta = result.c_term_mod.mono_delta if result.c_term_mod else 0.0
        return generate_fragments(
            result, ion_types=self._selected_series(),
            charges=self._selected_charges(), neutral_losses=losses,
            include_no_loss=True, n_term_delta=n_delta, c_term_delta=c_delta)

    def _do_match(self):
        if not self.state.last_mass_result:
            QMessageBox.information(
                self, "Aviso", "Gere os fragmentos na Aba 2 primeiro.")
            return
        if not self.peak_mz:
            QMessageBox.information(
                self, "Aviso", "Escolha um scan clicando no cromatograma.")
            return
        self.match_fragments = self._build_match_fragments()
        self.matches = match_experimental(
            self.match_fragments, self.peak_mz, tolerance=self.tol.value(),
            ppm=self.ppm.isChecked())
        unit = "ppm" if self.ppm.isChecked() else "Da"
        base = max(self.peak_int) if self.peak_int else 1.0
        inten_by = {m: i for m, i in zip(self.peak_mz, self.peak_int)}
        self.match_table.setSortingEnabled(False)
        self.match_table.setRowCount(0)
        for exp, f, err in self.matches:
            rel = 100.0 * inten_by.get(exp, 0.0) / base
            row = self.match_table.rowCount()
            self.match_table.insertRow(row)
            self.match_table.setItem(row, 0, NumericItem(exp, f"{exp:.4f}"))
            self.match_table.setItem(row, 1, QTableWidgetItem(f.label))
            self.match_table.setItem(row, 2, NumericItem(f.charge, f"+{f.charge}"))
            self.match_table.setItem(row, 3, NumericItem(f.mz, f"{f.mz:.4f}"))
            self.match_table.setItem(row, 4, NumericItem(err, f"{err:+.3f} {unit}"))
            self.match_table.setItem(row, 5, NumericItem(rel, f"{rel:.1f}"))
            self.match_table.setItem(row, 6, QTableWidgetItem(f.sequence))
        self.match_table.setSortingEnabled(True)
        self.scan_label.setText(
            _("{p}  —  {n} íons anotados").format(
                p=self.scan_label.text().split('  —')[0], n=len(self.matches)))
        # escore de Morpheus + diagnóstico de erro de massa
        sc = scoring.score_spectrum(
            self.matches, self.peak_mz, self.peak_int,
            n_theoretical=len(self.match_fragments))
        me = sc["mass_error"]
        self.score_label.setText(
            _("Score (Morpheus): {score}   |   {n} íons casados   |   "
              "{tic}% da TIC explicada   |   cobertura {cov}%   |   "
              "erro mediano {med} {unit} (máx {mx}, RMSE {rmse})").format(
                  score=f"{sc['score']:.3f}", n=sc['n_matched'],
                  tic=f"{sc['tic_fraction'] * 100:.1f}",
                  cov=f"{sc['coverage']:.0f}",
                  med=f"{me['median']:+.2f}", unit=unit,
                  mx=f"{me['max_abs']:.2f}", rmse=f"{me['rmse']:.2f}"))
        self._evaluate_criteria(len(self.matches))
        self._plot_spectrum()

    def _evaluate_criteria(self, n_ions):
        """Avalia os critérios de identificação (estilo WADA): massa do
        precursor, tempo de retenção, íons diagnósticos e ajuste isotópico."""
        result = self.state.last_mass_result
        scan = self.current_scan
        if not result or not scan:
            self.crit_label.setText("—")
            return
        pz = self.prec_charge.value()
        parts = []
        # 1) massa do precursor
        if scan.precursor_mz and pz:
            neutral = scan.precursor_mz * pz - pz * identification.PROTON
            err = (neutral - result.mono_mass) / result.mono_mass * 1e6
            ok = abs(err) <= (self.tol.value() if self.ppm.isChecked() else 20.0)
            parts.append(("✓ " if ok else "✗ ") + _(
                "precursor {e} ppm (z={z})").format(e=f"{err:+.1f}", z=pz))
        # 2) tempo de retenção
        if self.rt_exp.value() > 0:
            drt = abs(scan.rt - self.rt_exp.value())
            ok = drt <= self.rt_win.value()
            parts.append(("✓ " if ok else "✗ ") + _(
                "RT Δ{d} min").format(d=f"{drt:.2f}"))
        # 3) íons diagnósticos
        parts.append(("✓ " if n_ions >= 2 else "✗ ") + _(
            "{n} íons diagnósticos").format(n=n_ions))
        # 4) ajuste do envelope isotópico (do MS1 anterior)
        try:
            ms1 = self.run.ms1_before(scan) if self.run else None
            if ms1 is not None:
                mz1, i1 = self.run.spectrum(ms1.index)
                dist = self.state.calc.isotopic_distribution(
                    result.composition, max_peaks=8)
                fit, nfit = identification.isotope_fit(
                    mz1, i1, dist, pz, tol=max(self.xic_tol.value(), 0.02))
                if nfit >= 2:
                    parts.append(("✓ " if fit >= 0.9 else "~ ") + _(
                        "isótopos {f}").format(f=f"{fit:.2f}"))
        except Exception:
            pass
        self.crit_label.setText(_("Critérios:") + "   " + "    ".join(parts))

    # íons N-terminais (a/b/c) vs C-terminais (x/y/z) para colorir a marcação
    _N_TERM_IONS = {"a", "b", "c"}
    _COL_N = "#2f6fd0"   # azul  — íons N-terminais
    _COL_C = "#c23b3b"   # vermelho — íons C-terminais

    def _plot_spectrum(self):
        self.spec_fig.clear()
        try:
            self.spec_fig.set_layout_engine("none")
        except Exception:
            pass
        # eixo na parte de baixo; ~31% do topo reservado p/ os 2 níveis de rótulo
        ax = self.spec_fig.add_axes([0.085, 0.17, 0.90, 0.52])
        if not self.exp_mz:
            ax.set_ylim(0, 100)
            ax.set_xlabel("m/z", fontsize=10)
            ax.tick_params(labelsize=9)
            self.spec_canvas.draw()
            return
        mxi = max(self.exp_int) or 1.0
        norm = [100.0 * i / mxi for i in self.exp_int]
        if self.profile_view.isChecked():
            # perfil: traço contínuo
            ax.plot(self.exp_mz, norm, lw=0.7, color="#9a9a9a")
        else:
            # centroide: picos verticais
            ax.vlines(self.exp_mz, 0, norm, color="#cfcfcf", lw=0.7)
        # alturas vindas da lista de picos (centroidada, se em perfil)
        h_by = {mz: 100.0 * i / mxi
                for mz, i in zip(self.peak_mz, self.peak_int)}

        # marca os casados pela cor da série e rotula logo acima do pico
        items = []
        for exp, f, err in self.matches:
            h = h_by.get(exp, 0.0)
            col = self._COL_N if f.ion_type in self._N_TERM_IONS else self._COL_C
            ax.vlines(exp, 0, h, color=col, lw=1.4)
            items.append((exp, h, col, f.label))
        if items:
            n = len(items)
            fs = 10 if n <= 22 else (9 if n <= 40 else 8)  # fonte adaptativa
            for mz, h, col, lab in items:
                ax.text(mz, min(h, 100) + 1.5, lab, rotation=90, fontsize=fs,
                        ha="center", va="bottom", color=col, clip_on=False)

        ax.set_ylim(0, 100)
        ax.set_yticks([0, 20, 40, 60, 80, 100])
        ax.set_xlabel("m/z", fontsize=10)
        ax.set_ylabel("Intensidade rel. (%)", fontsize=10)
        ax.tick_params(labelsize=9)
        self.spec_canvas.draw()


# ===========================================================================
# ABA 4 — Sequenciamento (identificação por biblioteca + de novo)
# ===========================================================================
class SequencingTab(QWidget):
    def __init__(self, app_state, exp_tab, parent=None):
        super().__init__(parent)
        self.state = app_state
        self.exp_tab = exp_tab
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        box = QGroupBox("Espectro MS/MS de entrada")
        bv = QVBoxLayout(box)
        row = QHBoxLayout()
        row.addWidget(QLabel("Precursor m/z:"))
        self.prec_mz = QDoubleSpinBox()
        self.prec_mz.setDecimals(4); self.prec_mz.setRange(0, 100000)
        row.addWidget(self.prec_mz)
        row.addWidget(QLabel("Carga:"))
        self.prec_z = QSpinBox(); self.prec_z.setRange(1, 10); self.prec_z.setValue(2)
        row.addWidget(self.prec_z)
        row.addWidget(QLabel("Tol.:"))
        self.tol = QDoubleSpinBox()
        self.tol.setDecimals(4); self.tol.setRange(0.0001, 1000); self.tol.setValue(10.0)
        row.addWidget(self.tol)
        self.ppm = QCheckBox("ppm"); self.ppm.setChecked(True); row.addWidget(self.ppm)
        pull = QPushButton("Pegar espectro da Aba 3")
        pull.clicked.connect(self._pull_from_exp); row.addWidget(pull)
        row.addStretch()
        bv.addLayout(row)
        self.peaks_text = QPlainTextEdit()
        self.peaks_text.setPlaceholderText(
            "Cole os picos: um m/z por linha (intensidade opcional após espaço/vírgula)")
        self.peaks_text.setFixedHeight(80)
        bv.addWidget(self.peaks_text)
        self.info = QLabel("—")
        bv.addWidget(self.info)
        root.addWidget(box)

        arow = QHBoxLayout()
        idb = QPushButton("Identificar por biblioteca")
        idb.setObjectName("accent"); idb.clicked.connect(self._identify)
        dnb = QPushButton("Sequenciar de novo")
        dnb.setObjectName("accent"); dnb.clicked.connect(self._denovo)
        arow.addWidget(idb); arow.addWidget(dnb); arow.addStretch()
        root.addLayout(arow)

        split = QSplitter(Qt.Orientation.Vertical)
        libbox = QGroupBox("Identificação por biblioteca (ranqueado)")
        lv = QVBoxLayout(libbox)
        self.lib_table = make_table(
            ["#", "Peptídeo", "Erro precursor", "Íons b/y", "Cobertura", "Score"])
        self.lib_table.customContextMenuRequested.connect(
            lambda p: copy_table_selection(self.lib_table))
        lv.addWidget(self.lib_table)
        split.addWidget(libbox)

        dnbox = QGroupBox("De novo (grafo de espectro)")
        dv = QVBoxLayout(dnbox)
        self.dn_result = QLabel("—")
        self.dn_result.setObjectName("result"); self.dn_result.setWordWrap(True)
        self.dn_note = QLabel(""); self.dn_note.setWordWrap(True)
        self.dn_note.setStyleSheet("color:#e0a96c;")
        dv.addWidget(self.dn_result); dv.addWidget(self.dn_note); dv.addStretch()
        split.addWidget(dnbox)
        split.setSizes([360, 150])
        root.addWidget(split, stretch=1)

    def _parse_peaks(self):
        mz, inten = [], []
        for line in self.peaks_text.toPlainText().replace(",", " ").splitlines():
            parts = line.split()
            if not parts:
                continue
            try:
                m = float(parts[0])
            except ValueError:
                continue
            i = 1.0
            if len(parts) > 1:
                try:
                    i = float(parts[1])
                except ValueError:
                    i = 1.0
            mz.append(m); inten.append(i)
        return mz, inten

    def _pull_from_exp(self):
        et = self.exp_tab
        if not getattr(et, "peak_mz", None):
            QMessageBox.information(
                self, "Aviso", "Escolha um scan na Aba 3 primeiro.")
            return
        self.peaks_text.setPlainText(
            "\n".join(f"{m:.4f} {i:.0f}" for m, i in zip(et.peak_mz, et.peak_int)))
        if et.current_scan and et.current_scan.precursor_mz:
            self.prec_mz.setValue(et.current_scan.precursor_mz)
        self.info.setText(f"{len(et.peak_mz)} picos importados da Aba 3.")

    def _get_input(self):
        mz, inten = self._parse_peaks()
        if not mz:
            QMessageBox.information(
                self, "Aviso", "Forneça os picos (cole ou pegue da Aba 3).")
            return None
        if self.prec_mz.value() <= 0:
            QMessageBox.information(
                self, "Aviso", "Informe o m/z do precursor.")
            return None
        return mz, inten

    def _identify(self):
        got = self._get_input()
        if not got:
            return
        mz, inten = got
        peps = self.state.db.list_peptides()
        rank = denovo.library_identify(
            self.state.calc, peps, mz, self.prec_mz.value(),
            self.prec_z.value(), tol=self.tol.value(), ppm=self.ppm.isChecked())
        self.lib_table.setSortingEnabled(False)
        self.lib_table.setRowCount(0)
        for i, x in enumerate(rank[:25], 1):
            row = self.lib_table.rowCount()
            self.lib_table.insertRow(row)
            self.lib_table.setItem(row, 0, NumericItem(i, str(i)))
            self.lib_table.setItem(row, 1, QTableWidgetItem(x["name"]))
            self.lib_table.setItem(row, 2, NumericItem(
                abs(x["prec_err_ppm"]), f"{x['prec_err_ppm']:+.1f} ppm"))
            self.lib_table.setItem(row, 3, NumericItem(
                x["matched"], f"{x['matched']}/{x['total_by']}"))
            self.lib_table.setItem(row, 4, NumericItem(
                x["coverage"], f"{x['coverage']:.0f}%"))
            self.lib_table.setItem(row, 5, NumericItem(
                x["score"], str(int(x["score"]))))
        self.lib_table.setSortingEnabled(True)
        if rank and rank[0]["score"] >= 1000:
            self.info.setText(f"Melhor candidato: {rank[0]['name']}  "
                              f"({rank[0]['matched']}/{rank[0]['total_by']} íons b/y).")

    def _denovo(self):
        got = self._get_input()
        if not got:
            return
        mz, inten = got
        da_tol = 0.02 if self.ppm.isChecked() else self.tol.value()
        res = denovo.denovo_sequence(
            mz, self.prec_mz.value(), self.prec_z.value(),
            peak_int=inten, tol=da_tol)
        seq = res["sequence"] or "(nenhum caminho encontrado)"
        self.dn_result.setText(f"Sequência (N→C):  {seq}")
        status = ("completa" if res["complete"]
                  else f"parcial — {res['coverage'] * 100:.0f}% da massa explicada")
        self.dn_note.setText(
            f"Cobertura {status}.  I/L são indistinguíveis por massa (rótulo "
            f"'I/L'); K/Q diferem só 0.036 Da. Use a identificação por "
            f"biblioteca para confirmar.")


# ===========================================================================
# Estado compartilhado da aplicação
# ===========================================================================
# Bibliotecas de peptideos-exemplo (GLP e antidopagem): ficam em presets.py,
# compartilhadas com a versao web.
from presets import (GLP_PRESETS, DOPING_PRESETS,  # noqa: E402
                     migrate_preset_names)


class AppState:
    def __init__(self):
        self.db = Database()
        self.custom_manager = CustomResidueManager(self.db)
        custom_mods = self._load_custom_mods()
        self.mod_library = ModificationLibrary(custom=custom_mods)
        self.calc = MassCalculator(self.custom_manager, self.mod_library)
        self.last_mass_result = None
        self.last_fragments = []
        self.on_mass_updated = None
        self._seed_presets()

    # Presets nossos que foram renomeados/corrigidos: nome antigo -> sequência
    # semeada. São removidos só se o usuário não os tiver editado.
    _OBSOLETE_PRESETS = {
        # TB-500 é o fragmento 17-23, não a timosina β4 inteira.
        "Timosina beta-4 (TB-500)":
            "SDKPDMAEIEKFDKSKLKKTETQEKNPLPSKETIEQEKQAGES",
    }

    def _drop_obsolete_presets(self):
        for name, seq in self._OBSOLETE_PRESETS.items():
            row = self.db.get_peptide(name)
            if row and row["sequence"] == seq:
                self.db.delete_peptide(name)

    def _seed_presets(self):
        """Semeia as bibliotecas de peptídeos-exemplo uma única vez por grupo
        (respeita exclusões futuras do usuário via flags em `meta`)."""
        self._drop_obsolete_presets()
        migrate_preset_names(self.db)
        for flag, presets in (("glp_presets_seeded", GLP_PRESETS),
                              ("doping_presets_seeded_v9", DOPING_PRESETS)):
            if self.db.get_meta(flag):
                continue
            for entry in presets:
                name, seq, nt, ct = entry[:4]
                rmods = entry[4] if len(entry) > 4 else "[]"
                if not self.db.get_peptide(name):
                    self.db.save_peptide(name, seq, nt, ct, rmods)
            self.db.set_meta(flag, "1")

    def _load_custom_mods(self):
        mods = []
        for row in self.db.list_modifications():
            try:
                comp = parse_formula(row["formula"])
                targets = (frozenset(row["targets"]) if row["targets"]
                           else frozenset({row["position"]}))
                mods.append(Modification(
                    name=row["name"], composition=comp, targets=targets,
                    position=row["position"], description=row.get("description", "")))
            except FormulaError:
                pass
        return mods


# ===========================================================================
# Janela principal
# ===========================================================================
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
        # Aba de Sequenciamento oculta na v1.0 (SequencingTab/denovo.py prontos
        # no código para reativar em versão futura).
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
        i18n.translate_tree(self)

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
            self.state.db.add_modification(name, formula, targets, position)
            comp = parse_formula(formula)
            tset = frozenset(targets) if targets else frozenset({position})
            self.state.mod_library.add(Modification(
                name=name, composition=comp, targets=tset, position=position))
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


if __name__ == "__main__":
    main()
