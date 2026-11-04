#!/usr/bin/env python3
"""
test_web.py
===========
Verificacao da versao web (Flask test client, sem navegador):
catalogos pt-BR/en/es com as mesmas chaves, telas nos 3 idiomas e 2 modos de
cor, CSRF, calculos contra os valores do test_science, biblioteca, exportacoes
e a tela de Dados experimentais com o exemplo_PEPTIDE.mzML.

    python tests/test_web.py
"""

import io
import json
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = tempfile.mkdtemp(prefix="peptmass-web-test-")
os.environ["PEPTMASS_DATA_DIR"] = DATA
sys.path.insert(0, ROOT)

from peptmass.infra.database import Database  # noqa: E402
from peptmass.core.modifications import DEFAULT_MODIFICATIONS  # noqa: E402
from peptmass.core.presets import PRESET_RENAMES, migrate_preset_names  # noqa: E402
from peptmass.web import create_app, catalog  # noqa: E402

FAILS = []


def check(label, cond, detail=""):
    print(("  ok   " if cond else "  FALHA ") + label + (f"  ({detail})" if detail and not cond else ""))
    if not cond:
        FAILS.append(label)


def main():
    app = create_app()
    client = app.test_client()

    print("== catalogos")
    ref = set(catalog.load_catalog("pt-BR"))
    for lang in ("en", "es"):
        cat = set(catalog.load_catalog(lang))
        check(f"{lang}: mesmas chaves do pt-BR", cat == ref,
              f"faltam {sorted(ref - cat)[:5]} sobram {sorted(cat - ref)[:5]}")
    used = set()
    for root, _dirs, files in os.walk(os.path.join(ROOT, "peptmass", "web")):
        if "vendor" in root:
            continue
        for name in files:
            if name.endswith((".html", ".js", ".py")):
                text = open(os.path.join(root, name), encoding="utf-8").read()
                used.update(re.findall(r"(?:_\(|T\()\s*['\"]([a-z][\w-]*(?:\.[\w+-]+)+)['\"]", text))
    check("toda chave usada existe no pt-BR", used <= ref, f"{sorted(used - ref)[:8]}")

    print("== telas")
    for lang in ("pt-BR", "en", "es"):
        for tema in ("claro", "escuro"):
            for path in ("/", "/massa", "/fragmentacao", "/experimental", "/biblioteca"):
                r = client.get(f"{path}?lang={lang}&tema={tema}")
                html = r.get_data(as_text=True)
                ok = (r.status_code == 200 and f'lang="{lang}"' in html
                      and f'data-tema="{tema}"' in html)
                check(f"GET {path} [{lang}/{tema}]", ok, r.status_code)
    r = client.get("/massa", headers={"Cookie": "peptmass_lang=es; peptmass_tema=escuro"})
    html = r.get_data(as_text=True)
    check("cookie de idioma/tema respeitado", 'lang="es"' in html and 'data-tema="escuro"' in html)
    check("texto em espanhol", "Secuencia de aminoácidos" in html)
    check("404 com pagina de erro", client.get("/nao-existe").status_code == 404)

    token = re.search(r'name="csrf-token" content="([0-9a-f]+)"',
                      client.get("/").get_data(as_text=True)).group(1)
    H = {"X-CSRF-Token": token}

    def post(url, body, lang="pt-BR"):
        return client.post(f"{url}?lang={lang}", json=body, headers=H)

    print("== CSRF")
    r = client.post("/api/mass", json={"peptide": {"sequence": "PEPTIDE"}})
    check("POST sem token recusado (403)", r.status_code == 403)

    print("== massa")
    r = post("/api/mass", {"peptide": {"sequence": "PEPTIDE"}, "zextra": "15, 20"}).get_json()
    check("PEPTIDE valido", r["ok"] and r["valid"])
    check("PEPTIDE mono 799.359964", abs(r["result"]["mono"] - 799.359964) < 1e-3, r["result"]["mono"])
    check("tabela de cargas 1..10 + 15, 20", [z for z, _ in r["charges"]] == list(range(1, 11)) + [15, 20])
    check("distribuicao isotopica", len(r["isotopes"]) >= 3)
    r = post("/api/mass", {"peptide": {"sequence": "PEPT[Xyz]IDE"}}, "en").get_json()
    check("residuo desconhecido listado", r["unknown"] == ["Xyz"] and not r["valid"])
    check("mensagem do nucleo em ingles", r["message"].startswith("Unknown residue"), r["message"])
    r = post("/api/mass", {"peptide": {"sequence": "PEPT[Xyz]IDE"}}, "es").get_json()
    check("mensagem do nucleo em espanhol", r["message"].startswith("Residuo(s) desconocido"), r["message"])
    r = post("/api/mass", {"peptide": {"sequence": "PEPTIDE", "nterm": "Acetyl",
                                       "rmods": [[3, "Phosphorylation"]]}}).get_json()
    check("Ac-PEPT(Phospho)IDE", abs(r["result"]["mono"] - (799.359964 + 42.010565 + 79.966331)) < 1e-3)

    print("== fragmentos")
    body = {"peptide": {"sequence": "PEPTIDE"}, "ions": ["b", "y"], "charges": [1], "no_loss": True}
    r = post("/api/fragments", body).get_json()
    frags = {f["ion"]: f["mz"] for f in r["fragments"]}
    check("12 fragmentos b/y", len(r["fragments"]) == 12, len(r["fragments"]))
    check("b2 = 227.102633", abs(frags["b2"] - 227.102633) < 1e-3, frags.get("b2"))
    check("y1 = 148.060434", abs(frags["y1"] - 148.060434) < 1e-3, frags.get("y1"))
    r = post("/api/fragments", dict(body, match=True, exp="227.1026, 148.0604\n999.9", tol=0.01)).get_json()
    check("matching 2/3", r["ok"] and len(r["matches"]) == 2 and r["n_exp"] == 3)
    r = post("/api/fragments", {"peptide": {"sequence": "AAA/GGG"}, "ions": ["b"]}).get_json()
    check("multiplas cadeias sinalizadas", r["ok"] and r["multi_chain"])
    for fmt, magic in (("csv", b"Ion"), ("txt", b""), ("xlsx", b"PK"), ("pdf", b"%PDF"), ("skyline", b"Peptide")):
        r = client.post(f"/export/fragments/{fmt}?lang=en", headers=H,
                        data={"payload": json.dumps(body)})
        check(f"exportar {fmt}", r.status_code == 200 and r.data.startswith(magic)
              and "attachment" in r.headers.get("Content-Disposition", ""), r.status_code)

    print("== peptideos salvos")
    names = client.get("/api/peptides").get_json()["peptides"]
    check("presets semeados (GLP + WADA)", "Semaglutide" in names and len(names) > 50, len(names))
    for lang in ("pt-BR", "en", "es"):
        check(f"nomes em ingles ({lang})",
              client.get(f"/api/peptides?lang={lang}").get_json()["peptides"] == names)
    check("nenhum nome antigo nos presets", not set(PRESET_RENAMES) & set(names))
    check("descricoes sem portugues", not any(
        w in (m.description or "") for m in DEFAULT_MODIFICATIONS
        for w in ("Cadeia", "ção", "Ex.:", "ina ")))

    print("== migracao dos nomes")
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(os.path.join(tmp, "m.db"))
        db.save_peptide("Semaglutida", "EDITADA", "Acetyl", "", "[]", "nota")
        db.save_peptide("Oxitocina", "ANTIGA")
        db.save_peptide("Oxytocin", "DO USUARIO")
        migrate_preset_names(db)
        row = db.get_peptide("Semaglutide")
        check("renomeia mantendo os dados", row and row["sequence"] == "EDITADA"
              and row["n_term_mod"] == "Acetyl" and row["notes"] == "nota"
              and not db.get_peptide("Semaglutida"))
        check("nao sobrescreve nome existente",
              db.get_peptide("Oxytocin")["sequence"] == "DO USUARIO"
              and db.get_peptide("Oxitocina")["sequence"] == "ANTIGA")
        db.save_peptide("Semaglutida", "NOVA DO USUARIO")
        migrate_preset_names(db)
        check("roda uma vez so", db.get_peptide("Semaglutida") is not None)
        db.close()
    r = post("/api/peptide", {"name": "Teste web", "peptide": {"sequence": "PEPTIDE", "cterm": "Amidation"}})
    check("salvar", r.get_json()["ok"])
    r = post("/api/peptide", {"name": "Teste web", "peptide": {"sequence": "PEPTIDE"}})
    check("salvar de novo pede confirmacao (409)", r.status_code == 409 and r.get_json()["exists"])
    r = client.get("/api/peptide?name=Teste%20web").get_json()
    check("carregar", r["ok"] and r["peptide"]["cterm"] == "Amidation")
    check("remover", client.delete("/api/peptide?name=Teste%20web", headers=H).get_json()["ok"])
    check("home lista com massas", "Semaglutide" in client.get("/").get_data(as_text=True))
    for lang in ("pt-BR", "en", "es"):
        for rota in ("/", "/massa", "/fragmentacao", "/experimental", "/biblioteca"):
            html = client.get(f"{rota}?lang={lang}").get_data(as_text=True)
            check(f"sem travessao {rota} ({lang})", "\u2014" not in html and "\u2013" not in html)
    check("descricoes sem travessao", not any(
        c in (m.description or "") for m in DEFAULT_MODIFICATIONS for c in "\u2014\u2013"))

    print("== biblioteca")
    r = post("/api/residues", {"name": "Teste", "three": "Tst", "code": "Tst", "formula": "C4H9NO2"})
    check("novo aminoacido", r.get_json()["ok"], r.get_json())
    r = post("/api/mass", {"peptide": {"sequence": "A[Tst]G"}}).get_json()
    check("aminoacido usado na sequencia", r["valid"])
    r = post("/api/residues", {"name": "x", "three": "x", "code": "A", "formula": "C"}, "en").get_json()
    check("codigo natural recusado (en)", not r["ok"] and "natural" in r["error"], r)
    check("remover aminoacido", client.delete("/api/residues/Tst", headers=H).get_json()["ok"])
    r = client.delete("/api/residues/Aib", headers=H).get_json()
    check("embutido nao remove", not r["ok"])
    r = post("/api/modifications", {"name": "Teste mod", "formula": "C2H2O", "position": "residue", "targets": "k"})
    check("nova modificacao", r.get_json()["ok"], r.get_json())
    mods = client.get("/api/modifications?residue=K").get_json()["modifications"]
    check("modificacao aparece para K", any(m["name"] == "Teste mod" and m["custom"] for m in mods))
    check("remover modificacao",
          client.delete("/api/modifications?name=Teste%20mod", headers=H).get_json()["ok"])
    check("padrao nao remove",
          not client.delete("/api/modifications?name=Acetyl", headers=H).get_json()["ok"])
    r = post("/api/formula", {"formula": "C4H9NO2", "mode": "residue"}).get_json()
    check("previa do residuo Aib 85.052764", abs(r["mono"] - 85.052764) < 1e-4)
    r = post("/api/fasta", {"text": ">a\nPEPTIDE\n>b\nGGGG"}).get_json()
    check("FASTA", len(r["entries"]) == 2)

    print("== dados experimentais")
    sample = os.path.join(HERE, "data", "exemplo_PEPTIDE.mzML")
    if not os.path.exists(sample):
        print("  (exemplo_PEPTIDE.mzML ausente: pulado)")
    else:
        with open(sample, "rb") as fh:
            r = client.post("/api/ms/open", headers=H, content_type="multipart/form-data",
                            data={"file": (io.BytesIO(fh.read()), "exemplo_PEPTIDE.mzML"), "profile": "0"})
        r = r.get_json()
        check("abrir mzML", r["ok"] and r["n_scans"] > 0, r)
        rid = r["run_id"]
        filt = client.get(f"/api/ms/{rid}/filters?grouped=1").get_json()
        check("filtros", filt["ok"])
        ch = post(f"/api/ms/{rid}/chromatogram", {"ms_level": max(r["levels"]), "grouped": True}).get_json()
        check("cromatograma", ch["ok"] and len(ch["rt"]) > 0)
        sc = post(f"/api/ms/{rid}/scan", {"rt": ch["rt"][0], "ms_level": max(r["levels"])}).get_json()
        check("scan", sc["ok"] and len(sc["spectrum"]["mz"]) > 0)
        m = post(f"/api/ms/{rid}/match", {
            "index": sc["scan"]["index"], "peptide": {"sequence": "PEPTIDE"},
            "series": ["b", "y"], "charges": [1, 2], "tol": 20, "ppm": True,
            "prec_charge": 2}).get_json()
        check("anotacao b/y do PEPTIDE", m["ok"] and len(m["matches"]) >= 6, len(m.get("matches", [])))
        check("criterios e escore", m["ok"] and m["criteria"] and m["score"]["n"] >= 6)
        x = post(f"/api/ms/{rid}/xic", {"mz": m["matches"][0]["exp"], "ms_level": max(r["levels"])}).get_json()
        check("XIC", x["ok"] and len(x["rt"]) > 0)

    print()
    if FAILS:
        print(f"{len(FAILS)} FALHA(S):", ", ".join(FAILS))
    else:
        print("Todos os testes da versao web passaram.")
    return 1 if FAILS else 0


if __name__ == "__main__":
    try:
        code = main()
    finally:
        shutil.rmtree(DATA, ignore_errors=True)
    sys.exit(code)
