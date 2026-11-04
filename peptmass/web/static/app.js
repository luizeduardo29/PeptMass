/* Base do lado do navegador (o app.js da Hub): traducao, CSRF, menu de
   preferencias, modo de cor na hora e os componentes de tabela (ordenar,
   buscar, copiar). O catalogo vem inteiro do servidor - nenhuma string de
   interface fica no JS. */
(function () {
  "use strict";

  var node = document.getElementById("i18n-catalog");
  var CATALOG = {};
  try { CATALOG = node ? JSON.parse(node.textContent) : {}; } catch (e) { CATALOG = {}; }

  function T(key, params) {
    var text = Object.prototype.hasOwnProperty.call(CATALOG, key) ? CATALOG[key] : key;
    if (params) {
      Object.keys(params).forEach(function (name) {
        text = text.split("{" + name + "}").join(String(params[name]));
      });
    }
    return text;
  }

  /* ---- CSRF: o token da pagina vai em todo pedido que muda estado -------- */
  var metaToken = document.querySelector('meta[name="csrf-token"]');
  var CSRF = metaToken ? metaToken.getAttribute("content") : "";

  function api(url, options) {
    options = options || {};
    var init = { method: options.method || (options.body !== undefined || options.form ? "POST" : "GET"),
                 headers: { Accept: "application/json" } };
    if (init.method !== "GET") init.headers["X-CSRF-Token"] = CSRF;
    if (options.form) {
      init.body = options.form;
    } else if (options.body !== undefined) {
      init.headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(options.body);
    }
    return fetch(url, init).then(function (response) {
      return response.json().catch(function () {
        return { ok: false, error: T("error.http", { status: response.status }) };
      });
    }, function () {
      return { ok: false, error: T("error.network") };
    });
  }

  /* ---- Menu de preferencias: fecha ao clicar fora ou com Esc ------------- */
  function closeMenus(except) {
    Array.prototype.forEach.call(document.querySelectorAll("details.seletor-idioma[open]"), function (menu) {
      if (menu !== except) menu.removeAttribute("open");
    });
  }
  document.addEventListener("click", function (event) {
    var t = event.target;
    closeMenus(t && t.closest ? t.closest("details.seletor-idioma") : null);
  });
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") closeMenus(null);
  });

  /* ---- Modo de cor (claro / escuro) --------------------------------------
     Sem JavaScript o link ?tema= recarrega e o servidor grava o cookie. Com
     ele a troca e na hora (nada digitado se perde) e os graficos redesenham. */
  var THEME_COOKIE = "peptmass_tema";
  document.addEventListener("click", function (event) {
    var t = event.target;
    var option = t && t.closest ? t.closest("[data-tema-opcao]") : null;
    if (!option) return;
    event.preventDefault();
    var name = option.getAttribute("data-tema-opcao");
    document.documentElement.setAttribute("data-tema", name);
    document.cookie = THEME_COOKIE + "=" + name + "; path=/; max-age=31536000; samesite=lax";
    Array.prototype.forEach.call(document.querySelectorAll("[data-tema-opcao]"), function (other) {
      var active = other.getAttribute("data-tema-opcao") === name;
      other.classList.toggle("ativa", active);
      if (active) other.setAttribute("aria-current", "true"); else other.removeAttribute("aria-current");
    });
    document.dispatchEvent(new CustomEvent("peptmass:tema", { detail: name }));
  });

  /* ---- Tabelas: ordenar por coluna (th[data-sort]) ------------------------
     Celulas numericas podem trazer o valor bruto em data-v; senao o texto. */
  function cellValue(cell, kind) {
    if (!cell) return kind === "num" ? -Infinity : "";
    var raw = cell.hasAttribute("data-v") ? cell.getAttribute("data-v") : cell.textContent.trim();
    if (kind === "num") {
      var n = parseFloat(String(raw).replace(/[^0-9eE.+-]/g, ""));
      return isFinite(n) ? n : -Infinity;
    }
    return String(raw).toLowerCase();
  }
  document.addEventListener("click", function (event) {
    var th = event.target && event.target.closest ? event.target.closest("th[data-sort]") : null;
    if (!th) return;
    var table = th.closest("table");
    var tbody = table && table.tBodies[0];
    if (!tbody) return;
    var index = Array.prototype.indexOf.call(th.parentNode.children, th);
    var kind = th.getAttribute("data-sort");
    var asc = th.getAttribute("aria-sort") !== "ascending";
    Array.prototype.forEach.call(th.parentNode.children, function (other) { other.removeAttribute("aria-sort"); });
    th.setAttribute("aria-sort", asc ? "ascending" : "descending");
    var rows = Array.prototype.filter.call(tbody.rows, function (r) { return !r.querySelector(".vazio"); });
    rows.sort(function (a, b) {
      var va = cellValue(a.cells[index], kind), vb = cellValue(b.cells[index], kind);
      if (va < vb) return asc ? -1 : 1;
      if (va > vb) return asc ? 1 : -1;
      return 0;
    });
    rows.forEach(function (r) { tbody.appendChild(r); });
  });

  /* ---- Tabelas: copiar (button[data-copiar="id"]) - texto com tabulacao,
     cola direto em planilha. So as linhas visiveis (respeita a busca). */
  function tableText(table) {
    var lines = [];
    Array.prototype.forEach.call(table.rows, function (row) {
      if (row.hidden || row.querySelector(".vazio")) return;
      var cells = Array.prototype.map.call(row.cells, function (c) { return c.textContent.trim(); });
      while (cells.length && cells[cells.length - 1] === "") cells.pop();
      lines.push(cells.join("\t"));
    });
    return lines.join("\n");
  }
  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) return navigator.clipboard.writeText(text);
    var area = document.createElement("textarea");
    area.value = text; area.style.position = "fixed"; area.style.opacity = "0";
    document.body.appendChild(area); area.select();
    try { document.execCommand("copy"); } catch (e) { /* sem area de transferencia */ }
    document.body.removeChild(area);
    return Promise.resolve();
  }
  document.addEventListener("click", function (event) {
    var btn = event.target && event.target.closest ? event.target.closest("[data-copiar]") : null;
    if (!btn) return;
    var table = document.getElementById(btn.getAttribute("data-copiar"));
    if (!table) return;
    copyText(tableText(table)).then(function () {
      var old = btn.getAttribute("data-rotulo") || btn.innerHTML;
      btn.setAttribute("data-rotulo", old);
      btn.textContent = T("common.copied");
      setTimeout(function () { btn.innerHTML = old; }, 1300);
    });
  });

  /* ---- Busca em lista: input[data-busca="id"] filtra [data-busca-nome] ---- */
  function applySearch(input) {
    var id = input.getAttribute("data-busca");
    var target = document.getElementById(id);
    if (!target) return;
    var q = String(input.value || "").trim().toLowerCase(), shown = 0;
    Array.prototype.forEach.call(target.querySelectorAll("[data-busca-nome]"), function (item) {
      var hit = !q || item.getAttribute("data-busca-nome").toLowerCase().indexOf(q) >= 0;
      item.hidden = !hit;
      if (hit) shown += 1;
    });
    var empty = document.querySelector('[data-busca-vazio="' + id + '"]');
    if (empty) empty.hidden = !(q && shown === 0);
  }
  document.addEventListener("input", function (event) {
    var t = event.target;
    if (t && t.getAttribute && t.getAttribute("data-busca")) applySearch(t);
  });

  /* ---- Janelas: [data-fechar] fecha o <dialog> em que esta --------------- */
  document.addEventListener("click", function (event) {
    var closer = event.target && event.target.closest ? event.target.closest("[data-fechar]") : null;
    if (!closer) return;
    var dialog = closer.closest("dialog");
    if (dialog) { event.preventDefault(); dialog.close(); }
  });

  /* ---- Atalhos de DOM e de numero --------------------------------------- */
  function el(tag, attrs, children) {
    var n = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (key) {
      var v = attrs[key];
      if (v === null || v === undefined || v === false) return;
      if (key === "text") n.textContent = v;
      else if (key === "class") n.className = v;
      else if (key.slice(0, 2) === "on") n.addEventListener(key.slice(2), v);
      else n.setAttribute(key, v === true ? "" : v);
    });
    (children || []).forEach(function (child) {
      if (child === null || child === undefined) return;
      n.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
    });
    return n;
  }

  function num(value, digits, signed) {
    if (value === null || value === undefined || value === "") return "-";
    var n = Number(value);
    if (!isFinite(n)) return String(value);
    var s = n.toFixed(digits === undefined ? 4 : digits);
    return signed && n >= 0 ? "+" + s : s;
  }

  function setState(node, text, kind) {
    if (!node) return;
    node.className = "estado" + (kind ? " " + kind : "");
    node.textContent = text || "";
  }

  window.PMBase = { T: T, api: api, el: el, num: num, setState: setState,
                    copyText: copyText, csrf: CSRF, catalog: CATALOG };
})();
