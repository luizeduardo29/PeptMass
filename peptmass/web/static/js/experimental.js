/* Tela de Dados experimentais (a Aba 3 / ExperimentalTab do desktop).
   Abrir arquivo -> filtro de scan -> cromatograma (TIC/XIC) -> clique escolhe
   o scan -> "Casar com fragmentos" anota o espectro contra as series do
   peptideo da tela de Massa, com escore de Morpheus e criterios WADA. */
(function () {
  "use strict";
  var PM = window.PM, T = PM.T, el = PM.el, num = PM.num;
  function $(id) { return document.getElementById(id); }

  var MAX_LABELS = 15, LABEL_GAP_PX = 14;
  var SCAN_MARGIN = { l: 58, r: 18, t: 34, b: 46 };
  var runId = null, scan = null, spectrum = null, matches = [], chrom = null;
  var chromChart = $("graf-crom"), scanChart = $("graf-scan");
  var status = $("ms-estado");

  /* ------------------------------------------------------------ preferencias */
  var PREF_IDS = ["ms-tol", "ms-ppm", "ms-rt", "ms-rt-janela", "ms-perdas", "ms-xic-tol", "ms-agrupar"];
  function savePrefs() {
    var o = { series: PM.checkedValues($("ms-series")), charges: PM.checkedValues($("ms-cargas")) };
    PREF_IDS.forEach(function (id) { var n = $(id); o[id] = n.type === "checkbox" ? n.checked : n.value; });
    PM.save("ms.prefs", o);
  }
  function restorePrefs() {
    var o = PM.load("ms.prefs", null);
    if (!o) return;
    [["ms-series", o.series], ["ms-cargas", o.charges]].forEach(function (pair) {
      if (!Array.isArray(pair[1])) return;
      Array.prototype.forEach.call($(pair[0]).querySelectorAll("input[type=checkbox][value]"), function (cb) {
        cb.checked = pair[1].indexOf(cb.value) >= 0;
      });
    });
    PREF_IDS.forEach(function (id) {
      if (o[id] === undefined) return;
      var n = $(id);
      if (n.type === "checkbox") n.checked = !!o[id]; else n.value = o[id];
    });
  }

  function selection() {
    return { ms_level: $("ms-nivel").value, filter: $("ms-filtro").value, grouped: $("ms-agrupar").checked };
  }

  function runGone(res) {
    if (res && res.code === "run_gone") {
      runId = null;
      $("ms-selecao").hidden = true;
      $("ms-casar").disabled = true;
      PM.setState(status, res.error, "warn");
      return true;
    }
    return false;
  }

  /* --------------------------------------------------------------- abrir */
  $("ms-form").addEventListener("submit", function (event) {
    event.preventDefault();
    var file = $("ms-arquivo").files[0];
    if (!file) { PM.setState(status, T("ms.no_file"), "warn"); return; }
    openFile(file);
  });

  /* ?exemplo=1 (vindo da tela Como usar): abre o arquivo de exemplo incluso */
  function openExample() {
    var url = $("ms-form").getAttribute("data-exemplo");
    window.history.replaceState(null, "", window.location.pathname);
    fetch(url).then(function (r) { return r.blob(); }).then(function (blob) {
      openFile(new File([blob], url.split("/").pop()));
    });
  }

  function openFile(file) {
    /* Acima do limite do servidor: avisa aqui, sem enviar o arquivo */
    var maxMb = parseInt($("ms-form").getAttribute("data-max-mb"), 10);
    if (maxMb && file.size > maxMb * 1048576) {
      PM.setState(status, "✗ " + T("ms.file.too_large",
        { f: file.name, size: Math.ceil(file.size / 1048576), max: maxMb }), "bad");
      return;
    }
    var form = new FormData();
    form.append("file", file);
    form.append("profile", $("ms-perfil").checked ? "1" : "0");
    $("ms-abrir").disabled = true;
    $("ms-progresso").hidden = false;
    PM.setState(status, T("ms.file.opening", { f: file.name }));
    PM.api("/api/ms/open", { form: form }).then(function (res) {
      $("ms-abrir").disabled = false;
      $("ms-progresso").hidden = true;
      if (!res.ok) { PM.setState(status, "✗ " + res.error, "bad"); return; }
      runId = res.run_id;
      PM.setState(status, T("ms.file.opened", { f: res.filename, n: res.n_scans }), "ok");
      var level = $("ms-nivel");
      level.innerHTML = "";
      res.levels.forEach(function (lvl) { level.appendChild(el("option", { value: lvl, text: "MS" + lvl })); });
      level.value = String(res.levels[res.levels.length - 1]);   // o maior nivel
      $("ms-selecao").hidden = false;
      resetScan();
      loadFilters();
    });
  }

  /* ---------------------------------------------- leitor de .raw (executavel) */
  /* O executavel nao traz o ThermoRawFileParser (licenca da Thermo). Aqui o
     usuario o baixa do repositorio oficial, le a licenca e so entao instala. */
  var reader = $("ms-leitor"), readerState = $("ms-leitor-estado"), readerDlg = $("dlg-leitor");
  function readerMsg(text, kind) {
    readerState.hidden = !text;
    PM.setState(readerState, text, kind);
  }
  function checkReader() {
    PM.api("/api/raw-reader").then(function (res) {
      reader.hidden = !(res.ok && res.installable);
    });
  }
  $("ms-leitor-instalar").addEventListener("click", function () {
    var btn = this;
    btn.disabled = true;
    readerMsg(T("ms.reader.downloading"));
    PM.api("/api/raw-reader/download", { body: {} }).then(function (res) {
      btn.disabled = false;
      if (!res.ok) { readerMsg("✗ " + res.error, "bad"); return; }
      readerMsg("");
      $("leitor-licenca").textContent = res.thermo_license +
        (res.license ? "\n\n────────────────\n\nThermoRawFileParser\n\n" + res.license : "");
      $("leitor-licenca").scrollTop = 0;
      readerDlg.showModal();
    });
  });
  $("leitor-aceitar").addEventListener("click", function () {
    readerDlg.close();
    PM.api("/api/raw-reader/accept", { body: {} }).then(function (res) {
      if (!res.ok) { readerMsg("✗ " + res.error, "bad"); return; }
      reader.hidden = true;
      readerMsg("✓ " + T("ms.reader.installed"), "ok");
    });
  });
  function declineReader() {
    PM.api("/api/raw-reader/cancel", { body: {} });
    readerMsg(T("ms.reader.cancelled"), "warn");
  }
  $("leitor-recusar").addEventListener("click", function () { readerDlg.close(); declineReader(); });
  readerDlg.addEventListener("cancel", declineReader);   // tecla Esc
  checkReader();

  function loadFilters() {
    if (!runId) return;
    PM.api("/api/ms/" + runId + "/filters?grouped=" + ($("ms-agrupar").checked ? "1" : "0")).then(function (res) {
      if (runGone(res)) return;
      var sel = $("ms-filtro");
      sel.innerHTML = "";
      sel.appendChild(el("option", { value: "", text: T("ms.filter.all") }));
      (res.filters || []).forEach(function (f) {
        sel.appendChild(el("option", { value: f[0], text: T("ms.filter.item", { f: f[0], n: f[1] }) }));
      });
      drawTic();
    });
  }

  /* --------------------------------------------------------- cromatograma */
  function drawTic() {
    if (!runId) return;
    PM.api("/api/ms/" + runId + "/chromatogram", { body: selection() }).then(function (res) {
      if (runGone(res)) return;
      if (!res.ok) { PM.emptyChart(chromChart, res.error); return; }
      chrom = { rt: res.rt, y: res.intensity, kind: "tic", title: "TIC" };
      plotChrom();
    });
  }

  function drawXic(mz) {
    if (!runId) return;
    var target = mz !== undefined ? mz : parseFloat($("ms-xic-mz").value);
    if (!(target > 0)) { PM.setState(status, T("ms.xic.bad_mz"), "warn"); return; }
    $("ms-xic-mz").value = num(target, 4);
    var body = Object.assign(selection(), { mz: target, tol: $("ms-xic-tol").value });
    PM.api("/api/ms/" + runId + "/xic", { body: body }).then(function (res) {
      if (runGone(res)) return;
      if (!res.ok) { PM.setState(status, res.error, "warn"); return; }
      chrom = { rt: res.rt, y: res.intensity, kind: "xic", title: "XIC " + num(res.mz, 4) };
      plotChrom();
      chromChart.scrollIntoView({ behavior: "smooth", block: "center" });
    });
  }

  function plotChrom() {
    if (!chrom) { PM.emptyChart(chromChart, T("ms.file.none")); return; }
    if (!chrom.rt.length) { PM.emptyChart(chromChart, T("ms.chrom.empty")); return; }
    var c = PM.colors();
    var color = chrom.kind === "xic" ? c.xic : c.linha;
    var shapes = scan ? [{ type: "line", xref: "x", yref: "paper", x0: scan.rt, x1: scan.rt, y0: 0, y1: 1,
                           line: { color: c.c, width: 1, dash: "dot" } }] : [];
    PM.plot(chromChart, [{
      type: "scatter", mode: "lines", x: chrom.rt, y: chrom.y,
      line: { color: color, width: 1.2 },
      hovertemplate: "RT %{x:.3f} min<br>%{y:.3s}<extra></extra>"
    }], {
      hovermode: "x",
      xaxis: { title: { text: "RT (min)" } },
      yaxis: { title: { text: chrom.title }, exponentformat: "e" },
      shapes: shapes
    });
    // react() mantem os ouvintes, purge() (grafico vazio) os apaga: refaz sempre
    if (chromChart.removeAllListeners) chromChart.removeAllListeners("plotly_click");
    chromChart.on("plotly_click", function (ev) {
      if (ev && ev.points && ev.points.length) selectScan({ rt: ev.points[0].x });
    });
  }

  /* ----------------------------------------------------------------- scan */
  function resetScan() {
    scan = null; spectrum = null; matches = [];
    $("ms-scan-rotulo").textContent = T("ms.scan.none");
    $("ms-scan-rotulo").className = "tag na";
    $("ms-casar").disabled = true;
    $("ms-escore").textContent = "-";
    renderCriteria(null);
    renderTable();
    PM.emptyChart(scanChart, T("ms.scan.pick"));
  }

  function selectScan(query) {
    if (!runId) return;
    PM.api("/api/ms/" + runId + "/scan", { body: Object.assign(selection(), query) }).then(function (res) {
      if (runGone(res)) return;
      if (!res.ok) { PM.setState(status, res.error, "warn"); return; }
      scan = res.scan;
      spectrum = res.spectrum;
      matches = [];
      var label = T("ms.scan.label", { l: scan.label });
      if (scan.profile) label += "  " + T("ms.scan.profile", { n: scan.n_peaks });
      var tag = $("ms-scan-rotulo");
      tag.textContent = label;
      tag.title = scan.filter || "";
      tag.className = "tag";
      if (scan.precursor_charge) $("ms-carga-prec").value = scan.precursor_charge;
      $("ms-ver-perfil").checked = !!scan.profile;
      $("ms-casar").disabled = false;
      $("ms-escore").textContent = "-";
      renderCriteria(null);
      renderTable();
      plotScan();
      plotChrom();
      if (scan.precursor_charge && scan.charge_estimated) {
        PM.setState(status, T("ms.scan.charge_estimated", { z: scan.precursor_charge }));
      }
    });
  }

  function mzRange(mzs) {
    return mzs.reduce(function (r, mz) { return [Math.min(r[0], mz), Math.max(r[1], mz)]; }, [Infinity, -Infinity]);
  }

  /* Legendas so dos ions mais intensos da faixa visivel, sem sobrepor: ao dar
     zoom a faixa encolhe e os ions menores ganham legenda. */
  function scanLabels(c, xMin, xMax) {
    var visible = matches.filter(function (m) { return m.exp >= xMin && m.exp <= xMax; })
      .sort(function (a, b) { return b.rel - a.rel; });
    var plotWidth = Math.max(scanChart.clientWidth - SCAN_MARGIN.l - SCAN_MARGIN.r, 1);
    var minGap = LABEL_GAP_PX * (xMax - xMin) / plotWidth;
    var chosen = [];
    visible.some(function (m) {
      var fits = chosen.every(function (o) { return Math.abs(o.exp - m.exp) >= minGap; });
      if (fits) chosen.push(m);
      return chosen.length >= MAX_LABELS;
    });
    return chosen.reduce(function (out, m) {
      return out.concat(PM.labels([m.exp], [Math.min(m.rel, 100)], [m.label], c.ions[m.type], 10));
    }, []);
  }

  function plotScan() {
    if (!spectrum) { PM.emptyChart(scanChart, T("ms.scan.pick")); return; }
    var c = PM.colors();
    var mx = 0;   // laco, nao Math.max.apply: perfil passa de 100 mil pontos
    for (var k = 0; k < spectrum.intensity.length; k++) if (spectrum.intensity[k] > mx) mx = spectrum.intensity[k];
    mx = mx || 1;
    var norm = spectrum.intensity.map(function (i) { return 100 * i / mx; });
    var traces = [];
    var peaks = $("ms-ver-perfil").checked
      ? { type: "scatter", mode: "lines", x: spectrum.mz, y: norm, hoverinfo: "skip",
          line: { color: c.pico, width: 0.8 } }
      : PM.sticks(spectrum.mz, norm, c.pico, 0.8);
    peaks.showlegend = false;
    traces.push(peaks);
    var annotations = [];
    if (matches.length) {
      Object.keys(c.ions).forEach(function (ion) {
        var list = matches.filter(function (m) { return m.type === ion; });
        if (!list.length) return;
        var color = c.ions[ion];
        var xs = list.map(function (m) { return m.exp; });
        var ys = list.map(function (m) { return Math.min(m.rel, 100); });
        var sticks = PM.sticks(xs, ys, color, 1.6);
        sticks.name = ion;
        traces.push(sticks);
        traces.push(PM.hoverPoints(xs, ys, list.map(function (m) {
          return "<b>" + m.label + "</b>  " + m.z + "+<br>exp " + num(m.exp, 4) + " · " + T("ms.col.theo") + " " +
                 num(m.theo, 4) + "<br>" + T("ms.col.error") + " " + num(m.err, 2, true) + " " + matchUnit + "<br>" + m.seq;
        }), color));
      });
      var range = mzRange(matches.map(function (m) { return m.exp; }).concat(spectrum.mz));
      annotations = scanLabels(c, range[0], range[1]);
    }
    PM.plot(scanChart, traces, {
      showlegend: matches.length > 0,
      legend: { orientation: "h", x: 0, y: 1.08, font: { color: c.texto }, itemclick: false, itemdoubleclick: false },
      margin: SCAN_MARGIN,
      xaxis: { title: { text: "m/z" }, showgrid: false },
      yaxis: { title: { text: T("chart.intensity_pct") }, range: [0, matches.length ? 140 : 105],
               tickvals: [0, 20, 40, 60, 80, 100], showgrid: false },
      annotations: annotations
    });
    // react() mantem os ouvintes, purge() (grafico vazio) os apaga: refaz sempre
    if (scanChart.removeAllListeners) scanChart.removeAllListeners("plotly_relayout");
    scanChart.on("plotly_relayout", function (ev) {
      var zoomed = ev["xaxis.range[0]"] !== undefined || ev["xaxis.autorange"];
      if (!zoomed || !matches.length) return;
      var range = scanChart.layout.xaxis.range;
      window.Plotly.relayout(scanChart, { annotations: scanLabels(PM.colors(), range[0], range[1]) });
    });
  }

  /* ------------------------------------------------------------- matching */
  var matchUnit = "ppm";

  function doMatch() {
    if (!runId || !scan) return;
    if (!PM.peptide.has()) { $("ms-sem-peptideo").hidden = false; return; }
    savePrefs();
    var body = {
      index: scan.index, peptide: PM.peptide.get(),
      series: PM.checkedValues($("ms-series")), charges: PM.checkedValues($("ms-cargas")).map(Number),
      losses: $("ms-perdas").checked, tol: $("ms-tol").value, ppm: $("ms-ppm").checked,
      prec_charge: $("ms-carga-prec").value, rt_exp: $("ms-rt").value, rt_win: $("ms-rt-janela").value,
      xic_tol: $("ms-xic-tol").value
    };
    PM.api("/api/ms/" + runId + "/match", { body: body }).then(function (res) {
      if (runGone(res)) return;
      if (!res.ok) {
        $("ms-escore").textContent = "✗ " + res.error;
        return;
      }
      matches = res.matches;
      matchUnit = res.unit;
      var s = res.score;
      $("ms-escore").textContent = T("ms.score", {
        score: num(s.score, 3), n: s.n, tic: num(s.tic, 1), cov: num(s.coverage, 0),
        med: num(s.median, 2, true), unit: res.unit, mx: num(s.max, 2), rmse: num(s.rmse, 2)
      });
      $("ms-scan-rotulo").textContent = T("ms.scan.label", { l: scan.label }) + "  ·  " +
        T("ms.scan.annotated", { n: matches.length });
      renderCriteria(res.criteria);
      renderTable();
      plotScan();
    });
  }

  function renderCriteria(list) {
    var box = $("ms-criterios");
    box.innerHTML = "";
    if (!list || !list.length) { box.appendChild(el("span", { class: "muted", text: "-" })); return; }
    var icon = { ok: "✓ ", bad: "✗ ", warn: "~ " };
    list.forEach(function (c) {
      box.appendChild(el("span", { class: "tag " + c.state, text: (icon[c.state] || "") + c.text }));
    });
  }

  function renderTable() {
    var body = $("tab-anotacao").tBodies[0];
    body.innerHTML = "";
    if (!matches.length) {
      body.appendChild(el("tr", {}, [el("td", { colspan: "7", class: "vazio", text: "-" })]));
      return;
    }
    matches.forEach(function (m) {
      body.appendChild(el("tr", { class: "clicavel", title: T("ms.table_row_help"),
                                  ondblclick: function () { drawXic(m.exp); } }, [
        el("td", { class: "num", "data-v": m.exp, text: num(m.exp, 4) }),
        el("td", { text: m.label }),
        el("td", { class: "num", "data-v": m.z, text: "+" + m.z }),
        el("td", { class: "num", "data-v": m.theo, text: num(m.theo, 4) }),
        el("td", { class: "num", "data-v": m.err, text: num(m.err, 3, true) + " " + matchUnit }),
        el("td", { class: "num", "data-v": m.rel, text: num(m.rel, 1) }),
        el("td", { class: "mono", text: m.seq })
      ]));
    });
  }

  /* -------------------------------------------------------------- eventos */
  $("ms-nivel").addEventListener("change", drawTic);
  $("ms-filtro").addEventListener("change", drawTic);
  $("ms-agrupar").addEventListener("change", function () { savePrefs(); loadFilters(); });
  $("ms-tic").addEventListener("click", drawTic);
  $("ms-xic").addEventListener("click", function () { drawXic(); });
  $("ms-xic-mz").addEventListener("keydown", function (e) { if (e.key === "Enter") { e.preventDefault(); drawXic(); } });
  $("ms-casar").addEventListener("click", doMatch);
  $("ms-ver-perfil").addEventListener("change", plotScan);
  // como no desktop: mudar series/perdas/cargas/tolerancia re-casa sozinho
  ["ms-series", "ms-cargas"].forEach(function (id) {
    $(id).addEventListener("change", function (e) {
      if (e.target.id === "ms-ver-perfil") return;
      if (scan && matches.length) doMatch(); else savePrefs();
    });
  });
  ["ms-ppm", "ms-tol"].forEach(function (id) {
    $(id).addEventListener("change", function () { if (scan && matches.length) doMatch(); else savePrefs(); });
  });
  ["ms-rt", "ms-rt-janela", "ms-carga-prec", "ms-xic-tol"].forEach(function (id) {
    $(id).addEventListener("change", savePrefs);
  });
  PM.onTheme(function () { if (chrom) plotChrom(); plotScan(); });

  restorePrefs();
  $("ms-sem-peptideo").hidden = PM.peptide.has();
  PM.emptyChart(chromChart, T("ms.file.none"));
  PM.emptyChart(scanChart, T("ms.scan.pick"));
  if (new URLSearchParams(window.location.search).has("exemplo")) openExample();
})();
