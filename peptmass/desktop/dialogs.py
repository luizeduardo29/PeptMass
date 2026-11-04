"""Dialogos de aminoacido, modificacao e busca no PubChem."""

from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QVBoxLayout)

from peptmass.core.formula_parser import FormulaError, composition_mass, parse_formula
from peptmass.core.i18n import t as _
from peptmass.desktop.translation import translate_tree
from peptmass.infra import pubchem


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
        translate_tree(self)

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
        translate_tree(self)

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
        translate_tree(self)

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
