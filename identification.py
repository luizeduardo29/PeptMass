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

Estas métricas apoiam os critérios de identificação (massa do precursor, tempo
de retenção e íons diagnósticos são avaliados na interface).
"""

PROTON = 1.007276466812
ISOTOPE_SPACING = 1.0033548   # Δm C13-C12 (espaçamento isotópico médio)


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
        mz = (neutral + charge * PROTON) / charge
        j = _nearest(exp_mz, mz)
        if j >= 0 and abs(exp_mz[j] - mz) <= tol:
            exp_vec.append(float(exp_int[j])); n += 1
        else:
            exp_vec.append(0.0)
        theo_vec.append(float(rel))
    return cosine(exp_vec, theo_vec), n


if __name__ == "__main__":
    # cluster sintético: PEPTIDE (C34H53N7O15) 2+, isótopos a cada 0.5017
    import numpy as np
    from mass_calculator import MassCalculator
    calc = MassCalculator(); r = calc.parse("PEPTIDE")
    dist = calc.isotopic_distribution(r.composition, max_peaks=6)
    z = 2
    mzs = [(m + z * PROTON) / z for m, _ in dist]
    ints = [i for _, i in dist]
    # adiciona ruido/pico alheio
    mz_all = mzs + [350.0, 999.0]
    int_all = ints + [5.0, 3.0]
    ez, nz = estimate_charge(np.array(mz_all), np.array(int_all), mzs[0])
    fit, nf = isotope_fit(np.array(mz_all), np.array(int_all), dist, z)
    print(f"carga estimada: {ez} (isotopos={nz}) | esperado 2")
    print(f"ajuste isotopico (cosseno): {fit:.4f} | isotopos alinhados {nf}")
