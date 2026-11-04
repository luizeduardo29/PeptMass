# PeptMass

**Calculadora de massas moleculares e fragmentação MS/MS de peptídeos e proteínas**

Software desktop em Python + PyQt6 para cálculo de massas exatas, estados de
carga, séries teóricas de fragmentação MS/MS, modificações químicas e
aminoácidos não-naturais — com interface moderna e tema claro/escuro.

---

## Instalação

Requer **Python 3.10+**.

```bash
pip install -r requirements/desktop.txt
python run_desktop.py
```

No Windows, `scripts\run_desktop.bat` cria a venv e abre o programa.

---

## Versão web (Flask)

O PeptMass também roda no navegador, com o template dos outros módulos da Hub
(DopinGPT, DopingValidation, DegradationFinder) na cor **verde-limão**: tema claro e
escuro e idiomas **português, inglês e espanhol** (menu do globo no topo).
Usa o mesmo núcleo de cálculo e o mesmo banco do desktop.

```bash
pip install -r requirements/web.txt
python run_web.py            # http://127.0.0.1:8010
python tests/test_web.py     # verificação da versão web
```

Em container:

```bash
docker compose up -d --build # http://localhost:8010 (dados no volume peptmass_dados)
```

Telas: **Início**, **Massa** (Aba 1), **Fragmentação** (Aba 2), **Dados
experimentais** (Aba 3) e **Biblioteca** (aminoácidos não-naturais,
modificações e PubChem). O código fica em `peptmass/web/`, e as traduções em
`peptmass/web/locales/*.json`. No container, a leitura de `.raw` não está disponível
(o ThermoRawFileParser é um executável Windows); converta o arquivo para mzML antes.

---

## Arquitetura

```text
peptmass/
  core/             cálculo científico, sem interface
    constants.py        massas atômicas, isótopos, aminoácidos naturais
    formula_parser.py   fórmulas moleculares e massa de composição
    modifications.py    biblioteca de modificações
    custom_residues.py  aminoácidos não-naturais
    mass_calculator.py  sequência, massas, m/z e distribuição isotópica
    fragmentation.py    séries a/b/c/x/y/z, perdas neutras, matching
    scoring.py          escore de Morpheus e erro de massa
    identification.py   carga, ajuste isotópico e critérios de identificação
    presets.py          peptídeos pré-carregados
    workspace.py        banco + bibliotecas + calculadora (web e desktop)
    i18n.py             mensagens do núcleo e do desktop
  infra/            acesso externo
    database.py         SQLite local
    spectra_io.py       mzML, mzXML, .raw e centroidização
    pubchem.py          PubChem (PUG REST)
    exporters.py        CSV, XLSX, PDF, TXT, FASTA, Skyline
  web/              Flask
    __init__.py         create_app
    blueprints/         pages.py (telas) e api/ (mass, fragments, library, spectra)
    templates/  static/  locales/
  desktop/          PyQt6
    main_window.py      janela principal
    mass_tab.py, fragment_tab.py, experimental_tab.py
tests/              test_science.py, test_web.py, data/
packaging/          PyInstaller (peptmass.spec, build.bat, build.sh)
scripts/            atalhos do desktop no Windows
requirements/       desktop.txt, web.txt, build.txt
run_web.py          entrada web
run_desktop.py      entrada desktop
```

As dependências andam em um sentido: `web` e `desktop` usam `infra` e `core`;
`infra` usa `core`; `core` não conhece nenhuma interface.

---

## ABA 1 — Massa Molecular

- Entrada de sequência com **validação automática**.
- 20 aminoácidos naturais (massas monoisotópicas IUPAC).
- **Modificações**: N-terminal, C-terminal e por resíduo (Acetyl, PyroGlu,
  Formyl, Amidation, Oxidation, Phosphorylation, Carbamidomethyl, Deamidation,
  Sulfation e outras).
- Modificações **inline**: `PEPT(Phosphorylation)IDE`.
- **Múltiplas cadeias**: separe as cadeias com `/` — cada uma contribui com sua
  própria água terminal. Ex.: insulina = `GIVEQCC.../FVNQHLC...`. As pontes
  dissulfeto entram como a modificação `Disulfide (-2H)` em uma Cys por ponte.
  (A fragmentação MS/MS da Aba 2 não se aplica a múltiplas cadeias.)
- **Acilações de lisina dos análogos de GLP** (aplicáveis a `K`): cadeias laterais
  de liraglutida, semaglutida, tirzepatida e retatrutida — cada delta validado
  reconstruindo a fórmula do fármaco inteiro contra o PubChem.
- **Catálogo embutido** de resíduos não-naturais comuns, sempre disponíveis
  (não editáveis): Aib, pGlu, Mpa, Orn, Nle, Nva, Hyp, Cit, Sar, Abu, Dab,
  Dap, Pen, aMeLeu (α-metil-leucina), Nal (2-naftilalanina), MeW (2-metil-Trp),
  SertBu (O-terc-butil-Ser). Aparecem na tabela marcados como `embutido`.
- **Custom Amino Acids**: cadastro de resíduos não-naturais por fórmula
  molecular — massa calculada e armazenada em banco local.
  O **código pode ter de 1 a 3+ letras**; na sequência, resíduos multi-caractere
  vão **entre colchetes**: `A[Orn]G[Nle]K` (letra solta = aminoácido natural).
  Códigos de 1 letra continuam funcionando com ou sem colchetes.
- **Resíduos desconhecidos**: ao digitar uma sequência com um código não
  cadastrado (ex.: `[Aib]`), o botão *"Definir resíduo(s) desconhecido(s)…"*
  abre o cadastro assistido (com busca no PubChem) e salva na base.
- **Busca no PubChem**: pesquise por nome, CID ou fórmula e a fórmula molecular
  é preenchida automaticamente (com estrutura 2D e massas para conferência).
  Disponível no botão "🔍 PubChem" da barra de ferramentas e dentro dos
  diálogos de novo aminoácido e nova modificação. Requer conexão à internet.
- **Peptídeos salvos**: guarde a sequência + modificações (N/C-terminal e por
  resíduo) sob um nome no banco local e recarregue com um clique — não precisa
  redigitar. Já vêm **pré-carregados**, com massas validadas contra o PubChem:
  análogos de **GLP** (liraglutida, semaglutida, tirzepatida, retatrutida) e
  peptídeos de **controle antidopagem** (WADA S2): GnRH e agonistas
  (gonadorelina, triptorelina, leuprolida, nafarelina, buserelina, goserelina),
  GHRPs (GHRP-1, GHRP-2, GHRP-6, hexarelina, ipamorelina, alexamorelina),
  GHRH/GRF (sermorelina, Mod GRF 1-29, CJC-1295 com DAC, tesamorelina),
  hGH (somatropina), IGF-1, timosina β4 (43 aa) e seu fragmento ativo
  **TB-500** (Ac-LKKTETQ, resíduos 17–23), melanotanas I e II,
  nootrópicos (semax, selank), MOTS-c, vasopressina e análogos, ghrelina,
  BPC-157, ARA-290, corticotropinas (tetracosactídeo/Synacthen, ACTH 1-39),
  ocitocina, PT-141, timosina α1, epitalon, IGF-1 LR3, MGF, uma bateria de
  fragmentos/metabólitos do método de triagem, e as
  **insulinas** de duas cadeias (humana, lispro/Humalog, asparte/NovoLog,
  glulisina/Apidra, glargina/Lantus, detemir/Levemir, degludec/Tresiba).
- **Massa monoisotópica** e **massa média** (6 casas decimais).
- **Fórmula elementar** completa.
- **Tabela de estados de carga** (faixa configurável + extras como +15, +20).
- **Distribuição isotópica teórica** (gráfico).
- **Importação FASTA**.

Fórmula de m/z:

```
m/z = (M + z × 1.007276466812) / z
```

## ABA 2 — Fragmentação MS/MS

- Seleção de séries: **a, b, c, x, y, z** (e z• radical para ETD/ECD).
- **Perdas neutras**: −NH₃, −H₂O, −CO (combináveis).
- **Estados de carga** dos fragmentos: +1 a +5.
- Tabela ordenável com íon, carga, m/z, perda, massa neutra e subsequência.
- **Busca rápida** de fragmentos.
- **Matching** com lista experimental de m/z (tolerância em Da ou ppm).
- **Espectro teórico** (gráfico).
- **Exportação**: CSV, Excel (.xlsx), PDF, TXT e lista de transições Skyline.

## ABA 3 — Dados experimentais

Compara o espectro **teórico** (gerado na Aba 2) com um espectro **real** de um
arquivo de dados:

1. **Abrir arquivo**: `.mzML`, `.mzXML` ou `.raw` (Thermo).
2. **Filtro de scan** (estilo Xcalibur): escolha um dos filtros presentes no
   arquivo (`FTMS + p NSI Full ms`, `... Full ms2 ...@hcd27`, etc.) para
   restringir cromatograma, XIC e seleção de scan. Em DDA, a opção **agrupar**
   mascara o m/z do precursor, reduzindo milhares de filtros a poucos tipos.
3. **Cromatograma** por nível MS / filtro — **TIC** ou **XIC** (íon extraído:
   informe um m/z e a tolerância em Da). **Clique num ponto** para escolher o
   scan daquele tempo de retenção.
   - **Perfil × centroide**: marque *"abrir .raw em perfil"* para converter sem
     peak picking. Scans de perfil são detectados automaticamente, desenhados
     como **linha contínua**, e centroidados internamente (máximo local +
     refinamento parabólico no log) para o matching.
3. O **espectro do scan** é exibido.
4. **Casar com fragmentos**: anota os picos contra as séries teóricas e mostra um
   **gráfico espelhado** (experimental ↑ / teórico ↓) com os íons rotulados, mais
   uma tabela de anotação. O match considera automaticamente **perdas neutras**
   (−NH₃/−H₂O/−CO) e **múltiplas cargas** (1..z máx), com tolerância em Da ou ppm.
   Dê **duplo-clique** numa linha da tabela para ver o **XIC daquele íon**.
   - **Escore de identificação**: cada match recebe o **escore de Morpheus**
     (Wenger & Coon, *J. Proteome Res.* 2013) — nº de íons casados + fração da
     corrente iônica explicada — além da **cobertura** de íons e do **erro de
     massa** (mediano, máx e RMSE em ppm/Da) como controle de qualidade.
   - **Critérios de identificação (estilo WADA)**: avalia e sinaliza (✓/✗)
     **massa do precursor** (erro em ppm vs. o peptídeo da Aba 2), **tempo de
     retenção** (dentro da janela informada), **íons diagnósticos** (nº casados
     + abundância relativa na tabela) e **ajuste do envelope isotópico** do
     precursor (cosseno teórico × experimental, do MS1 anterior).
   - **Carga do precursor**: lida do arquivo ou **estimada automaticamente**
     pelo espaçamento do cluster isotópico (deconvolução).

Requer `pyteomics`, `psims` e `lxml` (já em `requirements/`). Para abrir
`.raw` diretamente é preciso o **ThermoRawFileParser**: aponte-o pela variável
de ambiente `PEPTMASS_THERMO_PARSER` (caminho do executável) ou coloque a pasta
`ThermoRawFileParser/` na raiz do projeto. Sem ele, converta o `.raw` para mzML
antes (ThermoRawFileParser ou msconvert).

Há um arquivo de teste `tests/data/exemplo_PEPTIDE.mzML` (sintético, com os íons b/y do
peptídeo PEPTIDE) para experimentar a aba sem dados próprios.

---

## Validação científica

`python tests/test_science.py` compara os cálculos com valores publicados
(PEPTIDE, bradicinina, angiotensina II, substância P, séries de fragmentos,
modificações) e confere os limites dos critérios de identificação. Os 19 testes
de referência passam dentro de tolerância de ±0.001 Da, e os 12 de critérios
também passam.

Padrões usados:
- Massas monoisotópicas IUPAC.
- Massa do próton = `1.007276466812`.
- Precisão de 6 casas decimais.
- Suporte a proteínas acima de 100 kDa (parsing < 5 ms).

---

## Interface

- Tema **claro** e **escuro** (alternável na barra de ferramentas).
- Tabelas ordenáveis e com cópia para a área de transferência
  (clique direito ou Ctrl+C na seleção).
- Atualização automática dos cálculos enquanto se digita.
- **Gráficos interativos** (espectro MS/MS e envelope isotópico): passe o mouse
  sobre os picos para ver íon, carga, m/z e subsequência; barra de navegação
  com zoom, pan, reset e exportar imagem.

---

## Empacotamento (executável)

O PeptMass pode ser empacotado num executável standalone com **PyInstaller**,
dispensando que o usuário final tenha Python instalado.

```bash
pip install -r requirements/build.txt
```

**Windows:**

```bat
packaging\build.bat              :: onedir em dist\PeptMass\PeptMass.exe
packaging\build.bat onefile      :: um único dist\PeptMass.exe
```

**macOS / Linux:**

```bash
chmod +x packaging/build.sh
packaging/build.sh             # gera dist/PeptMass/ (+ dist/PeptMass.app no macOS)
packaging/build.sh --onefile   # executável único
```

Ou diretamente, em qualquer plataforma:

```bash
pyinstaller packaging/peptmass.spec --noconfirm --clean
```

Detalhes:

- A receita está em [`packaging/peptmass.spec`](packaging/peptmass.spec); os
  scripts `build.bat` e `build.sh` criam uma venv de build isolada, rodam
  `tests/test_science.py` como rede de segurança e só então empacotam.
- **onedir** (padrão) é mais confiável e tem startup mais rápido; **onefile**
  (`PEPTMASS_ONEFILE=1`) gera um único arquivo, porém com startup mais lento e
  maior chance de falso-positivo de antivírus no Windows.
- O `.spec` coleta automaticamente os dados do `matplotlib` (backend QtAgg) e
  do `reportlab`, e exclui bindings Qt conflitantes (PyQt5/PySide).
- **Ícone (opcional):** coloque `peptmass.ico` (Windows) ou `peptmass.icns`
  (macOS) na raiz do projeto antes de empacotar — o `.spec` os detecta sozinho.
- O banco local continua em `~/.peptmass/peptmass.db`, criado em runtime — nada
  precisa ser embutido no pacote.
- O executável deve ser gerado **na plataforma de destino** (PyInstaller não faz
  cross-compile): builds Windows no Windows, builds macOS no macOS.
- **Distribuição**: no modo onedir, o resultado é a pasta `dist/PeptMass/`
  (executável + `_internal/`). Para levar a outro computador, **copie/zipe a
  pasta inteira** — o `PeptMass.exe` sozinho não roda. Não precisa de Python
  instalado no destino. Se a pasta `ThermoRawFileParser/` existir na raiz ao
  empacotar, ela é embutida e a leitura de `.raw` funciona sem instalar nada.

## Recursos avançados implementados

1. Distribuição isotópica teórica (convolução de padrões elementares).
2. Visualização gráfica do espectro teórico e do envelope isotópico.
3. Matching experimental × teórico (Da/ppm).
4. Importação FASTA.
5. Exportação compatível com Skyline (transition list).
6. Biblioteca editável de modificações customizadas.
7. Fórmulas elementares completas dos peptídeos.
8. Base para ETD/ECD (íon z•) e CID/HCD (perdas neutras).
