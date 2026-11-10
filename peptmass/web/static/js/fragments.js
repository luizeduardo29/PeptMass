/* Tela de Fragmentacao MS/MS (a Aba 2 / FragmentTab do desktop): series,
   perdas neutras e cargas recalculam na hora; matching com lista
   experimental; busca rapida; exportacao CSV/Excel/PDF/TXT/Skyline. */
(function () {
  "use strict";
  var PM = window.PM, T = PM.T, el = PM.el, num = PM.num;
  function $(id) { return document.getElementById(id); }

  // Cor por serie (tons medios: leem no claro e no escuro).
  var MAX_LABELS = 400;

  var fragments = [], matched = {}, summary = null;
  var table = $("tab-fragmentos"), chart = $("graf-espectro");

  function options() {
    return {
      ions: PM.checkedValues($("f-ions")),
      losses: PM.checkedValues($("f-perdas")),
      no_loss: $("f-sem-perda").checked,
      charges: PM.checkedValues($("f-cargas")).map(Number)
    };
  }

  function savePrefs() {
    var o = options();
    o.exp = $("f-exp").value; o.tol = $("f-tol").value; o.ppm = $("f-ppm").checked;
    o.labels = $("f-rotulos").checked;
    PM.save("frag.prefs", o);
  }

  function restorePrefs() {
    var o = PM.load("frag.prefs", null);
    if (!o) return;
    function setChecks(box, values) {
      Array.prototype.forEach.call(box.querySelectorAll("input[type=checkbox][value]"), function (cb) {
        cb.checked = values.indexOf(cb.value) >= 0 || values.indexOf(Number(cb.value)) >= 0;
      });
    }
    if (Array.isArray(o.ions)) setChecks($("f-ions"), o.ions);
    if (Array.isArray(o.losses)) setChecks($("f-perdas"), o.losses);
    if (Array.isArray(o.charges)) setChecks($("f-cargas"), o.charges);
    $("f-sem-perda").checked = o.no_loss !== false;
    $("f-exp").value = o.exp || "";
    $("f-tol").value = o.tol || "0.02";
    $("f-ppm").checked = !!o.ppm;
    $("f-rotulos").checked = o.labels !== false;
  }

  function payload(extra) {
    return Object.assign({ peptide: PM.peptide.get() }, options(), extra || {});
  }

  /* ------------------------------------------------------------- calculo */
  function emptyTable(message) {
    var body = table.tBodies[0];
    body.innerHTML = "";
    body.appendChild(el("tr", {}, [el("td", { colspan: "6", class: "vazio", text: message })]));
    $("f-contagem").textContent = "";
  }

  function recalc() {
    savePrefs();
    matched = {};
    $("f-casamentos").innerHTML = "";
    if (!PM.peptide.has()) {
      PM.renderSummary($("peptideo-resumo"), null);
      fragments = [];
      emptyTable(T("peptide.none"));
      PM.emptyChart(chart, T("peptide.none"));
      return;
    }
    PM.api("/api/fragments", { body: payload() }).then(function (res) {
      var box = $("peptideo-resumo");
      if (!res.ok) {
        summary = null;
        box.innerHTML = "";
        box.appendChild(el("div", { class: "notice bad", text: res.error }));
        fragments = [];
        emptyTable(res.error);
        PM.emptyChart(chart, "-");
        return;
      }
      summary = res.peptide;
      PM.renderSummary(box, summary);
      fragments = res.fragments;
      if (res.multi_chain) {
        box.appendChild(el("div", { class: "notice warn", style: "margin-top:12px", text: T("frag.multi_chain") }));
        emptyTable(T("frag.multi_chain"));
        PM.emptyChart(chart, T("frag.multi_chain"));
        return;
      }
      render();
      plot();
    });
  }

  function render() {
    var body = table.tBodies[0];
    body.innerHTML = "";
    if (!fragments.length) { emptyTable(T("frag.none_selected")); return; }
    var frag = document.createDocumentFragment();
    fragments.forEach(function (f) {
      var tr = el("tr", { "data-i": f.i, "data-filtro": (f.ion + " +" + f.z + " " + f.z + "+ " + (f.loss || "")).toLowerCase(),
                          class: matched[f.i] ? "casado" : null }, [
        el("td", { text: f.ion }),
        el("td", { class: "num", "data-v": f.z, text: "+" + f.z }),
        el("td", { class: "num", "data-v": f.mz, text: num(f.mz, 6) }),
        el("td", { text: f.loss || "-" }),
        el("td", { class: "num", "data-v": f.neutral, text: num(f.neutral, 6) }),
        el("td", { class: "mono", text: f.seq })
      ]);
      frag.appendChild(tr);
    });
    body.appendChild(frag);
    filter();
  }

  function filter() {
    var q = $("f-busca").value.trim().toLowerCase(), shown = 0;
    Array.prototype.forEach.call(table.tBodies[0].rows, function (tr) {
      var blob = tr.getAttribute("data-filtro");
      if (blob === null) return;
      var hit = !q || blob.indexOf(q) >= 0;
      tr.hidden = !hit;
      if (hit) shown += 1;
    });
    $("f-contagem").textContent = fragments.length
      ? T("frag.count", { n: shown, total: fragments.length }) : "";
  }

  function plot() {
    var noLoss = fragments.filter(function (f) { return !f.loss; });
    if (!noLoss.length) { PM.emptyChart(chart, T("frag.none_selected")); return; }
    var c = PM.colors(), traces = [], xsAll = [], textsAll = [];
    var showLabels = $("f-rotulos").checked;
    Object.keys(c.ions).forEach(function (s) {
      var list = noLoss.filter(function (f) { return f.type === s; });
      if (!list.length) return;
      var xs = list.map(function (f) { return f.mz; });
      var ys = list.map(function () { return 100; });
      var stick = PM.sticks(xs, ys, c.ions[s], 1.1);
      stick.name = s === "z+1" ? "z•" : s; stick.showlegend = true;
      traces.push(stick);
      traces.push(PM.hoverPoints(xs, ys, list.map(function (f) {
        return "<b>" + f.label + "</b>  " + f.z + "+<br>m/z " + num(f.mz, 4) + "<br>" + f.seq;
      }), c.ions[s]));
      xsAll = xsAll.concat(xs);
      textsAll = textsAll.concat(xs.map(function (x) { return num(x, 4); }));
    });
    var annotations = showLabels && xsAll.length <= MAX_LABELS
      ? PM.labels(xsAll, xsAll.map(function () { return 100; }), textsAll, c.texto, 8.5) : [];
    PM.plot(chart, traces, {
      showlegend: true,
      legend: { orientation: "h", x: 0, y: 1.08, font: { color: c.texto } },
      margin: { l: 58, r: 18, t: 34, b: 46 },
      xaxis: { title: { text: "m/z" } },
      yaxis: { title: { text: T("chart.intensity_rel") }, range: [0, annotations.length ? 165 : 110] },
      annotations: annotations
    });
  }

  /* ------------------------------------------------------------ matching */
  $("f-casar").addEventListener("click", function () {
    savePrefs();
    var out = $("f-casamentos");
    PM.api("/api/fragments", { body: payload({ match: true, exp: $("f-exp").value,
                                               tol: $("f-tol").value, ppm: $("f-ppm").checked }) })
      .then(function (res) {
        out.innerHTML = "";
        if (!res.ok) { out.appendChild(el("div", { class: "notice warn", text: res.error })); return; }
        fragments = res.fragments;
        matched = {};
        (res.matches || []).forEach(function (m) { matched[m.i] = true; });
        render();
        out.appendChild(el("p", { class: "grupo-titulo", text: T("frag.match.summary", { a: res.matches.length, b: res.n_exp }) }));
        if (!res.matches.length) { out.appendChild(el("p", { class: "muted", text: T("common.none") })); return; }
        var body = el("tbody");
        res.matches.forEach(function (m) {
          body.appendChild(el("tr", {}, [
            el("td", { class: "num", text: num(m.exp, 4) }),
            el("td", { text: m.label + " (" + m.z + "+)" }),
            el("td", { class: "num", text: num(m.err, 4, true) + " " + res.unit })
          ]));
        });
        out.appendChild(el("div", { class: "table-wrap baixa" }, [el("table", {}, [
          el("thead", {}, [el("tr", {}, [el("th", { class: "num mz", text: "m/z exp" }),
                                         el("th", { text: T("frag.col.ion") }),
                                         el("th", { class: "num", text: T("ms.col.error") })])]),
          body
        ])]));
      });
  });

  /* ------------------------------------------------------------ exportar */
  Array.prototype.forEach.call(document.querySelectorAll("[data-exportar]"), function (btn) {
    btn.addEventListener("click", function () {
      var fmt = btn.getAttribute("data-exportar");
      var form = new FormData();
      form.append("payload", JSON.stringify(payload()));
      btn.disabled = true;
      fetch("/export/fragments/" + fmt, { method: "POST", body: form,
                                          headers: { "X-CSRF-Token": window.PMBase.csrf } })
        .then(function (resp) {
          var type = resp.headers.get("Content-Type") || "";
          if (!resp.ok || type.indexOf("application/json") === 0) {
            return resp.json().then(function (j) { throw new Error(j.error || resp.status); });
          }
          var disp = resp.headers.get("Content-Disposition") || "";
          var m = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(disp);
          var name = m ? decodeURIComponent(m[1]) : "fragments." + fmt;
          return resp.blob().then(function (blob) {
            var a = el("a", { href: URL.createObjectURL(blob), download: name });
            document.body.appendChild(a); a.click(); a.remove();
            setTimeout(function () { URL.revokeObjectURL(a.href); }, 2000);
          });
        })
        .catch(function (err) { window.alert(T("frag.export.error", { e: err.message })); })
        .then(function () { btn.disabled = false; });
    });
  });

  /* ------------------------------------------------------------- eventos */
  ["f-ions", "f-perdas", "f-cargas"].forEach(function (id) { $(id).addEventListener("change", recalc); });
  $("f-busca").addEventListener("input", filter);
  $("f-rotulos").addEventListener("change", function () { savePrefs(); plot(); });
  ["f-exp", "f-tol", "f-ppm"].forEach(function (id) { $(id).addEventListener("change", savePrefs); });
  PM.onTheme(function () { if (fragments.length) plot(); });

  restorePrefs();
  recalc();
})();
