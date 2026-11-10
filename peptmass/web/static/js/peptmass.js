/* PeptMass: o que as telas compartilham.
 *
 *  - PM.peptide: o peptideo em edicao (sequencia + mods), guardado no
 *    navegador. A tela de Massa grava; Fragmentacao e Dados experimentais
 *    leem - como o AppState.last_mass_result do desktop.
 *  - PM.plot: graficos Plotly nas cores dos tokens do tema (redesenham ao
 *    trocar claro/escuro), com picos em bastao como o matplotlib do desktop.
 *  - PM.residueDialog / PM.modDialog / PM.pubchemDialog: as janelas de
 *    cadastro e a busca no PubChem.
 */
(function () {
  "use strict";
  var B = window.PMBase, T = B.T, el = B.el, num = B.num;
  var PROTON = (window.PEPTMASS && window.PEPTMASS.proton) || 1.007276466812;

  /* ---------------------------------------------------- armazenamento local */
  function load(key, fallback) {
    try {
      var raw = window.localStorage.getItem("peptmass." + key);
      return raw === null ? fallback : JSON.parse(raw);
    } catch (e) { return fallback; }
  }
  function save(key, value) {
    try { window.localStorage.setItem("peptmass." + key, JSON.stringify(value)); } catch (e) { /* sem storage */ }
  }

  var peptide = {
    get: function () {
      var p = load("peptide", null);
      if (!p || typeof p !== "object") return { sequence: "", nterm: "", cterm: "", rmods: [] };
      return { sequence: String(p.sequence || ""), nterm: String(p.nterm || ""),
               cterm: String(p.cterm || ""), rmods: Array.isArray(p.rmods) ? p.rmods : [] };
    },
    set: function (p) { save("peptide", p); },
    has: function () { return !!peptide.get().sequence.trim(); }
  };

  /* Resumo do peptideo (as telas 2 e 3): sequencia, mods e massa. */
  function renderSummary(box, summary) {
    box.innerHTML = "";
    if (!summary) { box.appendChild(el("p", { class: "muted", text: T("peptide.none") })); return; }
    var mods = [];
    if (summary.nterm) mods.push("N-term: " + summary.nterm);
    if (summary.cterm) mods.push("C-term: " + summary.cterm);
    box.appendChild(el("p", { class: "mono", style: "margin:0 0 8px;overflow-wrap:anywhere;font-weight:600", text: summary.sequence }));
    var kv = el("dl", { class: "kv", style: "margin:0" }, [
      el("dt", { text: T("mass.res.mono") }), el("dd", { text: num(summary.mono, 6) + " Da" }),
      el("dt", { text: T("mass.res.formula") }), el("dd", { class: "mono", text: summary.formula })
    ]);
    if (mods.length) {
      kv.appendChild(el("dt", { text: T("mass.mods.title") }));
      kv.appendChild(el("dd", { text: mods.join(" · ") }));
    }
    box.appendChild(kv);
  }

  /* ---------------------------------------------------------------- graficos */
  function token(name) {
    return getComputedStyle(document.documentElement).getPropertyValue("--" + name).trim();
  }
  function colors() {
    return {
      fundo: token("grafico-fundo") || token("superficie"), grade: token("grafico-grade"),
      eixo: token("grafico-eixo"), texto: token("grafico-texto"), forte: token("texto"),
      linha: token("grafico-linha"), xic: token("grafico-xic"),
      c: token("grafico-c"), pico: token("grafico-pico"),
      dica: token("grafico-dica-fundo"), fonte: token("fonte"),
      ions: { a: token("ion-a"), b: token("ion-b"), c: token("ion-c"), x: token("ion-x"),
              y: token("ion-y"), z: token("ion-z"), "z+1": token("ion-z") }
    };
  }
  function axis(c, extra) {
    return Object.assign({ gridcolor: c.grade, linecolor: c.eixo, zerolinecolor: c.eixo,
                           tickcolor: c.eixo, ticks: "outside", showline: true, automargin: true,
                           title: { font: { size: 12, color: c.texto } } }, extra || {});
  }
  function layout(extra) {
    var c = colors();
    extra = extra || {};
    var out = {
      paper_bgcolor: c.fundo, plot_bgcolor: c.fundo,
      font: { family: c.fonte, size: 11.5, color: c.texto },
      margin: { l: 58, r: 18, t: 18, b: 46 },
      showlegend: false, hovermode: "closest", dragmode: "zoom",
      hoverlabel: { bgcolor: c.dica, bordercolor: c.eixo, font: { color: c.forte, size: 12 } }
    };
    Object.keys(extra).forEach(function (k) {
      if (k === "xaxis" || k === "yaxis") out[k] = axis(c, extra[k]);
      else out[k] = extra[k];
    });
    if (!out.xaxis) out.xaxis = axis(c);
    if (!out.yaxis) out.yaxis = axis(c);
    return out;
  }
  var CONFIG = { responsive: true, displaylogo: false,
                 modeBarButtonsToRemove: ["select2d", "lasso2d", "autoScale2d"],
                 toImageButtonOptions: { format: "png", filename: "peptmass", scale: 2 } };

  function plot(div, traces, extra) {
    if (!window.Plotly || !div) return;
    var empty = div.querySelector(".grafico-vazio");
    if (empty) div.innerHTML = "";
    window.Plotly.react(div, traces, layout(extra), CONFIG);
  }
  function emptyChart(div, message) {
    if (!div) return;
    if (window.Plotly && div.classList.contains("js-plotly-plot")) window.Plotly.purge(div);
    div.innerHTML = "";
    div.appendChild(el("div", { class: "grafico-vazio", text: message || "-" }));
  }

  /* Picos em bastao: um unico traco de linhas com quebras (null), leve mesmo
     com milhares de picos; o hover fica num traco de marcadores invisiveis. */
  function sticks(xs, ys, color, width) {
    var x = [], y = [];
    for (var i = 0; i < xs.length; i++) { x.push(xs[i], xs[i], null); y.push(0, ys[i], null); }
    return { type: "scatter", mode: "lines", x: x, y: y, hoverinfo: "skip",
             line: { color: color, width: width || 1.2 } };
  }
  function hoverPoints(xs, ys, texts, color) {
    return { type: "scatter", mode: "markers", x: xs, y: ys, text: texts, showlegend: false,
             hovertemplate: "%{text}<extra></extra>",
             marker: { size: 9, color: color, opacity: 0 } };
  }
  function labels(xs, ys, texts, color, size) {
    var out = [];
    for (var i = 0; i < xs.length; i++) {
      out.push({ x: xs[i], y: ys[i], text: texts[i], showarrow: false, textangle: -90,
                 xanchor: "center", yanchor: "bottom", yshift: 3,
                 font: { size: size || 9, color: color } });
    }
    return out;
  }

  var themeHandlers = [];
  function onTheme(fn) { themeHandlers.push(fn); }
  document.addEventListener("peptmass:tema", function () {
    themeHandlers.forEach(function (fn) { try { fn(); } catch (e) { /* proximo */ } });
  });

  /* --------------------------------------------------------------- janelas */
  function byId(id) { return document.getElementById(id); }
  function debounce(fn, ms) {
    var t = null;
    return function () {
      var args = arguments, self = this;
      clearTimeout(t);
      t = setTimeout(function () { fn.apply(self, args); }, ms);
    };
  }

  /* Busca no PubChem. Resolve com o composto (ou null se cancelar). */
  function pubchemDialog(initial) {
    var dlg = byId("dlg-pubchem");
    if (!dlg) return Promise.resolve(null);
    var query = byId("pubchem-termo"), kind = byId("pubchem-tipo"), status = byId("pubchem-estado");
    var useBtn = byId("pubchem-usar"), searchBtn = byId("pubchem-buscar"), img = byId("pubchem-img");
    var found = null;
    query.value = initial || "";
    useBtn.disabled = true;
    img.innerHTML = "";
    ["pubchem-iupac", "pubchem-cid", "pubchem-formula", "pubchem-mono", "pubchem-mono-pc", "pubchem-media"]
      .forEach(function (id) { byId(id).textContent = "-"; });
    B.setState(status, T("dlg.pubchem.hint"));

    function search() {
      var q = query.value.trim();
      if (!q) return;
      searchBtn.disabled = true; useBtn.disabled = true;
      B.setState(status, T("dlg.pubchem.searching"));
      img.innerHTML = "";
      B.api("/api/pubchem", { body: { kind: kind.value, query: q } }).then(function (res) {
        searchBtn.disabled = false;
        if (!res.ok) { B.setState(status, "✗ " + res.error, "bad"); return; }
        found = res.compound;
        byId("pubchem-iupac").textContent = found.iupac || "-";
        byId("pubchem-cid").textContent = found.cid;
        byId("pubchem-formula").textContent = found.formula;
        byId("pubchem-mono").textContent = num(found.mono, 6) + " Da";
        byId("pubchem-mono-pc").textContent = found.pubchem_mono ? num(found.pubchem_mono, 6) + " Da" : "-";
        byId("pubchem-media").textContent = num(found.avg, 4) + " Da";
        if (found.cid) img.appendChild(el("img", { src: "/api/pubchem/" + found.cid + ".png", alt: found.iupac || "" }));
        B.setState(status, "✓ " + T("dlg.pubchem.found"), "ok");
        useBtn.disabled = false;
      });
    }
    searchBtn.onclick = search;
    query.onkeydown = function (e) { if (e.key === "Enter") { e.preventDefault(); search(); } };

    return new Promise(function (resolve) {
      var result = null;
      useBtn.onclick = function () { result = found; dlg.close(); };
      dlg.addEventListener("close", function handler() {
        dlg.removeEventListener("close", handler);
        resolve(result);
      });
      dlg.showModal();
      query.focus();
    });
  }

  function formulaPreview(input, out, mode, emptyKey, okKey, invalidKey) {
    var run = debounce(function () {
      var f = input.value.trim();
      if (!f) { out.textContent = T(emptyKey); return; }
      B.api("/api/formula", { body: { formula: f, mode: mode } }).then(function (res) {
        out.textContent = res.ok ? T(okKey, { m: num(res.mono, 6, mode === "delta") })
                                 : T(invalidKey);
      });
    }, 200);
    input.oninput = run;
    run();
  }

  /* Novo aminoacido personalizado. opts: {code, lockCode, title, name, formula}.
     Resolve com o codigo salvo (ou null). */
  function residueDialog(opts) {
    opts = opts || {};
    var dlg = byId("dlg-residuo");
    var name = byId("residuo-nome"), three = byId("residuo-abrev"), code = byId("residuo-codigo");
    var formula = byId("residuo-formula"), err = byId("residuo-erro");
    byId("residuo-titulo").textContent = opts.title || T("dlg.residue.title");
    name.value = opts.name || ""; three.value = opts.three || "";
    code.value = opts.code || ""; code.readOnly = !!opts.lockCode;
    formula.value = opts.formula || "";
    B.setState(err, "");
    formulaPreview(formula, byId("residuo-previa"), "residue", "dlg.residue.preview_empty",
                   "dlg.residue.preview", "dlg.residue.preview_invalid");
    byId("residuo-pubchem").onclick = function () {
      pubchemDialog(name.value.trim()).then(function (c) {
        if (!c) return;
        formula.value = c.formula;
        if (!name.value.trim()) name.value = c.iupac || c.name || "";
        formula.oninput();
      });
    };
    return new Promise(function (resolve) {
      var saved = null;
      byId("residuo-ok").onclick = function () {
        B.api("/api/residues", { body: { name: name.value, three: three.value,
                                         code: code.value, formula: formula.value } }).then(function (res) {
          if (!res.ok) { B.setState(err, res.error, "bad"); return; }
          saved = code.value.trim();
          dlg.close();
        });
      };
      dlg.addEventListener("close", function handler() {
        dlg.removeEventListener("close", handler);
        resolve(saved);
      });
      dlg.showModal();
      (opts.lockCode ? name : code).focus();
    });
  }

  /* Nova modificacao customizada. Resolve com o nome salvo (ou null). */
  function modDialog() {
    var dlg = byId("dlg-mod");
    var name = byId("mod-nome"), formula = byId("mod-formula"), pos = byId("mod-posicao");
    var targets = byId("mod-alvos"), err = byId("mod-erro");
    name.value = ""; formula.value = ""; pos.value = "residue"; targets.value = "";
    B.setState(err, "");
    formulaPreview(formula, byId("mod-previa"), "delta", "dlg.mod.preview_empty",
                   "dlg.mod.preview", "dlg.mod.preview_invalid");
    byId("mod-pubchem").onclick = function () {
      pubchemDialog(name.value.trim()).then(function (c) {
        if (!c) return;
        formula.value = c.formula;
        if (!name.value.trim()) name.value = c.iupac || c.name || "";
        formula.oninput();
      });
    };
    return new Promise(function (resolve) {
      var saved = null;
      byId("mod-ok").onclick = function () {
        B.api("/api/modifications", { body: { name: name.value, formula: formula.value,
                                              position: pos.value, targets: targets.value } }).then(function (res) {
          if (!res.ok) { B.setState(err, res.error, "bad"); return; }
          saved = name.value.trim();
          dlg.close();
        });
      };
      dlg.addEventListener("close", function handler() {
        dlg.removeEventListener("close", handler);
        resolve(saved);
      });
      dlg.showModal();
      name.focus();
    });
  }

  function checkedValues(container) {
    return Array.prototype.filter.call(container.querySelectorAll("input[type=checkbox][value]"),
      function (cb) { return cb.checked; }).map(function (cb) { return cb.value; });
  }

  window.PM = {
    T: T, el: el, num: num, api: B.api, setState: B.setState, proton: PROTON,
    load: load, save: save, peptide: peptide, renderSummary: renderSummary,
    colors: colors, plot: plot, emptyChart: emptyChart, sticks: sticks,
    hoverPoints: hoverPoints, labels: labels, onTheme: onTheme,
    debounce: debounce, checkedValues: checkedValues,
    pubchemDialog: pubchemDialog, residueDialog: residueDialog, modDialog: modDialog
  };
})();
