"""
spectra_io.py
=============
Leitura de dados de espectrometria de massas para o PeptMass.

Suporta arquivos abertos **mzML** e **mzXML** (via pyteomics). Arquivos **.raw**
da Thermo são convertidos para mzML sob demanda pelo ThermoRawFileParser, se
disponível (ver `thermo_raw_to_mzml`).

API:
    run = open_run(path)
    run.scans              -> lista de Scan (metadados, já carregados)
    run.chromatogram(...)  -> (rts, intensities)  — TIC por nível MS
    run.spectrum(index)    -> (mz_array, intensity_array)  — picos do scan

As dependências (pyteomics, lxml) são importadas de forma preguiçosa para que o
resto do PeptMass funcione mesmo sem elas instaladas.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass


# peptmass/infra/spectra_io.py -> raiz do projeto
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class SpectraIOError(Exception):
    pass


# Em DDA cada MS2 traz o m/z do precursor no filtro, gerando milhares de
# filtros distintos. Mascarar o precursor agrupa-os em poucos "tipos".
#   'FTMS + c NSI d Full ms2 1372.0000@hcd27.00' -> '... Full ms2 *@hcd27.00'
_PRECURSOR_RE = re.compile(r"(ms\d+\s+)([\d.]+)(@)")


def normalize_filter(filter_string):
    """Filtro com o m/z do precursor substituído por '*' (para agrupar)."""
    return _PRECURSOR_RE.sub(r"\1*\3", filter_string or "")


def centroid_peaks(mz, intensity, rel_threshold=0.001):
    """Centroida dados em perfil: máximos locais acima de `rel_threshold` ×
    pico-base, com o m/z do ápice refinado por parábola no logaritmo das três
    intensidades vizinhas (exato para picos gaussianos).

    Sem esse refinamento o m/z ficaria preso à grade do perfil, e o erro de
    quantização estouraria tolerâncias de poucos ppm.
    """
    import numpy as np
    mz = np.asarray(mz, dtype=float)
    y = np.asarray(intensity, dtype=float)
    if y.size < 3:
        return mz.tolist(), y.tolist()
    thr = float(y.max()) * rel_threshold
    mid = y[1:-1]
    is_max = (mid > y[:-2]) & (mid >= y[2:]) & (mid > thr)
    idx = np.where(is_max)[0] + 1
    if idx.size == 0:
        return [], []
    yl, yc, yr = y[idx - 1], y[idx], y[idx + 1]
    delta = np.zeros(idx.size)
    ok = (yl > 0) & (yc > 0) & (yr > 0)
    if ok.any():
        ll, lc, lr = np.log(yl[ok]), np.log(yc[ok]), np.log(yr[ok])
        denom = ll - 2.0 * lc + lr
        d = np.where(np.abs(denom) > 1e-12, 0.5 * (ll - lr) / denom, 0.0)
        delta[ok] = np.clip(np.nan_to_num(d), -0.5, 0.5)
    step = (mz[idx + 1] - mz[idx - 1]) / 2.0
    return (mz[idx] + delta * step).tolist(), yc.tolist()


@dataclass
class Scan:
    index: int            # índice 0-based no arquivo
    scan_id: str          # id nativo (ex.: 'controllerType=0 controllerNumber=1 scan=42')
    ms_level: int
    rt: float             # tempo de retenção em minutos
    tic: float            # corrente iônica total do scan
    filter_string: str = ""
    precursor_mz: float = None
    profile: bool = False   # True = dados em perfil (não centroidados)
    precursor_charge: int = None   # carga do precursor, se declarada no arquivo

    @property
    def label(self):
        base = f"#{self.index + 1}  RT {self.rt:.3f} min  MS{self.ms_level}"
        if self.precursor_mz:
            base += f"  prec {self.precursor_mz:.4f}"
        return base


class MSRun:
    """Interface comum. Subclasses preenchem self.scans e implementam spectrum()."""

    path = None
    scans = ()

    def filters(self, grouped=False):
        """Filtros de scan presentes, como [(filtro, nº de scans)] ordenados do
        mais frequente ao menos. Com grouped=True o m/z do precursor é mascarado."""
        key = normalize_filter if grouped else (lambda f: f)
        counts = Counter(key(s.filter_string)
                         for s in self.scans if s.filter_string)
        return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))

    def _select(self, ms_level=None, scan_filter=None, grouped=False):
        """Scans que atendem ao filtro. Um filtro de scan explícito tem
        precedência sobre o nível MS (o filtro já define o nível)."""
        if scan_filter:
            if grouped:
                return [s for s in self.scans
                        if normalize_filter(s.filter_string) == scan_filter]
            return [s for s in self.scans if s.filter_string == scan_filter]
        return [s for s in self.scans
                if ms_level is None or s.ms_level == ms_level]

    def chromatogram(self, ms_level=1, scan_filter=None, grouped=False):
        """TIC: (lista de RT, lista de intensidade) dos scans selecionados."""
        pts = [(s.rt, s.tic)
               for s in self._select(ms_level, scan_filter, grouped)]
        pts.sort()
        return [p[0] for p in pts], [p[1] for p in pts]

    def ms_levels(self):
        return sorted({s.ms_level for s in self.scans})

    def xic(self, target_mz, tol=0.02, ppm=False, ms_level=1,
            scan_filter=None, grouped=False):
        """Cromatograma de íon extraído (XIC): para cada scan do nível pedido,
        soma a intensidade dos picos dentro de [target ± tol].

        Retorna (lista de RT, lista de intensidade somada)."""
        if ppm:
            lo = target_mz * (1 - tol / 1e6)
            hi = target_mz * (1 + tol / 1e6)
        else:
            lo, hi = target_mz - tol, target_mz + tol
        rts, ints = [], []
        for s in self._select(ms_level, scan_filter, grouped):
            mz, inten = self.spectrum(s.index)
            mask = (mz >= lo) & (mz <= hi)
            rts.append(s.rt)
            ints.append(float(inten[mask].sum()) if mask.any() else 0.0)
        order = sorted(range(len(rts)), key=lambda i: rts[i])
        return [rts[i] for i in order], [ints[i] for i in order]

    def scan_at_rt(self, rt, ms_level=None, scan_filter=None, grouped=False):
        """Scan cujo RT é o mais próximo de `rt`, dentro da seleção."""
        cands = self._select(ms_level, scan_filter, grouped)
        if not cands:
            return None
        return min(cands, key=lambda s: abs(s.rt - rt))

    def ms1_before(self, scan):
        """MS1 (survey) imediatamente anterior a `scan` — onde o precursor foi
        isolado. Usado para carga e envelope isotópico do precursor."""
        prev = None
        for s in self.scans:
            if s.index >= scan.index:
                break
            if s.ms_level == 1:
                prev = s
        return prev

    def spectrum(self, index):
        raise NotImplementedError

    def close(self):
        pass


# ---------------------------------------------------------------------------
class _PyteomicsRun(MSRun):
    """Base para mzML/mzXML lidos com pyteomics."""

    def __init__(self, path):
        self.path = path
        self._reader = self._open_reader(path)
        self.scans = []
        for i, sp in enumerate(self._reader):
            self.scans.append(self._parse_meta(i, sp))

    # implementados pelas subclasses
    def _open_reader(self, path):
        raise NotImplementedError

    def _parse_meta(self, i, sp):
        raise NotImplementedError

    def close(self):
        try:
            self._reader.close()
        except Exception:
            pass


class MzmlRun(_PyteomicsRun):
    def _open_reader(self, path):
        from pyteomics import mzml
        return mzml.MzML(path)

    def _parse_meta(self, i, sp):
        ms_level = int(sp.get("ms level", 1) or 1)
        scan_id = sp.get("id", f"index={i}")
        rt, filt = 0.0, ""
        scans = sp.get("scanList", {}).get("scan", [])
        if scans:
            sc0 = scans[0]
            if "scan start time" in sc0:
                rt = float(sc0["scan start time"])
            filt = sc0.get("filter string", "") or ""
        tic = sp.get("total ion current", None)
        if tic is None and "intensity array" in sp:
            tic = float(sp["intensity array"].sum())
        prec, pz = None, None
        precs = sp.get("precursorList", {}).get("precursor", [])
        if precs:
            sel = precs[0].get("selectedIonList", {}).get("selectedIon", [])
            if sel:
                if "selected ion m/z" in sel[0]:
                    prec = float(sel[0]["selected ion m/z"])
                if "charge state" in sel[0]:
                    try:
                        pz = int(sel[0]["charge state"])
                    except (ValueError, TypeError):
                        pz = None
        # mzML marca o tipo do espectro por cvParam
        profile = "profile spectrum" in sp
        return Scan(i, scan_id, ms_level, rt, float(tic or 0.0), filt, prec,
                    profile, pz)

    def spectrum(self, index):
        sp = self._reader.get_by_index(index)
        return sp["m/z array"], sp["intensity array"]


class MzxmlRun(_PyteomicsRun):
    def _open_reader(self, path):
        from pyteomics import mzxml
        return mzxml.MzXML(path)

    def _parse_meta(self, i, sp):
        ms_level = int(sp.get("msLevel", 1) or 1)
        scan_id = str(sp.get("id", sp.get("num", i)))
        rt = float(sp.get("retentionTime", 0.0) or 0.0)  # pyteomics dá em minutos
        tic = sp.get("totIonCurrent", None)
        if tic is None and "intensity array" in sp:
            tic = float(sp["intensity array"].sum())
        prec = None
        pmz = sp.get("precursorMz", [])
        if pmz:
            prec = float(pmz[0].get("precursorMz"))
        return Scan(i, scan_id, ms_level, rt, float(tic or 0.0),
                    sp.get("filterLine", "") or "", prec)

    def spectrum(self, index):
        sp = self._reader.get_by_index(index)
        return sp["m/z array"], sp["intensity array"]


# ---------------------------------------------------------------------------
# Thermo .raw -> mzML (Fase 3): converte sob demanda se o conversor existir.
# ---------------------------------------------------------------------------
def find_thermo_parser():
    """Localiza o ThermoRawFileParser. Ordem de busca:
    1) variável de ambiente PEPTMASS_THERMO_PARSER (caminho do exe);
    2) pasta 'ThermoRawFileParser' ao lado do PeptMass.exe, no bundle, na
       raiz do projeto (execução por código) ou em ~/.peptmass;
    3) no PATH (ThermoRawFileParser.exe / ThermoRawFileParser).
    O conversor não vai no executável: a licença da biblioteca da Thermo
    restringe distribuí-la junto com software GPL."""
    env = os.environ.get("PEPTMASS_THERMO_PARSER")
    if env and os.path.exists(env):
        return env
    bases = []
    # exe congelado (PyInstaller): ao lado do PeptMass.exe (onde o usuario
    # coloca a pasta) e os dados do pacote em sys._MEIPASS
    if getattr(sys, "frozen", False):
        bases.append(os.path.dirname(sys.executable))
        if hasattr(sys, "_MEIPASS"):
            bases.append(sys._MEIPASS)
    bases.append(_PROJECT_ROOT)
    bases.append(os.path.join(os.path.expanduser("~"), ".peptmass"))
    for base in bases:
        for name in ("ThermoRawFileParser.exe", "ThermoRawFileParser"):
            cand = os.path.join(base, "ThermoRawFileParser", name)
            if os.path.exists(cand):
                return cand
    return shutil.which("ThermoRawFileParser") or \
        shutil.which("ThermoRawFileParser.exe")


def thermo_raw_to_mzml(raw_path, out_dir=None, no_peak_picking=False):
    """Converte um .raw em mzML e devolve o caminho do mzML gerado.

    no_peak_picking=True preserva os dados em **perfil** (passa -p ao
    ThermoRawFileParser). Pode ser uma string com os níveis MS, ex.: '1'.
    Por padrão o conversor faz peak picking (saída centroidada)."""
    exe = find_thermo_parser()
    if not exe:
        from peptmass.core.i18n import t as _
        raise SpectraIOError(_(
            "Para abrir .raw é preciso o leitor ThermoRawFileParser, que não vem "
            "com o PeptMass. No programa para Windows, use o botão \"Instalar "
            "leitor de .raw\" desta tela. Outra opção: converta o .raw para "
            "mzML e abra o mzML."))
    out_dir = out_dir or tempfile.mkdtemp(prefix="peptmass_raw_")
    cmd = [exe, "-i", raw_path, "-o", out_dir, "-f", "2"]  # -f 2 = mzML indexado
    if no_peak_picking:
        cmd.append("-p" if no_peak_picking is True
                   else f"-p{no_peak_picking}")
    # Em Linux/macOS, um build .NET Framework (.exe) precisa do mono.
    if os.name != "nt" and exe.lower().endswith(".exe"):
        cmd = ["mono"] + cmd
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SpectraIOError(
            "Falha ao converter o .raw:\n" + (proc.stderr or proc.stdout))
    base = os.path.splitext(os.path.basename(raw_path))[0] + ".mzML"
    out = os.path.join(out_dir, base)
    if not os.path.exists(out):
        raise SpectraIOError("Conversão concluída, mas o mzML não foi encontrado.")
    return out


# ---------------------------------------------------------------------------
def open_run(path, profile=False, work_dir=None):
    """Abre um arquivo de dados e devolve um MSRun.

    Suporta .mzML, .mzXML e .raw (este último convertido para mzML).
    profile=True converte o .raw sem peak picking (dados em perfil).
    work_dir: pasta onde o mzML convertido de um .raw é gravado (quem chama
    a apaga quando fecha o arquivo); sem ela, uma pasta temporária nova."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".mzml":
        return MzmlRun(path)
    if ext == ".mzxml":
        return MzxmlRun(path)
    if ext == ".raw":
        return MzmlRun(thermo_raw_to_mzml(path, out_dir=work_dir,
                                          no_peak_picking=profile))
    raise SpectraIOError(f"Formato não suportado: '{ext}'. "
                         f"Use .mzML, .mzXML ou .raw.")
