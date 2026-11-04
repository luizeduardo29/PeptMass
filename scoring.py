"""
scoring.py
==========
Escore de identificação espectral.

Usa o **escore de Morpheus** (Wenger & Coon, "A proteomics search algorithm
specifically designed for high-resolution tandem mass spectra", J. Proteome
Res. 2013, 12(3):1377-1386), desenhado para casar um espectro experimental
com íons teóricos in-silico SEM precisar de intensidades previstas:

    score = (nº de picos experimentais casados)
            + (fração da corrente iônica total explicada pelos picos casados)

A parte inteira conta os íons casados; a fração (0–1) pondera pela intensidade.
Maior = melhor. É interpretável, reprodutível e auditável.

Também expõe estatísticas do erro de massa dos íons casados (ppm), úteis como
controle de qualidade/calibração.
"""

from statistics import median


def morpheus_score(matched_exp_mzs, exp_mzs, exp_intensities):
    """Escore de Morpheus a partir dos m/z experimentais casados.

    matched_exp_mzs : m/z experimentais que casaram (vêm de exp_mzs)
    exp_mzs         : todos os m/z do espectro
    exp_intensities : intensidades correspondentes a exp_mzs

    Retorna dict: score, n_matched, tic_fraction, matched_tic, total_tic.
    """
    total = float(sum(exp_intensities)) or 1.0
    inten_by_mz = {}
    for m, i in zip(exp_mzs, exp_intensities):
        inten_by_mz[m] = i
    matched = set(matched_exp_mzs)
    matched_tic = float(sum(inten_by_mz.get(m, 0.0) for m in matched))
    n = len(matched)
    frac = matched_tic / total
    return {
        "score": n + frac,
        "n_matched": n,
        "tic_fraction": frac,
        "matched_tic": matched_tic,
        "total_tic": total,
    }


def mass_error_stats(errors):
    """Estatísticas do erro de massa dos íons casados (lista de erros, em ppm
    ou Da conforme o matching). Retorna dict: n, mean, median, max_abs, rmse."""
    if not errors:
        return {"n": 0, "mean": 0.0, "median": 0.0, "max_abs": 0.0, "rmse": 0.0}
    n = len(errors)
    mean = sum(errors) / n
    med = median(errors)
    max_abs = max(abs(e) for e in errors)
    rmse = (sum(e * e for e in errors) / n) ** 0.5
    return {"n": n, "mean": mean, "median": med, "max_abs": max_abs,
            "rmse": rmse}


def score_spectrum(matches, exp_mzs, exp_intensities, n_theoretical=None):
    """Conveniência: dado o resultado de `match_experimental`
    (lista de (exp_mz, Fragment, erro)) + o espectro, devolve o escore de
    Morpheus, a cobertura de íons e as estatísticas de erro de massa."""
    matched_mzs = [exp for exp, _f, _e in matches]
    errors = [e for _m, _f, e in matches]
    res = morpheus_score(matched_mzs, exp_mzs, exp_intensities)
    res["coverage"] = (100.0 * len(matches) / n_theoretical
                       if n_theoretical else 0.0)
    res["mass_error"] = mass_error_stats(errors)
    return res


if __name__ == "__main__":
    # Teste: casamento perfeito vs. parcial
    exp = [100.0, 200.0, 300.0, 400.0]
    inten = [10.0, 40.0, 30.0, 20.0]
    perfect = morpheus_score(exp, exp, inten)
    print("perfeito :", f"score={perfect['score']:.4f}  "
          f"n={perfect['n_matched']}  TIC={perfect['tic_fraction']*100:.0f}%")
    partial = morpheus_score([200.0, 300.0], exp, inten)
    print("parcial  :", f"score={partial['score']:.4f}  "
          f"n={partial['n_matched']}  TIC={partial['tic_fraction']*100:.0f}%")
    print("erro ppm :", mass_error_stats([2.1, -1.4, 0.8, 3.2, -2.0]))
