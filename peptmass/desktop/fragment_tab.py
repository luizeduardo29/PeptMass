"""Aba 2: fragmentacao MS/MS."""

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QDoubleSpinBox, QFileDialog, QGridLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QPushButton, QSplitter,
    QTableWidgetItem, QVBoxLayout, QWidget)

from peptmass.core.fragmentation import generate_fragments, match_experimental
from peptmass.core.i18n import t as _
from peptmass.desktop.widgets import (
    HoverTip, NumericItem, copy_table_selection, make_table)
from peptmass.infra import exporters


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
        self.spec_hover = HoverTip(self.canvas)
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
