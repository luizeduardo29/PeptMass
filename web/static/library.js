/* Biblioteca: aminoacidos nao-naturais, modificacoes e PubChem. Cada
   alteracao recarrega a pagina (as tabelas sao do servidor) e o aviso de
   sucesso sobrevive ao recarregamento pelo sessionStorage. */
(function () {
  "use strict";
  var PM = window.PM, T = PM.T;
  function $(id) { return document.getElementById(id); }

  function flash(message) {
    try { window.sessionStorage.setItem("peptmass.flash", message); } catch (e) { /* sem storage */ }
    window.location.reload();
  }
  try {
    var pending = window.sessionStorage.getItem("peptmass.flash");
    if (pending) {
      window.sessionStorage.removeItem("peptmass.flash");
      $("lib-aviso").textContent = pending;
      $("lib-aviso").hidden = false;
    }
  } catch (e) { /* sem storage */ }

  function fail(message) {
    var box = $("lib-aviso");
    box.className = "notice bad";
    box.textContent = message;
    box.hidden = false;
    box.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  $("btn-novo-residuo").addEventListener("click", function () {
    PM.residueDialog().then(function (code) {
      if (code) flash(T("library.residue.added", { c: code }));
    });
  });

  $("btn-nova-mod").addEventListener("click", function () {
    PM.modDialog().then(function (name) {
      if (name) flash(T("library.mod.added", { n: name }));
    });
  });

  // Como o "🔍 PubChem" da barra do desktop: busca e abre o cadastro de
  // aminoacido ja com a formula e o nome.
  $("btn-pubchem").addEventListener("click", function () {
    PM.pubchemDialog("").then(function (c) {
      if (!c) return;
      PM.residueDialog({ formula: c.formula, name: c.iupac || c.name || "" }).then(function (code) {
        if (code) flash(T("library.residue.from_pubchem", { c: code }));
      });
    });
  });

  document.addEventListener("click", function (event) {
    var t = event.target && event.target.closest ? event.target : null;
    if (!t) return;
    var res = t.closest("[data-remover-residuo]");
    if (res) {
      var code = res.getAttribute("data-remover-residuo");
      if (!window.confirm(T("library.residue.confirm_remove", { c: code }))) return;
      PM.api("/api/residues/" + encodeURIComponent(code), { method: "DELETE" }).then(function (r) {
        if (r.ok) flash(T("library.residue.removed", { c: code })); else fail(r.error);
      });
      return;
    }
    var mod = t.closest("[data-remover-mod]");
    if (mod) {
      var name = mod.getAttribute("data-remover-mod");
      if (!window.confirm(T("library.mod.confirm_remove", { n: name }))) return;
      PM.api("/api/modifications?name=" + encodeURIComponent(name), { method: "DELETE" }).then(function (r) {
        if (r.ok) flash(T("library.mod.removed", { n: name })); else fail(r.error);
      });
    }
  });
})();
