/* Como usar: demonstracoes interativas. O peptideo desta pagina e' proprio
   (nao mexe no peptideo em edicao das outras telas), e tudo e' calculado pela
   mesma API: /api/mass e /api/fragments. O espectro da secao de tolerancia e'
   simulado aqui, de forma deterministica, para ensinar o efeito da tolerancia. */
(function () {
  "use strict";
  var PM = window.PM, T = PM.T, el = PM.el, num = PM.num;
  function $(id) { return document.getElementById(id); }

  var MAX_ISO_RESIDUES = 130;   // ~15 kDa: abaixo do limite do envelope calculado
  var MAX_ISO_REPEAT = 12;
  var MAX_TOL_LABELS = 24;
  // erros de medida (ppm) dos picos reais simulados: alguns passam de 10 ppm
  var SIM_ERRORS = [2.1, -3.4, 5.0, -1.2, 7.8, -6.5, 0.9, 11.5, -2.7, 4.2, -14.0, 3.3, -0.6, 8.9, -4.8, 1.7];
  var DECOY_PPM = 38;           // ruido perto do ion ausente: casa so com tolerancia larga
  var N_NOISE = 10;

  var peptide = null, mass = null;
  var pairFrags = [], bond = 0;
  var tolFrags = [], simulated = null;
  var requests = { mass: 0, iso: 0, frag: 0, tol: 0 };

  function latest(kind) {
    var id = ++requests[kind];
    return function () { return id === requests[kind]; };
  }

  /* ------------------------------------------------------------- 1. massa */
  function definition(seq) {
    return { sequence: seq, nterm: $("g-acetil").checked ? "Acetyl" : "",
             cterm: $("g-amida").checked ? "Amidation" : "", rmods: [] };
  }

  function calcMass() {
    var current = latest("mass");
    var seq = $("g-seq").value.trim();
    var def = definition(seq);
    var hasMods = !!(def.nterm || def.cterm);
    var calls = [PM.api("/api/mass", { body: { peptide: def, zmin: 1, zmax: 6 } })];
    if (hasMods) {
      calls.push(PM.api("/api/mass", { body: { peptide: { sequence: seq, nterm: "", cterm: "", rmods: [] },
                                               zmin: 1, zmax: 1 } }));
    }
    Promise.all(calls).then(function (rs) {
      if (!current()) return;
      var res = rs[0], err = $("g-massa-erro");
      if (!res.ok || !res.valid) {
        peptide = null; mass = null;
        err.hidden = false;
        err.textContent = T("guide.mass.invalid", { m: res.ok ? res.message : res.error });
        clearAll();
        return;
      }
      err.hidden = true;
      peptide = def; mass = res;
      var r = res.result;
      $("g-mono").textContent = num(r.mono, 6) + " Da";
      $("g-avg").textContent = num(r.avg, 4) + " Da";
      $("g-formula").textContent = r.formula;
      $("g-residuos").textContent = r.n_residues;
      var base = rs[1] && rs[1].ok && rs[1].valid ? rs[1].result.mono : r.mono;
      $("g-delta").textContent = hasMods ? num(r.mono - base, 4, true) + " Da" : T("guide.mass.no_mods");
      var rep = $("g-rep");
      rep.max = Math.max(1, Math.min(MAX_ISO_REPEAT, Math.floor(MAX_ISO_RESIDUES / r.n_residues)));
      if (+rep.value > +rep.max) rep.value = rep.max;
      renderCharge();
      drawIsotopes();
      loadFragments();
      loadTolerance();
    });
  }

  function clearAll() {
    ["g-mono", "g-avg", "g-formula", "g-residuos", "g-delta"].forEach(function (id) { $(id).textContent = "-"; });
    $("g-z-formula").textContent = "-";
    $("g-cargas").innerHTML = "";
    $("g-iso-topo").textContent = "-";
    $("g-sequencia").innerHTML = "";
    $("g-quebra").textContent = T("guide.frag.need");
    $("g-tol-aviso").className = "notice";
    $("g-tol-aviso").textContent = T("guide.frag.need");
    $("g-tab-tol").tBodies[0].innerHTML = "";
    [$("g-graf-iso"), $("g-graf-frag"), $("g-graf-tol")].forEach(function (div) { PM.emptyChart(div, "-"); });
    pairFrags = []; tolFrags = []; simulated = null;
  }

  /* ------------------------------------------------------------- 2. carga */
  function renderCharge() {
    var z = +$("g-z").value;
    $("g-z-valor").textContent = z;
    if (!mass) return;
    var M = mass.result.mono, row = null;
    mass.charges.forEach(function (c) { if (c[0] === z) row = c; });
    var box = $("g-z-formula");
    box.innerHTML = "";
    box.appendChild(el("div", { text: "m/z = (M + z × " + num(PM.proton, 6) + ") / z" }));
    box.appendChild(el("div", {}, [
      "= (" + num(M, 4) + " + " + z + " × " + num(PM.proton, 6) + ") / " + z + " = ",
      el("b", { text: row ? num(row[1], 4) : "-" })
    ]));
    var list = $("g-cargas");
    list.innerHTML = "";
    mass.charges.forEach(function (c) {
      list.appendChild(el("span", { class: c[0] === z ? "on" : null, text: c[0] + "+  " + num(c[1], 4) }));
    });
  }

  /* ---------------------------------------------------------- 3. isotopos */
  function drawIsotopes() {
    if (!mass) return;
    var rep = +$("g-rep").value;
    var current = latest("iso");
    var done = function (dist, mono, residues) {
      if (!current()) return;
      $("g-rep-valor").textContent = T("guide.iso.repeat_value", { n: rep, r: residues, m: num(mono, 0) });
      plotIsotopes(dist, mono);
    };
    if (rep === 1) { done(mass.isotopes, mass.result.mono, mass.result.n_residues); return; }
    var def = Object.assign({}, peptide, { sequence: new Array(rep + 1).join(peptide.sequence) });
    PM.api("/api/mass", { body: { peptide: def, zmin: 1, zmax: 1 } }).then(function (res) {
      if (res.ok && res.valid) done(res.isotopes, res.result.mono, res.result.n_residues);
    });
  }

  function plotIsotopes(dist, mono) {
    var c = PM.colors();
    var top = 0;
    dist.forEach(function (p) { if (p[1] > top) top = p[1]; });
    var labels = dist.map(function (p) {
      var k = Math.round(p[0] - mono);
      return k === 0 ? "M" : "M+" + k;
    });
    var ys = dist.map(function (p) { return 100 * p[1] / (top || 1); });
    var best = ys.indexOf(Math.max.apply(null, ys));
    PM.plot($("g-graf-iso"), [{
      type: "bar", x: labels, y: ys, marker: { color: ys.map(function (_y, i) { return i === best ? c.linha : c.pico; }) },
      text: dist.map(function (p) { return num(p[0], 4) + " Da"; }),
      hovertemplate: "%{x}<br>%{text}<br>%{y:.1f}%<extra></extra>"
    }], {
      xaxis: { title: { text: T("guide.iso.axis") }, type: "category" },
      yaxis: { title: { text: T("chart.intensity_pct") }, range: [0, 110] }
    });
    var k = best;
    $("g-iso-topo").textContent = labels[best] === "M"
      ? T("guide.iso.top_mono") : T("guide.iso.top_other", { k: Math.round(dist[k][0] - mono) });
  }

  /* -------------------------------------------------------- 4. fragmentos */
  function pair() {
    var checked = document.querySelector("input[name=g-par]:checked");
    return (checked ? checked.value : "b,y").split(",");
  }

  function fragmentsOf(ions) {
    return PM.api("/api/fragments", { body: { peptide: peptide, ions: ions, charges: [1],
                                              losses: [], no_loss: true } });
  }

  function loadFragments() {
    if (!peptide) return;
    var current = latest("frag");
    fragmentsOf(pair()).then(function (res) {
      if (!current()) return;
      if (!res.ok || res.multi_chain) {
        pairFrags = [];
        $("g-sequencia").innerHTML = "";
        $("g-quebra").textContent = res.ok ? T("frag.multi_chain") : res.error;
        PM.emptyChart($("g-graf-frag"), "-");
        return;
      }
      pairFrags = res.fragments;
      renderSequence();
    });
  }

  function renderSequence() {
    var codes = mass.codes, n = codes.length;
    var box = $("g-sequencia");
    box.innerHTML = "";
    codes.forEach(function (code, i) {
      if (i > 0) {
        var cut = i;
        box.appendChild(el("button", {
          type: "button", class: "ligacao", "data-i": cut,
          "aria-label": T("guide.frag.cut", { a: codes[i - 1], b: code }),
          onmouseenter: function () { selectBond(cut); },
          onfocus: function () { selectBond(cut); },
          onclick: function () { selectBond(cut); }
        }));
      }
      box.appendChild(el("span", { class: "residuo", text: code }));
    });
    selectBond(Math.min(Math.max(1, bond || Math.floor(n / 2)), n - 1));
  }

  function selectBond(i) {
    if (!mass) return;
    var codes = mass.codes, n = codes.length;
    if (n < 2) { $("g-quebra").textContent = T("guide.frag.need"); return; }
    bond = i;
    var types = pair(), c = PM.colors();
    var box = $("g-sequencia");
    box.style.setProperty("--cor-n", c.ions[types[0]]);
    box.style.setProperty("--cor-c", c.ions[types[1]]);
    Array.prototype.forEach.call(box.querySelectorAll(".residuo"), function (r, k) {
      r.className = "residuo " + (k < i ? "n" : "c");
    });
    Array.prototype.forEach.call(box.querySelectorAll(".ligacao"), function (b) {
      b.classList.toggle("on", +b.getAttribute("data-i") === i);
    });
    var nFrag = findFrag(types[0], i), cFrag = findFrag(types[1], n - i);
    var out = $("g-quebra");
    out.innerHTML = "";
    out.appendChild(el("span", { class: "muted", text: T("guide.frag.cut", { a: codes[i - 1], b: codes[i] }) }));
    [[nFrag, codes.slice(0, i), types[0]], [cFrag, codes.slice(i), types[1]]].forEach(function (item) {
      if (!item[0]) return;
      out.appendChild(el("span", {}, [
        el("span", { class: "ion", style: "color:" + c.ions[item[2]], text: item[0].ion }),
        " = " + num(item[0].mz, 4) + " m/z  ",
        el("span", { class: "mono muted", text: "(" + item[1].join("") + ")" })
      ]));
    });
    plotFragments(types, [nFrag, cFrag]);
  }

  function findFrag(type, number) {
    var name = type + number;
    for (var k = 0; k < pairFrags.length; k++) if (pairFrags[k].ion === name) return pairFrags[k];
    return null;
  }

  function plotFragments(types, chosen) {
    var c = PM.colors(), traces = [];
    types.forEach(function (t) {
      var list = pairFrags.filter(function (f) { return f.type === t; });
      if (!list.length) return;
      var xs = list.map(function (f) { return f.mz; });
      var ys = list.map(function (f) { return chosen.indexOf(f) >= 0 ? 100 : 45; });
      var s = PM.sticks(xs, ys, c.ions[t], 1.6);
      s.name = t; s.showlegend = true;
      traces.push(s);
      traces.push(PM.hoverPoints(xs, ys, list.map(function (f) {
        return "<b>" + f.ion + "</b><br>m/z " + num(f.mz, 4) + "<br>" + f.seq;
      }), c.ions[t]));
    });
    var picked = chosen.filter(Boolean);
    PM.plot($("g-graf-frag"), traces, {
      showlegend: true,
      legend: { orientation: "h", x: 0, y: 1.12, font: { color: c.texto }, itemclick: false, itemdoubleclick: false },
      margin: { l: 58, r: 18, t: 34, b: 46 },
      xaxis: { title: { text: "m/z" } },
      yaxis: { title: { text: T("chart.intensity_rel") }, range: [0, 135], showticklabels: false },
      annotations: PM.labels(picked.map(function (f) { return f.mz; }), picked.map(function () { return 100; }),
                             picked.map(function (f) { return f.ion; }), c.texto, 11)
    });
  }

  /* -------------------------------------------------------- 5. tolerancia */
  function loadTolerance() {
    if (!peptide) return;
    var current = latest("tol");
    fragmentsOf(["b", "y"]).then(function (res) {
      if (!current()) return;
      tolFrags = res.ok && !res.multi_chain ? res.fragments.slice().sort(function (a, b) { return a.mz - b.mz; }) : [];
      simulated = tolFrags.length ? simulate(tolFrags) : null;
      renderTolerance();
    });
  }

  // gerador deterministico: o mesmo peptideo da sempre o mesmo espectro
  function seeded(seed) {
    var s = seed % 2147483647 || 1;
    return function () { s = s * 16807 % 2147483647; return (s - 1) / 2147483646; };
  }

  function simulate(frags) {
    var rand = seeded(frags.length * 7919 + Math.round(frags[0].mz * 1000));
    var missing = Math.floor(frags.length / 2);
    var peaks = [];
    frags.forEach(function (f, k) {
      if (k === missing) return;
      var err = SIM_ERRORS[k % SIM_ERRORS.length];
      peaks.push({ mz: f.mz * (1 + err * 1e-6), rel: 30 + 70 * rand(), kind: "real" });
    });
    var decoy = frags[missing];
    peaks.push({ mz: decoy.mz * (1 + DECOY_PPM * 1e-6), rel: 12 + 10 * rand(), kind: "decoy" });
    var lo = frags[0].mz - 40, hi = frags[frags.length - 1].mz + 40;
    for (var k = 0; k < N_NOISE; k++) {
      var mz = lo + (hi - lo) * (k + 0.5) / N_NOISE + 3.37;
      var clash = frags.some(function (f) { return Math.abs(f.mz - mz) < 0.5; });
      if (!clash) peaks.push({ mz: mz, rel: 5 + 20 * rand(), kind: "noise" });
    }
    return { peaks: peaks, missing: missing };
  }

  function renderTolerance() {
    var tol = +$("g-tol").value;
    $("g-tol-valor").textContent = tol;
    var body = $("g-tab-tol").tBodies[0];
    body.innerHTML = "";
    if (!simulated) { PM.emptyChart($("g-graf-tol"), "-"); return; }
    var c = PM.colors(), rows = [], matchedPeaks = [], missedReal = 0, falseHit = null;
    tolFrags.forEach(function (f) {
      var best = null;
      simulated.peaks.forEach(function (p) {
        if (!best || Math.abs(p.mz - f.mz) < Math.abs(best.mz - f.mz)) best = p;
      });
      var err = (best.mz - f.mz) / f.mz * 1e6;
      var hit = Math.abs(err) <= tol;
      var state = hit ? (best.kind === "real" ? "yes" : "chance") : "no";
      var close = Math.abs(err) < 100;   // so mostra o pico mais proximo se fizer sentido
      if (hit) matchedPeaks.push({ peak: best, frag: f });
      if (!hit && best.kind === "real") missedReal += 1;
      if (state === "chance") falseHit = f;
      rows.push(el("tr", { class: hit ? "casado" : null }, [
        el("td", { text: f.ion }),
        el("td", { class: "num", text: num(f.mz, 4) }),
        el("td", { class: "num", text: close ? num(best.mz, 4) : "-" }),
        el("td", { class: "num", text: close ? num(err, 1, true) : "-" }),
        el("td", {}, [el("span", { class: "tag " + { yes: "ok", no: "bad", chance: "warn" }[state],
                                   text: T("guide.tol." + state) })])
      ]));
    });
    rows.forEach(function (r) { body.appendChild(r); });

    var notice = $("g-tol-aviso");
    var count = T("guide.tol.count", { n: matchedPeaks.length, t: tolFrags.length }) + ". ";
    if (falseHit) {
      notice.className = "notice bad";
      notice.textContent = count + T("guide.tol.loose", { ion: falseHit.ion });
    } else if (missedReal) {
      notice.className = "notice warn";
      notice.textContent = count + T("guide.tol.tight", { n: missedReal });
    } else {
      notice.className = "notice ok";
      notice.textContent = count + T("guide.tol.good");
    }

    var all = simulated.peaks;
    var traces = [PM.sticks(all.map(function (p) { return p.mz; }), all.map(function (p) { return p.rel; }), c.pico, 1)];
    traces[0].showlegend = false;
    ["b", "y"].forEach(function (t) {
      var list = matchedPeaks.filter(function (m) { return m.frag.type === t; });
      if (!list.length) return;
      var xs = list.map(function (m) { return m.peak.mz; }), ys = list.map(function (m) { return m.peak.rel; });
      var s = PM.sticks(xs, ys, c.ions[t], 1.8);
      s.name = t; s.showlegend = true;
      traces.push(s);
      traces.push(PM.hoverPoints(xs, ys, list.map(function (m) {
        return "<b>" + m.frag.ion + "</b><br>exp " + num(m.peak.mz, 4) + "<br>" +
               num((m.peak.mz - m.frag.mz) / m.frag.mz * 1e6, 1, true) + " ppm";
      }), c.ions[t]));
    });
    var labeled = matchedPeaks.length <= MAX_TOL_LABELS ? matchedPeaks : [];
    PM.plot($("g-graf-tol"), traces, {
      showlegend: true,
      legend: { orientation: "h", x: 0, y: 1.12, font: { color: c.texto }, itemclick: false, itemdoubleclick: false },
      margin: { l: 58, r: 18, t: 34, b: 46 },
      xaxis: { title: { text: "m/z" }, showgrid: false },
      yaxis: { title: { text: T("chart.intensity_pct") }, range: [0, 130], tickvals: [0, 20, 40, 60, 80, 100], showgrid: false },
      annotations: labeled.reduce(function (out, m) {
        return out.concat(PM.labels([m.peak.mz], [m.peak.rel], [m.frag.ion], c.ions[m.frag.type], 10));
      }, [])
    });
  }

  /* ------------------------------------------------------ 6. experimental */
  $("g-abrir-exemplo").addEventListener("click", function () {
    PM.peptide.set({ sequence: "PEPTIDE", nterm: "", cterm: "", rmods: [] });
    window.location.href = window.PEPTMASS_EXEMPLO;
  });

  /* --------------------------------------------------------- glossario */
  $("g-busca").addEventListener("input", function () {
    var q = this.value.trim().toLowerCase(), shown = 0;
    Array.prototype.forEach.call(document.querySelectorAll("[data-termo]"), function (item) {
      var hit = !q || item.textContent.toLowerCase().indexOf(q) >= 0;
      item.hidden = !hit;
      if (hit) shown += 1;
    });
    $("g-busca-vazio").hidden = shown > 0;
  });

  /* ------------------------------------------------------------- eventos */
  $("g-seq").addEventListener("input", PM.debounce(calcMass, 250));
  ["g-acetil", "g-amida"].forEach(function (id) { $(id).addEventListener("change", calcMass); });
  Array.prototype.forEach.call(document.querySelectorAll("[data-seq]"), function (b) {
    b.addEventListener("click", function () { $("g-seq").value = b.getAttribute("data-seq"); bond = 0; calcMass(); });
  });
  $("g-z").addEventListener("input", renderCharge);
  $("g-rep").addEventListener("input", PM.debounce(drawIsotopes, 120));
  Array.prototype.forEach.call(document.querySelectorAll("input[name=g-par]"), function (r) {
    r.addEventListener("change", loadFragments);
  });
  $("g-tol").addEventListener("input", renderTolerance);
  PM.onTheme(function () {
    if (!mass) return;
    drawIsotopes();
    if (pairFrags.length) selectBond(bond);
    renderTolerance();
  });

  calcMass();
})();
