"""
pubchem.py
==========
Integração com o PubChem (PUG REST) para buscar moléculas diretamente
pelo nome, CID ou fórmula.

Usa apenas a biblioteca padrão (urllib) — sem dependências extras.
Não requer chave de API. O PubChem pede no máximo ~5 requisições/segundo.

Endpoints usados:
  /compound/name/{nome}/property/...      busca por nome
  /compound/cid/{cid}/property/...        busca por CID
  /compound/cid/{cid}/PNG                 imagem 2D da estrutura
"""

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass

from formula_parser import (parse_formula, composition_mass,
                            composition_to_string, FormulaError)
from i18n import t as _

BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
_PROPS = "MolecularFormula,MonoisotopicMass,ExactMass,MolecularWeight,IUPACName"
_TIMEOUT = 15
_HEADERS = {"User-Agent": "PeptMass/1.0 (peptide mass calculator)"}


class PubChemError(Exception):
    pass


@dataclass
class PubChemCompound:
    cid: int
    name: str                 # termo buscado / nome usual
    formula: str              # fórmula bruta retornada (Hill)
    clean_formula: str        # fórmula sanitizada (sem cargas/sais)
    iupac_name: str
    pubchem_monoisotopic: float
    pubchem_exact: float
    pubchem_avg: float
    composition: dict         # composição elementar (do clean_formula)

    @property
    def free_mono_mass(self) -> float:
        """Massa monoisotópica recalculada pelo PeptMass (IUPAC)."""
        return composition_mass(self.composition, average=False)

    @property
    def free_avg_mass(self) -> float:
        return composition_mass(self.composition, average=True)


# ---------------------------------------------------------------------------
def clean_formula(raw: str):
    """
    Sanitiza uma fórmula do PubChem para o parser do PeptMass.

    - Remove indicadores de carga (+, -).
    - Soma componentes separados por '.' (sais/hidratos) numa única fórmula.
    Retorna (string_limpa, composição_dict).
    """
    if not raw:
        raise PubChemError(_("Fórmula vazia."))
    # remove cargas e espaços
    s = raw.replace(" ", "")
    # remove dígitos de carga ao final de + / - (ex.: 'Mg+2')
    cleaned_parts = []
    for part in s.split("."):
        # tira sufixos de carga: +, -, +2, -3 ...
        p = part
        while p and p[-1] in "+-0123456789" and ("+" in p or "-" in p):
            # só corta se houver sinal de carga; evita cortar contagens normais
            if p[-1] in "+-":
                p = p[:-1]
            elif "+" in p[-3:] or "-" in p[-3:]:
                p = p[:-1]
            else:
                break
        p = p.replace("+", "").replace("-", "")
        if p:
            cleaned_parts.append(p)
    total = {}
    for p in cleaned_parts:
        try:
            comp = parse_formula(p)
        except FormulaError:
            continue
        for el, c in comp.items():
            total[el] = total.get(el, 0) + c
    if not total:
        raise PubChemError(
            _("Não foi possível interpretar a fórmula '{f}'.").format(f=raw))
    return composition_to_string(total), total


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers=_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            data = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise PubChemError(_("Composto não encontrado no PubChem."))
        raise PubChemError(_("Erro HTTP {c} do PubChem.").format(c=e.code))
    except urllib.error.URLError as e:
        raise PubChemError(
            _("Sem conexão com o PubChem: {e}").format(e=e.reason))
    return json.loads(data)


def _to_float(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _build_compound(query, props):
    raw_formula = props.get("MolecularFormula", "")
    clean, comp = clean_formula(raw_formula)
    return PubChemCompound(
        cid=int(props.get("CID", 0)),
        name=query,
        formula=raw_formula,
        clean_formula=clean,
        iupac_name=props.get("IUPACName", ""),
        pubchem_monoisotopic=_to_float(props.get("MonoisotopicMass")),
        pubchem_exact=_to_float(props.get("ExactMass")),
        pubchem_avg=_to_float(props.get("MolecularWeight")),
        composition=comp,
    )


def search_by_name(name: str) -> PubChemCompound:
    """Busca um composto pelo nome (ex.: 'ornithine', 'L-citrulline')."""
    q = urllib.parse.quote(name.strip())
    url = f"{BASE}/compound/name/{q}/property/{_PROPS},CID/JSON"
    data = _get_json(url)
    props_list = data.get("PropertyTable", {}).get("Properties", [])
    if not props_list:
        raise PubChemError(_("Nenhuma propriedade retornada."))
    return _build_compound(name.strip(), props_list[0])


def search_by_cid(cid: int) -> PubChemCompound:
    """Busca um composto pelo CID."""
    url = f"{BASE}/compound/cid/{int(cid)}/property/{_PROPS},CID/JSON"
    data = _get_json(url)
    props_list = data.get("PropertyTable", {}).get("Properties", [])
    if not props_list:
        raise PubChemError(_("CID não encontrado."))
    return _build_compound(f"CID {cid}", props_list[0])


def search_by_formula(formula: str, max_results: int = 5):
    """Busca compostos por fórmula molecular. Retorna lista de CIDs."""
    q = urllib.parse.quote(formula.strip())
    url = f"{BASE}/compound/fastformula/{q}/cids/JSON?MaxRecords={max_results}"
    data = _get_json(url)
    return data.get("IdentifierList", {}).get("CID", [])


def fetch_structure_png(cid: int) -> bytes:
    """Baixa a imagem 2D (PNG) da estrutura. Retorna bytes ou levanta erro."""
    url = f"{BASE}/compound/cid/{int(cid)}/PNG"
    req = urllib.request.Request(url, headers=_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return resp.read()
    except Exception as e:
        raise PubChemError(
            _("Não foi possível obter a imagem: {e}").format(e=e))


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Teste OFFLINE do sanitizador e do parsing (não acessa a rede).
    print("Teste de sanitização de fórmula:")
    for raw, exp in [("C9H8O4", "C9H8O4"),
                     ("C5H12N2O2", "C5H12N2O2"),     # ornitina
                     ("C6H13N2O2+", "C6H13N2O2"),     # cátion (lisina+)
                     ("C2H3O2.Na", "C2H3NaO2"),       # acetato de sódio
                     ("Mg+2", "Mg")]:
        clean, comp = clean_formula(raw)
        flag = "OK" if clean == exp else "??"
        print(f"  [{flag}] {raw:14s} -> {clean:12s} "
              f"mono={composition_mass(comp):.5f}")

    # Teste de parsing de resposta simulada do PubChem (estrutura real)
    mock = {
        "PropertyTable": {"Properties": [{
            "CID": 6262,
            "MolecularFormula": "C5H12N2O2",
            "MonoisotopicMass": "132.08988",
            "ExactMass": "132.08988",
            "MolecularWeight": "132.16",
            "IUPACName": "(2S)-2,5-diaminopentanoic acid",
        }]}}
    c = _build_compound("ornithine", mock["PropertyTable"]["Properties"][0])
    print(f"\nMock 'ornithine': CID={c.cid} {c.clean_formula} "
          f"PubChem mono={c.pubchem_monoisotopic} "
          f"PeptMass mono={c.free_mono_mass:.5f}")
    assert abs(c.free_mono_mass - 132.089878) < 1e-3
    print("Parsing PubChem: OK")
