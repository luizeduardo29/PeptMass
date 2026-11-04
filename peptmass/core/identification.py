"""
identification.py
=================
Ferramentas de confirmação de identidade a partir do MS1 do precursor:

- `estimate_charge()`  — deduz a carga do precursor pelo espaçamento do
  cluster isotópico (os isótopos distam 1.00335/z em m/z).
- `cosine()`           — similaridade cosseno entre dois vetores.
- `isotope_fit()`      — compara o envelope isotópico experimental do precursor
  com o teórico (de `MassCalculator.isotopic_distribution`) e devolve um escore
  de ajuste 0–1.

- `evaluate_criteria()` — avalia massa do precursor, tempo de retenção, íons
  diagnósticos e envelope isotópico, para a web e o desktop.
"""

from peptmass.core.constants import PROTON_MASS

ISOTOPE_SPACING = 1.0033548   # Δm C13-C12 (espaçamento isotópico médio)

# Limites dos critérios "estilo WADA". São decisões deste sistema, não regras
# oficiais: qualquer mudança aqui vale para a web e para o desktop.
PRECURSOR_LIMIT_PPM = 20.0    # usado quando a tolerância do matching é em Da
MIN_DIAGNOSTIC_IONS = 2
MIN_ISOTOPE_COSINE = 0.9
MIN_ALIGNED_ISOTOPES = 2
MIN_ISOTOPE_TOLERANCE = 0.02  # Da


def _nearest(mz_list, target):
    """Índice do m/z mais próximo de target (ou -1 se vazio)."""
    if not len(mz_list):
        return -1
    best_i, best_d = -1, float("inf")
    for i, m in enumerate(mz_list):
        d = abs(m - target)
        if d < best_d:
            best_d, best_i = d, i
    return best_i


def estimate_charge(mz, inten, target_mz, tol=0.02, zmax=8):
    """Carga do precursor pelo cluster isotópico ao redor de `target_mz`.

    Para cada z candidato, verifica picos consecutivos em target + k·(1.00335/z)
    e escolhe o z com maior suporte (soma de intensidades dos isótopos achados).
    Retorna (z, n_isotopos) ou (None, 0) se não houver evidência."""
    if not len(mz):
        return None, 0
    i0 = _nearest(mz, target_mz)
    base = mz[i0] if abs(mz[i0] - target_mz) <= max(tol, 0.5) else target_mz
    best_z, best_support, best_n = None, 0.0, 0
    for z in range(1, zmax + 1):
        step = ISOTOPE_SPACING / z
        support, n = 0.0, 0
        for k in range(1, 6):
            j = _nearest(mz, base + k * step)
            if j >= 0 and abs(mz[j] - (base + k * step)) <= tol:
                support += float(inten[j])
                n += 1
            else:
                break   # exige isótopos consecutivos
        if n >= 1 and support > best_support:
            best_z, best_support, best_n = z, support, n
    return best_z, best_n


def cosine(a, b):
    """Similaridade cosseno (0–1) entre dois vetores de intensidade."""
    num = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return num / (na * nb) if na and nb else 0.0


def isotope_fit(exp_mz, exp_int, theo_dist, charge, tol=0.02):
    """Escore de ajuste (cosseno 0–1) do envelope isotópico do precursor.

    exp_mz/exp_int : espectro MS1 (ou região do precursor)
    theo_dist      : lista [(massa_neutra, intensidade_rel)] do teórico
    charge         : carga do precursor
    Alinha cada pico teórico (convertido para m/z na carga dada) ao pico
    experimental mais próximo e compara as intensidades."""
    if not theo_dist or not len(exp_mz) or not charge:
        return 0.0, 0
    th = sorted(theo_dist, key=lambda x: x[0])
    exp_vec, theo_vec, n = [], [], 0
    for neutral, rel in th:
        mz = (neutral + charge * PROTON_MASS) / charge
        j = _nearest(exp_mz, mz)
        if j >= 0 and abs(exp_mz[j] - mz) <= tol:
            exp_vec.append(float(exp_int[j])); n += 1
        else:
            exp_vec.append(0.0)
        theo_vec.append(float(rel))
    return cosine(exp_vec, theo_vec), n


def ms1_envelope_fit(run, scan, distribution, charge, tol):
    """(cosseno, n isotopos) contra o MS1 anterior ao scan, ou None. O ajuste e'
    complementar: uma falha de leitura nao pode derrubar a anotacao do espectro."""
    try:
        ms1 = run.ms1_before(scan)
        if ms1 is None:
            return None
        mz, intensity = run.spectrum(ms1.index)
        return isotope_fit(mz, intensity, distribution, charge,
                           tol=max(tol, MIN_ISOTOPE_TOLERANCE))
    except Exception:  # noqa: BLE001
        return None


def evaluate_criteria(mono_mass, precursor_mz, charge, tolerance, ppm, scan_rt,
                      expected_rt, rt_window, n_ions, envelope_fit):
    """Criterios de identificacao, na ordem de exibicao.

    Devolve [{"kind", "state", "value"}]: kind e' precursor | rt | ions | isotopes
    e state e' ok | bad | warn. Precursor e RT so entram quando ha dado para
    avaliar; expected_rt = 0 significa "nao informado"."""
    criteria = []
    if precursor_mz and charge:
        neutral = precursor_mz * charge - charge * PROTON_MASS
        error = (neutral - mono_mass) / mono_mass * 1e6
        limit = tolerance if ppm else PRECURSOR_LIMIT_PPM
        criteria.append({"kind": "precursor", "value": error,
                         "state": "ok" if abs(error) <= limit else "bad"})
    if expected_rt > 0:
        delta = abs(scan_rt - expected_rt)
        criteria.append({"kind": "rt", "value": delta,
                         "state": "ok" if delta <= rt_window else "bad"})
    criteria.append({"kind": "ions", "value": n_ions,
                     "state": "ok" if n_ions >= MIN_DIAGNOSTIC_IONS else "bad"})
    if envelope_fit and envelope_fit[1] >= MIN_ALIGNED_ISOTOPES:
        fit = envelope_fit[0]
        criteria.append({"kind": "isotopes", "value": fit,
                         "state": "ok" if fit >= MIN_ISOTOPE_COSINE else "warn"})
    return criteria
