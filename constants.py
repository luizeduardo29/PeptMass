"""
constants.py
============
Constantes científicas: massas atômicas (IUPAC), distribuições isotópicas
e fórmulas dos aminoácidos naturais.

Massas monoisotópicas: valores IUPAC/CODATA.
Massas médias: pesos atômicos padrão IUPAC.
"""

# Massa do próton (carga) — valor exigido pela especificação
PROTON_MASS = 1.007276466812

# ---------------------------------------------------------------------------
# Massas atômicas MONOISOTÓPICAS (isótopo mais abundante)
# ---------------------------------------------------------------------------
ELEMENTS_MONO = {
    "H": 1.0078250319,
    "D": 2.0141017779,      # deutério
    "C": 12.0000000000,
    "N": 14.0030740052,
    "O": 15.9949146221,
    "P": 30.9737615120,
    "S": 31.9720706912,
    "Se": 79.9165218000,
    "F": 18.9984031627,
    "Cl": 34.9688527100,
    "Br": 78.9183376000,
    "I": 126.904473000,
    "Na": 22.9897692809,
    "K": 38.9637064864,
    "Ca": 39.9625909800,
    "Mg": 23.9850417000,
    "Fe": 55.9349363300,
    "Zn": 63.9291422000,
    "Cu": 62.9295975000,
    "Mn": 54.9380451000,
    "Ni": 57.9353429000,
    "Co": 58.9331943000,
    "B": 11.0093054000,
    "Si": 27.9769265350,
}

# ---------------------------------------------------------------------------
# Massas atômicas MÉDIAS (peso atômico padrão)
# ---------------------------------------------------------------------------
ELEMENTS_AVG = {
    "H": 1.00794,
    "D": 2.014102,
    "C": 12.0107,
    "N": 14.0067,
    "O": 15.9994,
    "P": 30.973762,
    "S": 32.065,
    "Se": 78.96,
    "F": 18.9984032,
    "Cl": 35.453,
    "Br": 79.904,
    "I": 126.90447,
    "Na": 22.98976928,
    "K": 39.0983,
    "Ca": 40.078,
    "Mg": 24.305,
    "Fe": 55.845,
    "Zn": 65.38,
    "Cu": 63.546,
    "Mn": 54.938045,
    "Ni": 58.6934,
    "Co": 58.933195,
    "B": 10.811,
    "Si": 28.0855,
}

# ---------------------------------------------------------------------------
# Distribuições isotópicas (massa, abundância relativa) por elemento.
# Usadas no cálculo do envelope isotópico teórico.
# ---------------------------------------------------------------------------
ISOTOPES = {
    "H":  [(1.0078250319, 0.999885), (2.0141017779, 0.000115)],
    "C":  [(12.0000000000, 0.989300), (13.0033548378, 0.010700)],
    "N":  [(14.0030740052, 0.996320), (15.0001088984, 0.003680)],
    "O":  [(15.9949146221, 0.997570), (16.9991315000, 0.000380),
           (17.9991604000, 0.002050)],
    "P":  [(30.9737615120, 1.000000)],
    "S":  [(31.9720706912, 0.949300), (32.9714585000, 0.007600),
           (33.9678668300, 0.042900), (35.9670808800, 0.000200)],
    "Se": [(73.9224764000, 0.000890), (75.9192136000, 0.009370),
           (76.9199140000, 0.076300), (77.9173091000, 0.237700),
           (79.9165213000, 0.496100), (81.9166994000, 0.087300)],
    "Cl": [(34.9688527100, 0.757800), (36.9659026000, 0.242200)],
    "Br": [(78.9183376000, 0.506900), (80.9162910000, 0.493100)],
    "F":  [(18.9984031627, 1.000000)],
    "I":  [(126.904473000, 1.000000)],
    "Na": [(22.9897692809, 1.000000)],
    "K":  [(38.9637064864, 0.932581), (39.9639981660, 0.000117),
           (40.9618252579, 0.067302)],
    "Si": [(27.9769265350, 0.922230), (28.9764946600, 0.046850),
           (29.9737701700, 0.030920)],
}

# ---------------------------------------------------------------------------
# Aminoácidos naturais — definidos pela fórmula do RESÍDUO
# (aminoácido livre menos uma molécula de água; H2O é adicionada nas pontas)
# ---------------------------------------------------------------------------
AMINO_ACIDS = {
    "G": {"name": "Glycine",        "three": "Gly", "formula": "C2H3NO"},
    "A": {"name": "Alanine",        "three": "Ala", "formula": "C3H5NO"},
    "S": {"name": "Serine",         "three": "Ser", "formula": "C3H5NO2"},
    "P": {"name": "Proline",        "three": "Pro", "formula": "C5H7NO"},
    "V": {"name": "Valine",         "three": "Val", "formula": "C5H9NO"},
    "T": {"name": "Threonine",      "three": "Thr", "formula": "C4H7NO2"},
    "C": {"name": "Cysteine",       "three": "Cys", "formula": "C3H5NOS"},
    "L": {"name": "Leucine",        "three": "Leu", "formula": "C6H11NO"},
    "I": {"name": "Isoleucine",     "three": "Ile", "formula": "C6H11NO"},
    "N": {"name": "Asparagine",     "three": "Asn", "formula": "C4H6N2O2"},
    "D": {"name": "Aspartic acid",  "three": "Asp", "formula": "C4H5NO3"},
    "Q": {"name": "Glutamine",      "three": "Gln", "formula": "C5H8N2O2"},
    "K": {"name": "Lysine",         "three": "Lys", "formula": "C6H12N2O"},
    "E": {"name": "Glutamic acid",  "three": "Glu", "formula": "C5H7NO3"},
    "M": {"name": "Methionine",     "three": "Met", "formula": "C5H9NOS"},
    "H": {"name": "Histidine",      "three": "His", "formula": "C6H7N3O"},
    "F": {"name": "Phenylalanine",  "three": "Phe", "formula": "C9H9NO"},
    "R": {"name": "Arginine",       "three": "Arg", "formula": "C6H12N4O"},
    "Y": {"name": "Tyrosine",       "three": "Tyr", "formula": "C9H9NO2"},
    "W": {"name": "Tryptophan",     "three": "Trp", "formula": "C11H10N2O"},
}
