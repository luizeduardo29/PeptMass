"""
presets.py
==========
Peptideos pre-carregados na base local na primeira execucao (analogos de
GLP e controle antidopagem WADA S2). Compartilhado pela interface desktop
(gui.py) e pela web (web/), por isso nao importa nada de interface.
"""

# Peptídeos-exemplo semeados na base na primeira execução (análogos de GLP).
# (nome, sequência com mods inline, mod N-terminal, mod C-terminal)
GLP_PRESETS = [
    ("Liraglutide",
     "HAEGTFTSDVSSYLEGQAAK(Liraglutide)EFIAWLVRGRG", "", ""),
    ("Semaglutide",
     "H[Aib]EGTFTSDVSSYLEGQAAK(Semaglutide)EFIAWLVRGRG", "", ""),
    ("Tirzepatide",
     "Y[Aib]EGTFTSDYSI[Aib]LDKIAQK(Tirzepatide)AFVQWLIAGGPSSGAPPPS",
     "", "Amidation"),
    ("Retatrutide",
     "Y[Aib]QGTFTSDYSI[aMeLeu]LDKK(Retatrutide)AQ[Aib]AFIEYLLEGGPSSGAPPPS",
     "", "Amidation"),
]

# Peptídeos de controle antidopagem (WADA S2). D-aminoácidos têm a mesma massa
# que os L, então usam-se os códigos L. Massas validadas contra o PubChem.
# (nome, sequência com mods inline, mod N-terminal, mod C-terminal)
DOPING_PRESETS = [
    # -- GnRH / LHRH e agonistas --
    ("Gonadorelin (GnRH)", "[pGlu]HWSYGLRPG", "", "Amidation"),
    ("Triptorelin", "[pGlu]HWSYWLRPG", "", "Amidation"),
    ("Leuprolide", "[pGlu]HWSYLLRP", "", "Ethylamide"),
    ("Nafarelin", "[pGlu]HWSY[Nal]LRPG", "", "Amidation"),
    ("Buserelin", "[pGlu]HWSY[SertBu]LRP", "", "Ethylamide"),
    ("Goserelin", "[pGlu]HWSY[SertBu]LRP", "", "Azaglycinamide"),
    ("Deslorelin", "[pGlu]HWSYWLRP", "", "Ethylamide"),
    ("Fertirelin", "[pGlu]HWSYGLRP", "", "Ethylamide"),
    ("Alarelin", "[pGlu]HWSYALRP", "", "Ethylamide"),
    ("Histrelin", "[pGlu]HWSY[HisBzl]LRP", "", "Ethylamide"),
    ("Lecirelin", "[pGlu]HWSY[Tle]LRP", "", "Ethylamide"),
    # -- Vasopressina e análogos (ciclo Cys1-Cys6) --
    ("Vasopressin (Arg8)", "CYFQNCPRG", "", "Amidation",
     '[[0, "Disulfide (-2H)"]]'),
    ("Lypressin (Lys8)", "CYFQNCPKG", "", "Amidation",
     '[[0, "Disulfide (-2H)"]]'),
    ("Felypressin", "CFFQNCPKG", "", "Amidation",
     '[[0, "Disulfide (-2H)"]]'),
    ("Desmopressin (dDAVP)", "[Mpa]YFQNCPRG", "", "Amidation",
     '[[0, "Disulfide (-2H)"]]'),
    ("Terlipressin", "GGGCYFQNCPKG", "", "Amidation",
     '[[3, "Disulfide (-2H)"]]'),
    # -- GHRP / secretagogos de GH --
    ("GHRP-1", "AH[Nal]AWFK", "", "Amidation"),
    ("GHRP-2 (pralmorelin)", "A[Nal]AWFK", "", "Amidation"),
    ("GHRP-6", "HWAWFK", "", "Amidation"),
    ("Hexarelin", "H[MeW]AWFK", "", "Amidation"),
    ("Ipamorelin", "[Aib]H[Nal]FK", "", "Amidation"),
    ("Alexamorelin", "AH[MeW]AWFK", "", "Amidation"),
    ("GHRP-3", "[Aib]WPIR", "", "Amidation"),
    ("GHRP-4", "WAWF", "", "Amidation"),
    ("GHRP-5", "YWAWF", "", "Amidation"),
    ("Ghrelin (Ser3-acylated)", "GSSFLSPEHQRVQQRKESKKPPAKLQPR", "", "",
     '[[2, "Octanoyl"]]'),
    # -- GHRH / GRF --
    ("Sermorelin (GHRH 1-29)",
     "YADAIFTNSYRKVLGQLSARKLLQDIMSR", "", "Amidation"),
    ("Mod GRF 1-29 (CJC-1295 without DAC)",
     "YADAIFTQSYRKVLAQLSARKLLQDILSR", "", "Amidation"),
    ("Tesamorelin (GHRH 1-44)",
     "YADAIFTNSYRKVLGQLSARKLLQDIMSRQQGESNQERGARARL",
     "3-Hexenoyl", "Amidation"),
    # -- Fragmentos de hGH / reparo tecidual / opioides --
    ("AOD-9604 (Tyr-hGH 177-191)", "YLRIVQCRSVEGSCGF", "", "",
     '[[6, "Disulfide (-2H)"]]'),
    ("hGH (176-191)", "FLRIVQCRSVEGSCGF", "", "",
     '[[6, "Disulfide (-2H)"]]'),
    ("BPC-157", "GEPPPGKPADDAGLV", "", ""),
    ("ARA-290 (cibinetide)", "[pGlu]EQLERALNSS", "", ""),
    ("Dermorphin", "YAFGYPS", "", "Amidation"),
    # -- Peptídeo mitocondrial --
    ("MOTS-c", "MRWQEMGYIFYPRKLR", "", ""),
    # -- Nootrópicos / reguladores (família russa Pro-Gly-Pro) --
    ("Semax (ACTH 4-7 + PGP)", "MEHFPGP", "", ""),
    ("Selank", "TKPRPGP", "", ""),

    # === Fragmentos / metabólitos do método TRIAGEM XVI =================
    # Convenção: ponta cortada = ácido/amina livre; ponta preservada mantém
    # o grupo do parente (salvo FA/OH). Massas por construção a partir dos
    # parentes validados; confira contra seus padrões.
    ("Hexarelin (1-3)", "H[MeW]A", "", ""),
    ("Hexarelin (2-5)", "[MeW]AWF", "", ""),
    ("Hexarelin (4-6)", "WFK", "", "Amidation"),
    ("Alexamorelin (1-4)", "AH[MeW]A", "", ""),
    ("Alarelin (5-9)", "YALRP", "", "Ethylamide"),
    ("GHRP-1 (2-4) FA", "H[Nal]A", "", ""),
    ("GHRP-1 (3-7)", "[Nal]AWFK", "", "Amidation"),
    ("Dermorphin (1-4)", "YAFG", "", ""),
    ("GHRP-2 (1-3)", "A[Nal]A", "", ""),
    ("Leuprolide (5-9) OH", "YLLRP", "", ""),
    ("Triptorelin (5-10)", "YWLRPG", "", "Amidation"),
    ("GHRP-6 (2-6)", "WAWFK", "", "Amidation"),
    ("GHRP-6 (2-6) FA", "WAWFK", "", ""),
    ("GHRP-6 (2-5) FA", "WAWF", "", ""),
    ("Ipamorelin (1-4)", "[Aib]H[Nal]F", "", ""),
    ("Desmopressin (1-7)", "[Mpa]YFQNCP", "", "",
     '[[0, "Disulfide (-2H)"]]'),
    ("LHRH (2-10)", "HWSYGLRPG", "", "Amidation"),
    ("Goserelin (5-10)", "Y[SertBu]LRP", "", "Azaglycinamide"),
    ("Ipamorelin FA", "[Aib]H[Nal]FK", "", ""),
    ("GHRP-3 FA", "[Aib]WPIR", "", ""),
    ("GHRP-6 FA", "HWAWFK", "", ""),
    # -- Melanocortinas --
    ("Melanotan I (afamelanotide)", "SYS[Nle]EHFRWGKPV", "Acetyl", "Amidation"),
    ("Melanotan II (cyclic)", "[Nle]DHFRWK", "Acetyl", "Amidation",
     '[[1, "Lactam bridge"]]'),
    # -- Timosina β4 (43 aa) e TB-500 (seu fragmento ativo 17-23) --
    ("Thymosin beta-4 (43 aa)",
     "SDKPDMAEIEKFDKSKLKKTETQEKNPLPSKETIEQEKQAGES", "Acetyl", ""),
    ("TB-500 (Tbeta4 17-23)", "LKKTETQ", "Acetyl", ""),
    # -- CJC-1295 com DAC (Lys30 maleimidopropionila) --
    ("CJC-1295 with DAC", "YADAIFTQSYRKVLAQLSARKLLQDILSRK", "", "Amidation",
     '[[29, "Maleimidopropionyl (DAC)"]]'),
    # -- Corticotropinas (ACTH) --
    ("Tetracosactide (Synacthen, ACTH 1-24)",
     "SYSMEHFRWGKPVGKKRRPVKVYP", "", ""),
    ("ACTH 1-39 (corticotropin)",
     "SYSMEHFRWGKPVGKKRRPVKVYPNGAEDESAEAFPLEF", "", ""),
    # -- Ocitocina (ciclo Cys1-Cys6) --
    ("Oxytocin", "CYIQNCPLG", "", "Amidation",
     '[[0, "Disulfide (-2H)"]]'),
    # -- Melanocortina (PT-141) --
    ("PT-141 (bremelanotide)", "[Nle]DHFRWK", "Acetyl", "",
     '[[1, "Lactam bridge"]]'),
    # -- Timosina alfa --
    ("Thymosin alpha-1 (thymalfasin)",
     "SDAAVDTSSEITTKDLKEKKEVVEEAEN", "Acetyl", ""),
    # -- Pequenos reguladores --
    ("Epitalon (Epithalon)", "AEDG", "", ""),
    # -- IGF-1 e variantes (cadeia única, 3 pontes dissulfeto) --
    ("IGF-1 (mecasermin)",
     "GPETLCGAELVDALQFVCGDRGFYFNKPTGYGSSSRRAPQTGIVDECCFRSCDLRRLEMYCAPLKPAKSA",
     "", "",
     '[[5, "Disulfide (-2H)"], [46, "Disulfide (-2H)"], [51, "Disulfide (-2H)"]]'),
    ("IGF-1 LR3 (Long R3)",
     "MFPAMPLSSLFVNGPRTLCGAELVDALQFVCGDRGFYFNKPTGYGSSSRRAPQTGIVDECCFR"
     "SCDLRRLEMYCAPLKPAKSA",
     "", "",
     '[[18, "Disulfide (-2H)"], [59, "Disulfide (-2H)"], [64, "Disulfide (-2H)"]]'),
    # MGF: variante humana (...EERK); há forma sintética ...EEHK na literatura.
    ("MGF (IGF-1Ec, E-peptide 24 aa)",
     "YQPPSTNKNTKSQRRKGSTFEERK", "", ""),
    # -- Insulinas: DUAS cadeias (A/B) + 3 pontes dissulfeto --
    ("Human insulin",
     "GIVEQCCTSICSLYQLENYCN/FVNQHLCGSHLVEALYLVCGERGFFYTPKT", "", "",
     '[[5, "Disulfide (-2H)"], [10, "Disulfide (-2H)"], [27, "Disulfide (-2H)"]]'),
    ("Insulin lispro (Humalog)",
     "GIVEQCCTSICSLYQLENYCN/FVNQHLCGSHLVEALYLVCGERGFFYTKPT", "", "",
     '[[5, "Disulfide (-2H)"], [10, "Disulfide (-2H)"], [27, "Disulfide (-2H)"]]'),
    ("Insulin glargine (Lantus)",
     "GIVEQCCTSICSLYQLENYCG/FVNQHLCGSHLVEALYLVCGERGFFYTPKTRR", "", "",
     '[[5, "Disulfide (-2H)"], [10, "Disulfide (-2H)"], [27, "Disulfide (-2H)"]]'),
    ("Insulin aspart (NovoLog)",
     "GIVEQCCTSICSLYQLENYCN/FVNQHLCGSHLVEALYLVCGERGFFYTDKT", "", "",
     '[[5, "Disulfide (-2H)"], [10, "Disulfide (-2H)"], [27, "Disulfide (-2H)"]]'),
    ("Insulin glulisine (Apidra)",
     "GIVEQCCTSICSLYQLENYCN/FVKQHLCGSHLVEALYLVCGERGFFYTPET", "", "",
     '[[5, "Disulfide (-2H)"], [10, "Disulfide (-2H)"], [27, "Disulfide (-2H)"]]'),
    ("Insulin detemir (Levemir)",
     "GIVEQCCTSICSLYQLENYCN/FVNQHLCGSHLVEALYLVCGERGFFYTPK", "", "",
     '[[5, "Disulfide (-2H)"], [10, "Disulfide (-2H)"], [27, "Disulfide (-2H)"],'
     ' [49, "Myristoyl (K)"]]'),
    ("Insulin degludec (Tresiba)",
     "GIVEQCCTSICSLYQLENYCN/FVNQHLCGSHLVEALYLVCGERGFFYTPK", "", "",
     '[[5, "Disulfide (-2H)"], [10, "Disulfide (-2H)"], [27, "Disulfide (-2H)"],'
     ' [49, "Degludec"]]'),
    # -- Hormônio de crescimento (hGH) — 191 aa, 2 pontes dissulfeto (−4H) --
    ("Somatropin (hGH)",
     "FPTIPLSRLFDNAMLRAHRLHQLAFDTYQEFEEAYIPKEQKYSFLQNPQTSLCFSESIPTPSN"
     "REETQQKSNLELLRISLLLIQSWLEPVQFLRSVFANSLVYGASDSNVYDLLKDLEEGIQTLMG"
     "RLEDGSPRTGQIFKQTYSKFDTNSHNDDALLKNYGLLYCFRKDMDKVETFLRIVQCRSVEGSCGF",
     "", "",
     '[[52, "Disulfide (-2H)"], [181, "Disulfide (-2H)"]]'),
]

# Nomes de substancia sao sempre em ingles, em qualquer idioma da interface.
# Nome antigo em portugues -> nome atual, para bases ja semeadas.
PRESET_RENAMES = {
    "Liraglutida": "Liraglutide",
    "Semaglutida": "Semaglutide",
    "Tirzepatida": "Tirzepatide",
    "Retatrutida": "Retatrutide",
    "Gonadorelina (GnRH)": "Gonadorelin (GnRH)",
    "Triptorelina": "Triptorelin",
    "Leuprolida": "Leuprolide",
    "Nafarelina": "Nafarelin",
    "Buserelina": "Buserelin",
    "Goserelina": "Goserelin",
    "Deslorelina": "Deslorelin",
    "Fertirelina": "Fertirelin",
    "Alarelina": "Alarelin",
    "Histrelina": "Histrelin",
    "Lecirelina": "Lecirelin",
    "Vasopressina (Arg8)": "Vasopressin (Arg8)",
    "Lipressina (Lys8)": "Lypressin (Lys8)",
    "Felipressina": "Felypressin",
    "Desmopressina (dDAVP)": "Desmopressin (dDAVP)",
    "Terlipressina": "Terlipressin",
    "GHRP-2 (pralmorelina)": "GHRP-2 (pralmorelin)",
    "Hexarelina": "Hexarelin",
    "Ipamorelina": "Ipamorelin",
    "Alexamorelina": "Alexamorelin",
    "Grelina (acilada Ser3)": "Ghrelin (Ser3-acylated)",
    "Sermorelina (GHRH 1-29)": "Sermorelin (GHRH 1-29)",
    "Mod GRF 1-29 (CJC-1295 sem DAC)": "Mod GRF 1-29 (CJC-1295 without DAC)",
    "Tesamorelina (GHRH 1-44)": "Tesamorelin (GHRH 1-44)",
    "ARA-290 (cibinetida)": "ARA-290 (cibinetide)",
    "Dermorfina": "Dermorphin",
    "Hexarelina (1-3)": "Hexarelin (1-3)",
    "Hexarelina (2-5)": "Hexarelin (2-5)",
    "Hexarelina (4-6)": "Hexarelin (4-6)",
    "Alexamorelina (1-4)": "Alexamorelin (1-4)",
    "Alarelina (5-9)": "Alarelin (5-9)",
    "Dermorfina (1-4)": "Dermorphin (1-4)",
    "Leuprolida (5-9) OH": "Leuprolide (5-9) OH",
    "Triptorelina (5-10)": "Triptorelin (5-10)",
    "Ipamorelina (1-4)": "Ipamorelin (1-4)",
    "Desmopressina (1-7)": "Desmopressin (1-7)",
    "Goserelina (5-10)": "Goserelin (5-10)",
    "Ipamorelina FA": "Ipamorelin FA",
    "Melanotana I (afamelanotida)": "Melanotan I (afamelanotide)",
    "Melanotana II (cíclica)": "Melanotan II (cyclic)",
    "Timosina beta-4 (43 aa)": "Thymosin beta-4 (43 aa)",
    "CJC-1295 com DAC": "CJC-1295 with DAC",
    "Tetracosactídeo (Synacthen, ACTH 1-24)": "Tetracosactide (Synacthen, ACTH 1-24)",
    "ACTH 1-39 (corticotropina)": "ACTH 1-39 (corticotropin)",
    "Oxitocina": "Oxytocin",
    "PT-141 (bremelanotida)": "PT-141 (bremelanotide)",
    "Timosina alfa-1 (timalfasina)": "Thymosin alpha-1 (thymalfasin)",
    "IGF-1 (mecasermina)": "IGF-1 (mecasermin)",
    "MGF (IGF-1Ec, E-peptídeo 24aa)": "MGF (IGF-1Ec, E-peptide 24 aa)",
    "Insulina humana": "Human insulin",
    "Insulina lispro (Humalog)": "Insulin lispro (Humalog)",
    "Insulina glargina (Lantus)": "Insulin glargine (Lantus)",
    "Insulina asparte (NovoLog)": "Insulin aspart (NovoLog)",
    "Insulina glulisina (Apidra)": "Insulin glulisine (Apidra)",
    "Insulina detemir (Levemir)": "Insulin detemir (Levemir)",
    "Insulina degludec (Tresiba)": "Insulin degludec (Tresiba)",
    "Somatropina (hGH)": "Somatropin (hGH)",
}


def migrate_preset_names(db):
    """Renomeia uma unica vez os presets ja gravados, mantendo os dados da
    linha. Se o nome em ingles ja existir, o registro antigo fica como esta
    para nao sobrescrever nada do usuario."""
    if db.get_meta("preset_names_en"):
        return
    for old, new in PRESET_RENAMES.items():
        if db.get_peptide(old) and not db.get_peptide(new):
            db.rename_peptide(old, new)
    db.set_meta("preset_names_en", "1")
