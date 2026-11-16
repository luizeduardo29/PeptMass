"""
i18n.py
=======
Alternância de idioma (Português / Inglês) para a interface do PeptMass.

Uso:
    from peptmass.core.i18n import t as _
    _("Massa Molecular")   -> "Molecular Mass" quando o idioma é 'en'

As chaves são as próprias strings em português; o inglês fica no mapa `_EN`.
Strings ainda não traduzidas caem no português (nunca quebram nem ficam vazias).
O idioma é lido no início a partir de `meta.language` no banco; o botão na
barra de ferramentas troca e aplica ao reabrir.
"""

import threading

_LANG = "pt"
# Idioma por thread: a versão web atende cada requisição numa thread e
# fixa o idioma dela com use_language(); o desktop usa só o global _LANG.
_local = threading.local()


def _norm(lang):
    lang = str(lang or "pt").lower()
    if lang.startswith("en"):
        return "en"
    if lang.startswith("es"):
        return "es"
    return "pt"


def set_language(lang):
    global _LANG
    _LANG = _norm(lang)


def use_language(lang):
    """Idioma só da thread atual (uma requisição web)."""
    _local.lang = _norm(lang)


def get_language():
    return getattr(_local, "lang", None) or _LANG


def t(s):
    """Traduz `s` para o idioma atual (identidade em português)."""
    lang = get_language()
    if lang == "en":
        return _EN.get(s, s)
    if lang == "es":
        return _ES.get(s, s)
    return s


# --------------------------------------------------------------------------
# Português -> Inglês
# --------------------------------------------------------------------------
_EN = {
    # ---- Janela / barra / abas ----
    "PeptMass 1.0 — Calculadora de Massas e Fragmentação":
        "PeptMass 1.0 — Mass & Fragmentation Calculator",
    "  Massa Molecular  ": "  Molecular Mass  ",
    "  Fragmentação MS/MS  ": "  MS/MS Fragmentation  ",
    "  Dados experimentais  ": "  Experimental Data  ",
    "☀ / ☾  Tema": "☀ / ☾  Theme",
    "Nova modificação…": "New modification…",
    "Sobre": "About",
    # botão de idioma: só "Idioma: PT" é exibido no modo EN (alvo = voltar p/ PT)
    "Idioma: PT": "Language: PT",
    "Pronto.  Massa do próton = {p}  |  massas IUPAC":
        "Ready.  Proton mass = {p}  |  IUPAC masses",
    # ---- Diálogo Sobre ----
    "Sobre o PeptMass": "About PeptMass",
    "Calculadora de massas moleculares e fragmentação MS/MS "
    "de peptídeos e proteínas.":
        "Molecular mass and MS/MS fragmentation calculator for peptides "
        "and proteins.",
    "Massas monoisotópicas IUPAC · próton = 1.007276466812 · "
    "precisão de 6 casas decimais.":
        "IUPAC monoisotopic masses · proton = 1.007276466812 · "
        "6-decimal precision.",
    "Séries a/b/c/x/y/z, perdas neutras, multicarga, "
    "modificações customizadas e aminoácidos não-naturais.":
        "a/b/c/x/y/z series, neutral losses, multicharge, custom "
        "modifications and non-natural amino acids.",
    # ---- Idioma / reinício ----
    "Idioma": "Language",
    "Idioma alterado para Inglês. Reinicie o PeptMass para aplicar.":
        "Language changed to English. Restart PeptMass to apply.",
    "Idioma alterado para Português. Reinicie o PeptMass para aplicar.":
        "Language changed to Portuguese. Restart PeptMass to apply.",
    # ---- Avisos / títulos comuns ----
    "Aviso": "Notice",
    "Erro": "Error",
    "Sucesso": "Success",
    "Salvo": "Saved",
    "Exportado": "Exported",
    "Exportar": "Export",
    "Remover": "Remove",
    "Sobrescrever": "Overwrite",
    "Matching": "Matching",
    "Posição": "Position",
    "Modificação": "Modification",
    "Salvar peptídeo": "Save peptide",
    "Selecionar sequência": "Select sequence",
    "Entradas FASTA:": "FASTA entries:",
    "Importar FASTA": "Import FASTA",
    "FASTA (*.fasta *.fa *.txt);;Todos (*)":
        "FASTA (*.fasta *.fa *.txt);;All (*)",
    "Resíduos cadastrados": "Residues registered",
    "Erro ao abrir": "Open error",
    "Erro ao ler scan": "Scan read error",
    "Dependência ausente": "Missing dependency",
    "Abrir dados de MS": "Open MS data",
    "Dados MS (*.mzML *.mzXML *.raw);;Todos (*)":
        "MS data (*.mzML *.mzXML *.raw);;All (*)",
    # ---- Diálogos: títulos ----
    "Novo aminoácido personalizado": "New custom amino acid",
    "Nova modificação customizada": "New custom modification",
    "Buscar molécula no PubChem": "Search molecule on PubChem",
    # ---- Diálogos: linhas de formulário ----
    "Nome:": "Name:",
    "Abreviação:": "Abbreviation:",
    "Código (1–3 letras):": "Code (1–3 letters):",
    "Fórmula molecular:": "Molecular formula:",
    "Fórmula (delta):": "Formula (delta):",
    "Posição:": "Position:",
    "Alvos:": "Targets:",
    "Nome IUPAC:": "IUPAC name:",
    "Fórmula:": "Formula:",
    "Massa média:": "Average mass:",
    # ---- Diálogos: placeholders ----
    "ex.: Aib, Orn (use [Aib] na sequência)":
        "e.g.: Aib, Orn (use [Aib] in the sequence)",
    "ex.: C4H9NO2 (aminoácido livre)": "e.g.: C4H9NO2 (free amino acid)",
    "delta elementar, ex.: C2H2O ou H-1N-1O":
        "elemental delta, e.g.: C2H2O or H-1N-1O",
    "resíduos alvo, ex.: STY  (vazio = qualquer)":
        "target residues, e.g.: STY  (empty = any)",
    "ex.: ornithine, citrulline, 6262, C5H12N2O2":
        "e.g.: ornithine, citrulline, 6262, C5H12N2O2",
    # ---- Diálogos: botões / status ----
    "🔍  Buscar no PubChem…": "🔍  Search PubChem…",
    "🔍  Buscar fórmula no PubChem…": "🔍  Search formula on PubChem…",
    "Buscar": "Search",
    "Usar esta fórmula": "Use this formula",
    "Resultado": "Result",
    "Massa monoisotópica do resíduo: —": "Residue monoisotopic mass: —",
    "Massa monoisotópica do resíduo: {m} Da": "Residue monoisotopic mass: {m} Da",
    "Massa monoisotópica do resíduo: (fórmula inválida)":
        "Residue monoisotopic mass: (invalid formula)",
    "Delta monoisotópico: —": "Monoisotopic delta: —",
    "Delta monoisotópico: {m} Da": "Monoisotopic delta: {m} Da",
    "Delta monoisotópico: (fórmula inválida)":
        "Monoisotopic delta: (invalid formula)",
    "Digite um termo e clique em Buscar.": "Type a term and click Search.",
    "Consultando o PubChem…": "Querying PubChem…",
    "✓ Encontrado. Revise e clique em 'Usar esta fórmula'.":
        "✓ Found. Review and click 'Use this formula'.",
    "Nome": "Name",
    "Fórmula": "Formula",
    # ---- Aba 1: Massa Molecular ----
    "Sequência de aminoácidos": "Amino acid sequence",
    "ex.: ACDEFGHIKLMNPQRSTVWY\n"
    "Não-naturais entre colchetes: A[Orn]G[Nle]K\n"
    "Modificações inline: PEPT(Phosphorylation)IDE":
        "e.g.: ACDEFGHIKLMNPQRSTVWY\n"
        "Non-natural in brackets: A[Orn]G[Nle]K\n"
        "Inline modifications: PEPT(Phosphorylation)IDE",
    "Definir resíduo(s) desconhecido(s)…": "Define unknown residue(s)…",
    "Definir resíduo(s) desconhecido(s): {x} …":
        "Define unknown residue(s): {x} …",
    "Importar FASTA…": "Import FASTA…",
    "Modificações": "Modifications",
    "N-terminal:": "N-terminal:",
    "C-terminal:": "C-terminal:",
    "Mod. por resíduo:": "Per-residue mod.:",
    "Adicionar mod. a resíduo…": "Add mod. to residue…",
    "Limpar": "Clear",
    "Código": "Code",
    "Abrev.": "Abbr.",
    "Tipo": "Type",
    "Novo…": "New…",
    "Peptídeos salvos": "Saved peptides",
    "Salvar atual…": "Save current…",
    "Carregar": "Load",
    "Resultado de massa": "Mass result",
    "Massa monoisotópica: —": "Monoisotopic mass: —",
    "Massa média: —": "Average mass: —",
    "Fórmula: —": "Formula: —",
    "Massa monoisotópica: {m} Da": "Monoisotopic mass: {m} Da",
    "Massa média: {m} Da": "Average mass: {m} Da",
    "Fórmula: {f}": "Formula: {f}",
    "Estados de carga (m/z)": "Charge states (m/z)",
    "z de": "z from",
    "até": "to",
    "extras:": "extras:",
    "Atualizar": "Update",
    "Distribuição isotópica teórica": "Theoretical isotopic distribution",
    "Carga do envelope:": "Envelope charge:",
    "m/z sobre os picos": "m/z over peaks",
    "(nenhuma)": "(none)",
    "M (neutro)": "M (neutral)",
    # ---- mass_calculator: validação / avisos ----
    "Resíduo(s) desconhecido(s): {x}": "Unknown residue(s): {x}",
    "Caractere(s) inválido(s): {x}": "Invalid character(s): {x}",
    "Sequência vazia.": "Empty sequence.",
    "Sequência válida.": "Valid sequence.",
    "Resíduo desconhecido: '{c}'": "Unknown residue: '{c}'",
    "Modificação desconhecida: '{m}'": "Unknown modification: '{m}'",
    "'{m}' normalmente não se aplica a {c}.":
        "'{m}' usually does not apply to {c}.",
    "'{m}' normalmente não se aplica a {c} (posição {p}).":
        "'{m}' usually does not apply to {c} (position {p}).",
    "{n} cadeias independentes: a fragmentação MS/MS não se "
    "aplica a múltiplas cadeias.":
        "{n} independent chains: MS/MS fragmentation does not apply "
        "to multiple chains.",
    "Composição com {el} negativo: verifique as modificações.":
        "Composition has negative {el}: check the modifications.",
    # ---- Aba 2: Fragmentação MS/MS ----
    "Peptídeo (da Aba 1)": "Peptide (from Tab 1)",
    "Nenhum peptídeo calculado.": "No peptide calculated.",
    "<b>{seq}</b>{extra}<br>Massa monoisotópica: {m} Da":
        "<b>{seq}</b>{extra}<br>Monoisotopic mass: {m} Da",
    "Séries de íons": "Ion series",
    "Perdas neutras": "Neutral losses",
    "Sem perdas": "No losses",
    "Estados de carga dos fragmentos": "Fragment charge states",
    "Matching com lista experimental de m/z":
        "Matching with experimental m/z list",
    "Cole valores de m/z (um por linha ou separados por vírgula)":
        "Paste m/z values (one per line or comma-separated)",
    "Tolerância:": "Tolerance:",
    "Casar": "Match",
    "Busca rápida de fragmentos (ex.: b5, y, 2+)…":
        "Quick fragment search (e.g.: b5, y, 2+)…",
    "Copiar seleção": "Copy selection",
    "Íon": "Ion",
    "Perda": "Loss",
    "Massa neutra": "Neutral mass",
    "Sequência": "Sequence",
    "Espectro teórico": "Theoretical spectrum",
    "Forneça m/z experimentais e gere fragmentos.":
        "Provide experimental m/z and generate fragments.",
    "{e} → {lbl} ({z}+)  erro {err} {unit}":
        "{e} → {lbl} ({z}+)  error {err} {unit}",
    "{a}/{b} casamentos:": "{a}/{b} matches:",
    "nenhum": "none",
    "Nenhum fragmento para exportar.": "No fragments to export.",
    "Fragmentos — {s}": "Fragments — {s}",
    "Fragmentos": "Fragments",
    "Fragmentos MS/MS": "MS/MS Fragments",
    "Peptídeo: {s}  M={m} Da": "Peptide: {s}  M={m} Da",
    "Arquivo salvo:\n{p}": "File saved:\n{p}",
    # ---- Aba 3: Dados experimentais ----
    "Abrir arquivo…": "Open file…",
    "abrir .raw em perfil": "open .raw in profile",
    "Converte o .raw sem peak picking (dados em perfil). "
    "Arquivos ficam bem maiores.":
        "Converts .raw without peak picking (profile data). "
        "Files get much larger.",
    "Nenhum arquivo aberto.": "No file open.",
    "Nível MS:": "MS level:",
    "Filtro de scan:": "Scan filter:",
    "agrupar (ignorar m/z do precursor)": "group (ignore precursor m/z)",
    "Cromatograma — clique para escolher o scan":
        "Chromatogram — click to choose the scan",
    "XIC m/z:": "XIC m/z:",
    "ex.: 800.3672": "e.g.: 800.3672",
    "Mostrar XIC": "Show XIC",
    "Scan: —": "Scan: —",
    "Scan {lbl}": "Scan {lbl}",
    "  [perfil: {n} picos]": "  [profile: {n} peaks]",
    "{p}  —  {n} íons anotados": "{p}  —  {n} annotated ions",
    "Tol.:": "Tol.:",
    "Casar com fragmentos": "Match with fragments",
    "Séries:": "Series:",
    "perdas neutras": "neutral losses",
    "Cargas:": "Charges:",
    "ver em perfil": "profile view",
    "Desenha o espectro como linha contínua (perfil) em vez de picos "
    "(centroide). Marcado automaticamente quando o scan é de perfil.":
        "Draws the spectrum as a continuous line (profile) instead of peaks "
        "(centroid). Checked automatically when the scan is profile.",
    "Carga precursor:": "Precursor charge:",
    "RT esperado (min):": "Expected RT (min):",
    "± janela:": "± window:",
    "Teór m/z": "Theor m/z",
    "(todos os scans)": "(all scans)",
    "{base} — {n} scans": "{base} — {n} scans",
    "Informe um m/z válido para o XIC.": "Enter a valid m/z for the XIC.",
    "Score (Morpheus): {score}   |   {n} íons casados   |   "
    "{tic}% da TIC explicada   |   cobertura {cov}%   |   "
    "erro mediano {med} {unit} (máx {mx}, RMSE {rmse})":
        "Score (Morpheus): {score}   |   {n} matched ions   |   "
        "{tic}% of TIC explained   |   coverage {cov}%   |   "
        "median error {med} {unit} (max {mx}, RMSE {rmse})",
    "Critérios:": "Criteria:",
    "precursor {e} ppm (z={z})": "precursor {e} ppm (z={z})",
    "RT Δ{d} min": "RT Δ{d} min",
    "{n} íons diagnósticos": "{n} diagnostic ions",
    "isótopos {f}": "isotopes {f}",
    # ---- Caixas de diálogo (QMessageBox / QInputDialog) ----
    "Insira a sequência primeiro.": "Enter the sequence first.",
    "Resíduo a modificar:": "Residue to modify:",
    "Modificação para {r}:": "Modification for {r}:",
    "Definir resíduo '{c}' (via PubChem)": "Define residue '{c}' (via PubChem)",
    "Salvos na base de dados e disponíveis nas sequências:\n{x}":
        "Saved to the database and available in sequences:\n{x}",
    "Aminoácido '{c}' cadastrado e disponível nas sequências.":
        "Amino acid '{c}' registered and available in sequences.",
    "'{c}' é um resíduo embutido e não pode ser removido.":
        "'{c}' is a built-in residue and cannot be removed.",
    "A sequência está vazia — nada a salvar.":
        "The sequence is empty — nothing to save.",
    "Já existe '{n}'. Substituir?": "'{n}' already exists. Replace?",
    "Peptídeo '{n}' salvo na base.": "Peptide '{n}' saved to the database.",
    "Remover '{n}' da base?": "Remove '{n}' from the database?",
    "Aminoácido '{c}' criado a partir do PubChem.":
        "Amino acid '{c}' created from PubChem.",
    "Fórmula inválida: {e}": "Invalid formula: {e}",
    "Modificação '{n}' adicionada.": "Modification '{n}' added.",
    # ---- formula_parser / custom_residues / pubchem ----
    "Fórmula vazia.": "Empty formula.",
    "Parênteses desbalanceados.": "Unbalanced parentheses.",
    "Caractere inesperado em '{f}' posição {i}: '{c}'":
        "Unexpected character in '{f}' at position {i}: '{c}'",
    "Elemento desconhecido: '{el}'": "Unknown element: '{el}'",
    "Elemento sem massa tabelada: '{el}'": "Element without tabulated mass: '{el}'",
    "Nome obrigatório.": "Name is required.",
    "O código deve ter de 1 a 10 caracteres.":
        "The code must have 1 to 10 characters.",
    "O código deve conter apenas letras (sem dígitos ou símbolos). "
    "Ex.: Aib, Orn, Nle.":
        "The code must contain letters only (no digits or symbols). "
        "E.g.: Aib, Orn, Nle.",
    "O código '{c}' já pertence a um aminoácido natural.":
        "The code '{c}' already belongs to a natural amino acid.",
    "O código '{c}' já está em uso.": "The code '{c}' is already in use.",
    "Não foi possível interpretar a fórmula '{f}'.":
        "Could not interpret the formula '{f}'.",
    "Composto não encontrado no PubChem.": "Compound not found on PubChem.",
    "Erro HTTP {c} do PubChem.": "HTTP error {c} from PubChem.",
    "Sem conexão com o PubChem: {e}": "No connection to PubChem: {e}",
    "Nenhuma propriedade retornada.": "No properties returned.",
    "CID não encontrado.": "CID not found.",
    "Não foi possível obter a imagem: {e}": "Could not fetch the image: {e}",
    # ---- Desktop no visual do site (topo, títulos e cartões) ----
    "Massa": "Mass",
    "Fragmentação": "Fragmentation",
    "Dados experimentais": "Experimental data",
    "Massa molecular": "Molecular mass",
    "O cálculo é refeito enquanto você digita. O peptídeo fica disponível "
    "nas telas de Fragmentação e Dados experimentais.":
        "The calculation updates as you type. The peptide is available on "
        "the Fragmentation and Experimental data screens.",
    "Fragmentação MS/MS": "MS/MS fragmentation",
    "Séries teóricas do peptídeo da tela de Massa. Marque séries, perdas e "
    "cargas; a tabela e o espectro se atualizam na hora.":
        "Theoretical series of the peptide from the Mass screen. Tick series, "
        "losses and charges; the table and the spectrum update right away.",
    "Compare o espectro teórico com um espectro real: abra o arquivo, "
    "escolha o scan no cromatograma e case com os fragmentos do peptídeo "
    "da tela de Massa.":
        "Compare the theoretical spectrum with a real one: open the file, "
        "pick the scan on the chromatogram and match it against the "
        "fragments of the peptide from the Mass screen.",
    "Massas e fragmentação MS/MS de peptídeos":
        "Peptide masses and MS/MS fragmentation",
    "Biblioteca": "Library",
    "Novo aminoácido…": "New amino acid…",
    "Buscar no PubChem…": "Search PubChem…",
    "Modo de cor": "Color mode",
    "Claro": "Light",
    "Escuro": "Dark",
    "Massas monoisotópicas IUPAC · próton = {p} Da · 6 casas decimais · v1.0":
        "IUPAC monoisotopic masses · proton = {p} Da · 6 decimal places · v1.0",
    "Aminoácidos não naturais": "Non-natural amino acids",
    "Mono (Da)": "Mono (Da)",
    "N-terminal": "N-terminal",
    "C-terminal": "C-terminal",
    "Modificações por resíduo": "Per-residue modifications",
    "Extras": "Extra",
    "Carga do envelope": "Envelope charge",
    "0 = massa neutra (M). Passe o mouse sobre os picos; use a lupa para dar "
    "zoom e a casa para voltar.":
        "0 = neutral mass (M). Hover over the peaks; use the magnifier to "
        "zoom and the house to go back.",
    "m/z (neutro)": "m/z (neutral)",
    "Intensidade (%)": "Intensity (%)",
    "Massa monoisotópica": "Monoisotopic mass",
    "Massa média": "Average mass",
    "Resíduos": "Residues",
    "Peptídeo": "Peptide",
    "Editar na tela de Massa": "Edit on the Mass screen",
    "Busca rápida (ex.: b5, y, 2+, -H2O)…": "Quick search (e.g. b5, y, 2+, -H2O)…",
    "Intensidade rel.": "Rel. intensity",
    "{a} de {b} fragmentos": "{a} of {b} fragments",
    "Arquivo de MS": "MS file",
    "Arquivo (.mzML, .mzXML ou .raw)": "File (.mzML, .mzXML or .raw)",
    "Nível MS": "MS level",
    "Filtro de scan": "Scan filter",
    "Cromatograma": "Chromatogram",
    "Clique num ponto do cromatograma para escolher o scan daquele tempo "
    "de retenção.":
        "Click a point on the chromatogram to pick the scan at that retention time.",
    "Espectro do scan": "Scan spectrum",
    "nenhum scan": "no scan",
    "Séries": "Series",
    "Cargas": "Charges",
    "Tolerância": "Tolerance",
    "Carga precursor": "Precursor charge",
    "RT esperado (min)": "Expected RT (min)",
    "± janela": "± window",
    "Critérios de identificação": "Identification criteria",
    "Duplo-clique numa linha para ver o XIC daquele íon.":
        "Double-click a row to see the XIC of that ion.",
    "Copiar": "Copy",
    "Abund.%": "Abund.%",
    "Subseq": "Subseq.",
    "{base} · {n} scans": "{base} · {n} scans",
    "{p} · {n} íons anotados": "{p} · {n} ions annotated",
    "{f}   —   {n} scans": "{f}   —   {n} scans",
    "Para abrir .raw é preciso o leitor ThermoRawFileParser, que não vem "
    "com o PeptMass. No programa para Windows, use o botão \"Instalar "
    "leitor de .raw\" desta tela. Outra opção: converta o .raw para "
    "mzML e abra o mzML.":
        "Opening .raw files requires the ThermoRawFileParser reader, which "
        "is not shipped with PeptMass. In the Windows program, use the "
        "\"Install .raw reader\" button on this screen. Alternatively, "
        "convert the .raw file to mzML and open the mzML.",
    "Não foi possível baixar o leitor de .raw: {e}":
        "Could not download the .raw reader: {e}",
    "O download do leitor de .raw veio maior que o esperado.":
        "The .raw reader download was larger than expected.",
    "O arquivo baixado não confere com a versão oficial do leitor de .raw. "
    "Nada foi instalado.":
        "The downloaded file does not match the official .raw reader "
        "release. Nothing was installed.",
    "Pacote do leitor de .raw inválido.": "Invalid .raw reader package.",
    "Baixe o leitor de .raw antes de instalar.":
        "Download the .raw reader before installing.",
}


# --------------------------------------------------------------------------
# Português -> Espanhol (só as mensagens do núcleo: cálculo, fórmulas,
# resíduos e PubChem; a interface web tem o próprio catálogo em peptmass/web/locales)
# --------------------------------------------------------------------------
_ES = {
    "Resíduo(s) desconhecido(s): {x}": "Residuo(s) desconocido(s): {x}",
    "Caractere(s) inválido(s): {x}": "Carácter(es) no válido(s): {x}",
    "Sequência vazia.": "Secuencia vacía.",
    "Sequência válida.": "Secuencia válida.",
    "Resíduo desconhecido: '{c}'": "Residuo desconocido: '{c}'",
    "Modificação desconhecida: '{m}'": "Modificación desconocida: '{m}'",
    "'{m}' normalmente não se aplica a {c}.":
        "'{m}' normalmente no se aplica a {c}.",
    "'{m}' normalmente não se aplica a {c} (posição {p}).":
        "'{m}' normalmente no se aplica a {c} (posición {p}).",
    "{n} cadeias independentes: a fragmentação MS/MS não se "
    "aplica a múltiplas cadeias.":
        "{n} cadenas independientes: la fragmentación MS/MS no se "
        "aplica a múltiples cadenas.",
    "Composição com {el} negativo: verifique as modificações.":
        "Composición con {el} negativo: revise las modificaciones.",
    "Fórmula inválida: {e}": "Fórmula no válida: {e}",
    "Fórmula vazia.": "Fórmula vacía.",
    "Parênteses desbalanceados.": "Paréntesis desbalanceados.",
    "Caractere inesperado em '{f}' posição {i}: '{c}'":
        "Carácter inesperado en '{f}' posición {i}: '{c}'",
    "Elemento desconhecido: '{el}'": "Elemento desconocido: '{el}'",
    "Elemento sem massa tabelada: '{el}'": "Elemento sin masa tabulada: '{el}'",
    "Nome obrigatório.": "El nombre es obligatorio.",
    "O código deve ter de 1 a 10 caracteres.":
        "El código debe tener de 1 a 10 caracteres.",
    "O código deve conter apenas letras (sem dígitos ou símbolos). "
    "Ex.: Aib, Orn, Nle.":
        "El código debe contener solo letras (sin dígitos ni símbolos). "
        "Ej.: Aib, Orn, Nle.",
    "O código '{c}' já pertence a um aminoácido natural.":
        "El código '{c}' ya pertenece a un aminoácido natural.",
    "O código '{c}' já está em uso.": "El código '{c}' ya está en uso.",
    "Não foi possível interpretar a fórmula '{f}'.":
        "No se pudo interpretar la fórmula '{f}'.",
    "Composto não encontrado no PubChem.": "Compuesto no encontrado en PubChem.",
    "Erro HTTP {c} do PubChem.": "Error HTTP {c} de PubChem.",
    "Sem conexão com o PubChem: {e}": "Sin conexión con PubChem: {e}",
    "Nenhuma propriedade retornada.": "No se devolvió ninguna propiedad.",
    "CID não encontrado.": "CID no encontrado.",
    "Não foi possível obter a imagem: {e}": "No se pudo obtener la imagen: {e}",
    "Para abrir .raw é preciso o leitor ThermoRawFileParser, que não vem "
    "com o PeptMass. No programa para Windows, use o botão \"Instalar "
    "leitor de .raw\" desta tela. Outra opção: converta o .raw para "
    "mzML e abra o mzML.":
        "Para abrir .raw se necesita el lector ThermoRawFileParser, que no "
        "viene con PeptMass. En el programa para Windows, use el botón "
        "\"Instalar lector de .raw\" de esta pantalla. Otra opción: "
        "convierta el .raw a mzML y abra el mzML.",
    "Não foi possível baixar o leitor de .raw: {e}":
        "No se pudo descargar el lector de .raw: {e}",
    "O download do leitor de .raw veio maior que o esperado.":
        "La descarga del lector de .raw fue mayor de lo esperado.",
    "O arquivo baixado não confere com a versão oficial do leitor de .raw. "
    "Nada foi instalado.":
        "El archivo descargado no coincide con la versión oficial del lector "
        "de .raw. No se instaló nada.",
    "Pacote do leitor de .raw inválido.": "Paquete del lector de .raw no válido.",
    "Baixe o leitor de .raw antes de instalar.":
        "Descargue el lector de .raw antes de instalar.",
}
