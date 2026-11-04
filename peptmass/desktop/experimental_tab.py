"""Aba 3: dados experimentais (mzML, mzXML e .raw)."""

import os

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QSpinBox, QSplitter,
    QTableWidgetItem, QVBoxLayout, QWidget)

from peptmass.core import identification
from peptmass.core import scoring
from peptmass.core.constants import PROTON_MASS
from peptmass.core.fragmentation import generate_fragments, match_experimental
from peptmass.core.i18n import t as _
from peptmass.desktop.widgets import NumericItem, copy_table_selection, make_table
from peptmass.infra import spectra_io


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
        distribution = self.state.calc.isotopic_distribution(
            result.composition, max_peaks=8)
        envelope = identification.ms1_envelope_fit(
            self.run, scan, distribution, pz, self.xic_tol.value())
        criteria = identification.evaluate_criteria(
            result.mono_mass, scan.precursor_mz, pz, self.tol.value(),
            self.ppm.isChecked(), scan.rt, self.rt_exp.value(),
            self.rt_win.value(), n_ions, envelope)
        marks = {"ok": "✓ ", "bad": "✗ ", "warn": "~ "}
        texts = {
            "precursor": lambda v: _("precursor {e} ppm (z={z})").format(
                e=f"{v:+.1f}", z=pz),
            "rt": lambda v: _("RT Δ{d} min").format(d=f"{v:.2f}"),
            "ions": lambda v: _("{n} íons diagnósticos").format(n=v),
            "isotopes": lambda v: _("isótopos {f}").format(f=f"{v:.2f}"),
        }
        parts = [marks[c["state"]] + texts[c["kind"]](c["value"]) for c in criteria]
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
