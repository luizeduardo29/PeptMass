"""Aba 1: massa molecular."""

import json

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout,
    QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
    QPlainTextEdit, QPushButton, QSpinBox, QSplitter, QTableWidgetItem, QVBoxLayout,
    QWidget)

from peptmass.core.formula_parser import FormulaError
from peptmass.core.i18n import t as _
from peptmass.core.mass_calculator import SequenceError
from peptmass.desktop.dialogs import CustomResidueDialog
from peptmass.desktop.widgets import (
    HoverTip, NumericItem, copy_table_selection, make_table)
from peptmass.infra import exporters


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
        self.iso_hover = HoverTip(self.canvas)
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
