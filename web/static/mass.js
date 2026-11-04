/* Tela de Massa (a Aba 1 / MassTab do desktop): recalcula 250 ms depois de
   cada alteracao, guarda o peptideo para as outras telas e cuida de mods por
   residuo, peptideos salvos, FASTA e cadastro de residuos desconhecidos. */
(function () {
  "use strict";
  var PM = window.PM, T = PM.T, el = PM.el, num = PM.num;
  function $(id) { return document.getElementById(id); }

  var seq = $("seq"), nterm = $("nterm"), cterm = $("cterm");
  var status = $("seq-estado"), defineBtn = $("btn-definir");
  var chartIso = $("graf-iso");
  var rmods = [];          // [[indice_0, nome_mod], ...]
  var codes = [];          // codigos de residuo da ultima sequencia
  var isotopes = [];       // [[massa_neutra, intensidade], ...]
  var lastUnknown = [];

  /* ------------------------------------------------------------ estado */
  function current() {
    return { sequence: seq.value, nterm: nterm.value, cterm: cterm.value, rmods: rmods.slice() };
  }

  function selectValue(select, value) {
    var has = Array.prototype.some.call(select.options, function (o) { return o.value === value; });
    select.value = has ? value : "";
  }

  function apply(p) {
    seq.value = p.sequence || "";
    selectValue(nterm, p.nterm || "");
    selectValue(cterm, p.cterm || "");
    rmods = (p.rmods || []).map(function (x) { return [Number(x[0]), String(x[1])]; });
  }

  /* ----------------------------------------------------------- calculo */
  function clearResults() {
    $("res-mono").textContent = "-";
    $("res-avg").textContent = "-";
    $("res-formula").textContent = "-";
    $("res-residuos").textContent = "-";
    $("res-avisos").hidden = true;
    var body = $("tab-cargas").tBodies[0];
    body.innerHTML = "";
    body.appendChild(el("tr", {}, [el("td", { colspan: "2", class: "vazio", text: T("mass.empty") })]));
    isotopes = [];
    PM.emptyChart(chartIso, T("mass.empty"));
  }

  function calc() {
    var p = current();
    PM.peptide.set(p);
    PM.save("mass.charges", { zmin: $("zmin").value, zmax: $("zmax").value, zextra: $("zextra").value });
    if (!p.sequence.trim()) {
      PM.setState(status, T("mass.seq.empty_hint"));
      defineBtn.hidden = true;
      codes = [];
      renderRmods();
      clearResults();
      return;
    }
    PM.api("/api/mass", { body: { peptide: p, zmin: $("zmin").value, zmax: $("zmax").value,
                                  zextra: $("zextra").value } }).then(function (res) {
      if (!res.ok) { PM.setState(status, "✗ " + res.error, "bad"); return; }
      codes = res.codes || [];
      renderRmods();
      lastUnknown = res.unknown || [];
      defineBtn.hidden = !lastUnknown.length;
      if (lastUnknown.length) {
        defineBtn.querySelector("span").textContent = T("mass.define_unknown", { x: lastUnknown.join(", ") });
      }
      if (!res.valid) {
        PM.setState(status, "✗ " + res.message, "bad");
        clearResults();
        return;
      }
      PM.setState(status, "✓ " + res.message, "ok");
      showResult(res);
    });
  }
  var schedule = PM.debounce(calc, 250);

  function showResult(res) {
    var r = res.result;
    $("res-mono").textContent = num(r.mono, 6);
    $("res-avg").textContent = num(r.avg, 6) + " Da";
    $("res-formula").textContent = r.formula;
    $("res-residuos").textContent = r.n_chains > 1
      ? T("mass.res.residues_chains", { n: r.n_residues, c: r.n_chains })
      : String(r.n_residues);
    var warn = $("res-avisos");
    warn.hidden = !r.warnings.length;
    warn.textContent = r.warnings.length ? "⚠ " + r.warnings.join(" | ") : "";

    var body = $("tab-cargas").tBodies[0];
    body.innerHTML = "";
    res.charges.forEach(function (row) {
      body.appendChild(el("tr", {}, [
        el("td", { class: "num", "data-v": row[0], text: "+" + row[0] }),
        el("td", { class: "num", "data-v": row[1], text: num(row[1], 6) })
      ]));
    });
    isotopes = res.isotopes || [];
    plotIsotopes();
  }

  function plotIsotopes() {
    if (!isotopes.length) { PM.emptyChart(chartIso, T("mass.empty")); return; }
    var z = Math.max(0, parseInt($("iso-z").value, 10) || 0);
    var c = PM.colors();
    var xs = isotopes.map(function (p) { return z ? (p[0] + z * PM.proton) / z : p[0]; });
    var ys = isotopes.map(function (p) { return p[1]; });
    var ztag = z ? "  (" + z + "+)" : "";
    var tips = xs.map(function (x, i) { return "m/z " + num(x, 4) + ztag + "<br>" + num(ys[i], 2) + " %"; });
    var showLabels = $("iso-rotulos").checked;
    PM.plot(chartIso, [PM.sticks(xs, ys, c.linha, 2), PM.hoverPoints(xs, ys, tips, c.linha)], {
      xaxis: { title: { text: z ? "m/z (" + z + "+)" : T("mass.iso.neutral_axis") } },
      yaxis: { title: { text: T("chart.intensity_pct") }, range: [0, showLabels ? 150 : 110] },
      annotations: showLabels ? PM.labels(xs, ys, xs.map(function (x) { return num(x, 4); }), c.texto, 9) : []
    });
  }

  /* ----------------------------------------------------- mods por residuo */
  function renderRmods() {
    var list = $("rmods");
    list.innerHTML = "";
    if (!rmods.length) {
      list.appendChild(el("li", { class: "vazio", style: "background:none;color:inherit", text: T("common.none") }));
      return;
    }
    rmods.forEach(function (item, k) {
      var code = codes[item[0]] || "?";
      list.appendChild(el("li", {}, [
        code + (item[0] + 1) + " → " + item[1],
        el("button", { type: "button", title: T("common.remove"), "aria-label": T("common.remove"), text: "×",
                       onclick: function () { rmods.splice(k, 1); renderRmods(); schedule(); } })
      ]));
    });
  }

  function fillMods(code) {
    var select = $("rmod-mod"), info = $("rmod-info");
    select.innerHTML = "";
    info.textContent = "…";
    PM.api("/api/modifications?residue=" + encodeURIComponent(code)).then(function (res) {
      var mods = res.ok ? res.modifications : [];
      mods.forEach(function (m) {
        select.appendChild(el("option", { value: m.name, "data-info": m.formula + "   " + num(m.delta, 6, true) + " Da",
                                          text: m.name }));
      });
      showModInfo();
    });
  }
  function showModInfo() {
    var opt = $("rmod-mod").selectedOptions[0];
    $("rmod-info").textContent = opt ? opt.getAttribute("data-info") : "-";
  }

  $("btn-add-rmod").addEventListener("click", function () {
    if (!codes.length) { PM.setState(status, T("mass.rmod.need_seq"), "warn"); return; }
    var pos = $("rmod-pos");
    pos.innerHTML = "";
    codes.forEach(function (c, i) { pos.appendChild(el("option", { value: i, text: (i + 1) + ": " + c })); });
    pos.onchange = function () { fillMods(codes[Number(pos.value)]); };
    $("rmod-mod").onchange = showModInfo;
    fillMods(codes[0]);
    $("rmod-ok").onclick = function () {
      var idx = Number(pos.value), name = $("rmod-mod").value;
      if (!name) return;
      rmods = rmods.filter(function (x) { return x[0] !== idx; });
      rmods.push([idx, name]);
      rmods.sort(function (a, b) { return a[0] - b[0]; });
      $("dlg-rmod").close();
      renderRmods();
      schedule();
    };
    $("dlg-rmod").showModal();
  });

  $("btn-clear-rmods").addEventListener("click", function () { rmods = []; renderRmods(); schedule(); });

  /* -------------------------------------------- residuos desconhecidos */
  defineBtn.addEventListener("click", function () {
    var queue = lastUnknown.slice(), added = [];
    function next() {
      if (!queue.length) { done(); return; }
      var code = queue.shift();
      PM.residueDialog({ code: code, lockCode: true, title: T("dlg.residue.define", { c: code }) })
        .then(function (saved) {
          if (!saved) { done(); return; }   // cancelou: interrompe a fila
          added.push(saved);
          next();
        });
    }
    function done() {
      if (added.length) {
        PM.setState($("salvos-estado"), "");
        calc();
        setTimeout(function () { PM.setState(status, "✓ " + T("mass.define_done", { x: added.join(", ") }), "ok"); }, 400);
      }
    }
    next();
  });

  /* ------------------------------------------------ peptideos salvos */
  var savedSel = $("salvos"), savedStatus = $("salvos-estado");

  function refreshSaved(select) {
    return PM.api("/api/peptides").then(function (res) {
      if (!res.ok) return;
      savedSel.innerHTML = "";
      res.peptides.forEach(function (n) { savedSel.appendChild(el("option", { value: n, text: n })); });
      if (select) savedSel.value = select;
    });
  }

  function loadPeptide(name) {
    return PM.api("/api/peptide?name=" + encodeURIComponent(name)).then(function (res) {
      if (!res.ok) { PM.setState(savedStatus, res.error, "bad"); return; }
      apply(res.peptide);
      savedSel.value = res.name;
      PM.setState(savedStatus, T("mass.saved.loaded", { n: res.name }), "ok");
      calc();
    });
  }

  $("btn-carregar").addEventListener("click", function () {
    if (savedSel.value) loadPeptide(savedSel.value);
  });

  $("btn-remover").addEventListener("click", function () {
    var name = savedSel.value;
    if (!name || !window.confirm(T("mass.saved.confirm_remove", { n: name }))) return;
    PM.api("/api/peptide?name=" + encodeURIComponent(name), { method: "DELETE" }).then(function (res) {
      if (!res.ok) { PM.setState(savedStatus, res.error, "bad"); return; }
      PM.setState(savedStatus, T("mass.saved.removed", { n: name }), "ok");
      refreshSaved();
    });
  });

  $("btn-salvar").addEventListener("click", function () {
    if (!seq.value.trim()) { PM.setState(savedStatus, T("peptide.empty"), "warn"); return; }
    var dlg = $("dlg-salvar"), input = $("salvar-nome"), err = $("salvar-erro");
    input.value = savedSel.value || "";
    PM.setState(err, "", "bad");
    function send(overwrite) {
      var name = input.value.trim();
      PM.api("/api/peptide", { body: { name: name, peptide: current(), overwrite: overwrite } }).then(function (res) {
        if (!res.ok && res.exists) {
          if (window.confirm(T("mass.saved.confirm_overwrite", { n: name }))) send(true);
          return;
        }
        if (!res.ok) { PM.setState(err, res.error, "bad"); return; }
        dlg.close();
        PM.setState(savedStatus, res.message, "ok");
        refreshSaved(name);
      });
    }
    $("salvar-ok").onclick = function () { send(false); };
    input.onkeydown = function (e) { if (e.key === "Enter") { e.preventDefault(); send(false); } };
    dlg.showModal();
    input.focus();
    input.select();
  });

  /* ------------------------------------------------------------- FASTA */
  $("btn-fasta").addEventListener("click", function () { $("fasta-arquivo").click(); });
  $("fasta-arquivo").addEventListener("change", function () {
    var file = this.files && this.files[0];
    this.value = "";
    if (!file) return;
    var reader = new FileReader();
    reader.onload = function () {
      PM.api("/api/fasta", { body: { text: String(reader.result || "") } }).then(function (res) {
        var entries = res.ok ? res.entries : [];
        if (!entries.length) { PM.setState(status, T("mass.fasta.empty"), "warn"); return; }
        if (entries.length === 1) { seq.value = entries[0].sequence; calc(); return; }
        var list = $("fasta-entradas");
        list.innerHTML = "";
        entries.forEach(function (e, i) {
          list.appendChild(el("option", { value: i, text: e.header.slice(0, 70) + "  (" + e.sequence.length + " aa)" }));
        });
        list.value = "0";
        $("fasta-ok").onclick = function () {
          var e = entries[Number(list.value)];
          if (e) { seq.value = e.sequence; calc(); }
          $("dlg-fasta").close();
        };
        list.ondblclick = $("fasta-ok").onclick;
        $("dlg-fasta").showModal();
      });
    };
    reader.readAsText(file);
  });

  /* ----------------------------------------------------------- eventos */
  seq.addEventListener("input", schedule);
  nterm.addEventListener("change", calc);
  cterm.addEventListener("change", calc);
  ["zmin", "zmax", "zextra"].forEach(function (id) { $(id).addEventListener("input", schedule); });
  $("iso-z").addEventListener("input", function () {
    PM.save("mass.iso_z", this.value);
    plotIsotopes();
  });
  $("iso-rotulos").addEventListener("change", function () {
    PM.save("mass.iso_labels", this.checked);
    plotIsotopes();
  });
  PM.onTheme(plotIsotopes);

  /* ------------------------------------------------------------ inicio */
  var charges = PM.load("mass.charges", null);
  if (charges) {
    $("zmin").value = charges.zmin || 1;
    $("zmax").value = charges.zmax || 10;
    $("zextra").value = charges.zextra === undefined ? "15, 20" : charges.zextra;
  }
  $("iso-z").value = PM.load("mass.iso_z", "0");
  $("iso-rotulos").checked = PM.load("mass.iso_labels", true) !== false;

  var params = new URLSearchParams(window.location.search);
  var wanted = params.get("peptide");
  if (wanted) {
    params.delete("peptide");
    var rest = params.toString();
    window.history.replaceState(null, "", window.location.pathname + (rest ? "?" + rest : ""));
    // os links de idioma/tema repetem a query: sem isto, trocar o idioma
    // recarregaria o peptideo salvo por cima do que foi editado
    Array.prototype.forEach.call(document.querySelectorAll(".opcao-idioma, .opcao-modo"), function (a) {
      var url = new URL(a.href, window.location.href);
      url.searchParams.delete("peptide");
      a.href = url.pathname + url.search;
    });
    loadPeptide(wanted);
  } else {
    apply(PM.peptide.get());
    renderRmods();
    calc();
  }
})();
