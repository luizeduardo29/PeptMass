# PeptMass

**Calculadora de massas moleculares e fragmentação MS/MS de peptídeos e proteínas**

Software em Python para cálculo de massas exatas, estados de carga, séries
teóricas de fragmentação MS/MS, modificações químicas, aminoácidos
não-naturais e anotação de espectros experimentais (`.mzML`, `.mzXML` e `.raw`
da Thermo), com tema claro/escuro e interface em português, inglês e espanhol.

Licença: [GPL-3.0](LICENSE).

---

## Como usar: escolha uma das três formas

As três formas têm **as mesmas telas e as mesmas funções**. Escolha a mais
simples para o seu caso:

| Forma | Sistema | Precisa instalar | Para quem |
|---|---|---|---|
| [**1. Programa para Windows (.exe)**](#1-programa-para-windows-exe) | Windows 10 ou 11 (64 bits) | Nada | Quem só quer usar o programa |
| [**2. Docker**](#2-docker-windows-macos-e-linux) | Windows, macOS (inclusive M1 ou mais novo) e Linux | Docker | macOS e Linux, ou um servidor para a equipe na rede |
| [**3. Python (código-fonte)**](#3-python-código-fonte) | Qualquer um com Python 3.10+ | Python | Quem vai estudar ou alterar o código |

---

## 1. Programa para Windows (.exe)

Não precisa de Python nem de nenhuma outra instalação.

1. Na página do projeto no GitHub, abra **Releases** (à direita) e baixe o
   arquivo `PeptMass-<versão>-Windows.zip` (cerca de 220 MB).
2. Clique com o botão direito no `.zip` → **Extrair tudo…** e escolha uma
   pasta (por exemplo, `Documentos\PeptMass`). Não abra o programa de dentro do
   `.zip`: extraia antes.
3. Na pasta extraída, abra **`PeptMass\PeptMass.exe`** (duplo clique). A
   janela do PeptMass abre em alguns segundos.

> **Aviso "O Windows protegeu o computador".** Na primeira vez, o Windows
> pode mostrar essa tela azul (SmartScreen), porque o programa ainda não tem
> assinatura digital de uma empresa. Para abrir:
> clique em **Mais informações** → **Executar assim mesmo**. O aviso não volta
> nas próximas vezes. Se o antivírus da instituição bloquear o programa, peça
> ao suporte de TI para liberar a pasta do PeptMass.

**Mantenha a pasta inteira.** O `PeptMass.exe` precisa da pasta `_internal`
que está ao lado dele. Para levar o programa a outro computador, copie a pasta
`PeptMass` inteira. Para criar um atalho, clique com o botão direito no
`PeptMass.exe` → **Mostrar mais opções** → **Enviar para** → **Área de
trabalho (criar atalho)**.

**Abrir arquivos `.raw` da Thermo.** O programa não traz o leitor de `.raw`
(ThermoRawFileParser), porque a licença da biblioteca da Thermo não permite
distribuí-lo junto com o PeptMass. Para instalar, uma única vez:

1. Abra a tela **Dados experimentais**.
2. Clique em **Instalar leitor de .raw** (precisa de internet).
3. Leia a licença da Thermo que aparece e clique em **Aceito e instalar**.

O PeptMass baixa a versão oficial do
[ThermoRawFileParser](https://github.com/compomics/ThermoRawFileParser), confere
que o arquivo é o original (SHA-256) e só instala se você aceitar. Se recusar,
nada fica no computador. Arquivos `.mzML` e `.mzXML` abrem sem o leitor.

**Onde ficam os dados.** Peptídeos salvos, aminoácidos e modificações
cadastrados ficam em `C:\Users\<seu usuário>\.peptmass\peptmass.db`, junto com
o leitor de `.raw` (se instalado). Atualizar o programa (baixar um `.zip` novo)
não apaga esses dados.

**Atualizar.** Baixe o `.zip` da nova versão em Releases, extraia e use a nova
pasta. A pasta antiga pode ser apagada.

**Desinstalar.** Apague a pasta do programa. Para apagar também os dados,
apague a pasta `C:\Users\<seu usuário>\.peptmass`.

---

## 2. Docker (Windows, macOS e Linux)

O Docker roda o PeptMass num "container" e você usa o programa pelo navegador.
O container **já traz o leitor de `.raw`**: não é preciso instalar mais nada.

### 2.1 Instalar o Docker (uma vez)

- **Windows e macOS:** instale o
  [Docker Desktop](https://www.docker.com/products/docker-desktop/) e abra-o.
  Espere o ícone da baleia indicar que o Docker está rodando. No Windows, o
  instalador pode pedir para ativar o WSL 2 e reiniciar o computador.
- **Mac com chip Apple (M1 ou mais novo):** o leitor de `.raw` só existe para
  processadores Intel/AMD (amd64), então o Docker Desktop roda o PeptMass pela
  emulação Rosetta. Se o Docker pedir, aceite instalar o Rosetta; em
  **Settings → General**, deixe marcada a opção *Use Rosetta for x86_64/amd64
  emulation on Apple Silicon*.
- **Linux:** instale o [Docker Engine](https://docs.docker.com/engine/install/)
  com o plugin `docker compose`. Para não precisar de `sudo`:
  `sudo usermod -aG docker $USER` e entre de novo na sessão.

Para conferir, abra um terminal (no Windows, o **PowerShell**) e rode:

```bash
docker compose version
```

### 2.2 Baixar o PeptMass

Com git:

```bash
git clone https://github.com/luizeduardo29/PeptMass.git
cd PeptMass
```

Sem git: na página do projeto no GitHub, clique em **Code → Download ZIP**,
extraia o `.zip` e abra o terminal dentro da pasta extraída (a que tem o
arquivo `docker-compose.yml`).

### 2.3 Subir o PeptMass

Dentro da pasta do projeto:

```bash
docker compose up -d --build
```

A primeira vez demora alguns minutos (baixa e monta a imagem, cerca de 900 MB).
Depois, abra no navegador: **<http://localhost:8010>**

O container fica rodando em segundo plano e volta sozinho quando o Docker
reinicia (por exemplo, depois de religar o computador).

### 2.4 Comandos do dia a dia

Rode todos dentro da pasta do projeto.

| Para | Comando |
|---|---|
| Ver se está rodando | `docker compose ps` |
| Parar (os dados ficam guardados) | `docker compose stop` |
| Iniciar de novo | `docker compose start` |
| Ver o registro (log) | `docker compose logs -f` (Ctrl+C sai) |
| Atualizar para a versão nova | `git pull` (ou baixe o ZIP novo) e depois `docker compose up -d --build` |
| Remover o container (os dados ficam) | `docker compose down` |
| Remover o container **e apagar os dados** | `docker compose down -v` |
| Copiar o banco para a pasta atual (backup) | `docker compose cp peptmass:/data/peptmass.db ./peptmass.db` |

### 2.5 Ajustes

As opções vão antes do comando (Linux e macOS) ou num arquivo `.env` na pasta
do projeto (qualquer sistema, inclusive Windows), uma por linha, por exemplo
`PORTA_HOST=8020`.

| Variável | Padrão | O que faz |
|---|---|---|
| `PORTA_HOST` | `8010` | Porta no computador. Use outra se a 8010 estiver ocupada. |
| `PEPTMASS_MAX_UPLOAD_MB` | `4096` | Tamanho máximo de arquivo de MS enviado, em MB. |
| `MEM_LIMIT` | `2g` | Memória máxima do container. Aumente para arquivos `.raw` grandes em perfil. |
| `PEPTMASS_INSTANCIA` | `peptmass` | Nome da instância (e do volume com os dados). |

Exemplo (Linux/macOS): `PORTA_HOST=8020 docker compose up -d`.

**Usar de outros computadores da rede.** O container aceita conexões da rede:
os colegas abrem `http://<IP do seu computador>:8010`. No Windows, pode ser
preciso liberar a porta 8010 no Firewall do Windows. O PeptMass **não tem
login**: deixe-o acessível só na rede interna, nunca direto na internet.

**Rodar duas instâncias** (por exemplo, uma por equipe, cada uma com seu
próprio banco): dê outro nome e outra porta à segunda.

```bash
PEPTMASS_INSTANCIA=peptmass2 PORTA_HOST=8011 docker compose up -d
```

No Windows (PowerShell):

```powershell
$env:PEPTMASS_INSTANCIA="peptmass2"; $env:PORTA_HOST="8011"; docker compose up -d
```

Para parar ou atualizar essa segunda instância, use o mesmo
`PEPTMASS_INSTANCIA` nos comandos.

**Onde ficam os dados.** No volume do Docker `peptmass_dados` (ou
`<instância>_dados`). Ele sobrevive a `stop`, `down`, atualizações e
reinícios; só `docker compose down -v` o apaga. Os arquivos de MS enviados são
temporários: saem do disco quando o arquivo é fechado (o PeptMass mantém até 3
abertos) e quando o container reinicia.

---

## 3. Python (código-fonte)

Requer **Python 3.10 ou mais novo**
([python.org](https://www.python.org/downloads/); no Windows, marque *Add
python.exe to PATH* na instalação).

```bash
git clone https://github.com/luizeduardo29/PeptMass.git
cd PeptMass
python -m venv .venv
# Windows:      .venv\Scripts\activate
# Linux/macOS:  source .venv/bin/activate
```

**No navegador** (a mesma versão do container):

```bash
pip install -r requirements/web.txt
python run_web.py                         # http://127.0.0.1:8010, só neste computador
python run_web.py --host 0.0.0.0          # também para a rede (sem login: só rede interna)
python run_web.py --port 8020             # outra porta
```

**Numa janela própria** (o mesmo programa do `.exe`):

```bash
pip install -r requirements/desktop.txt
python run_desktop.py
```

No Windows, `scripts\run_desktop.bat` faz tudo isso com um duplo clique: na
primeira vez cria a `.venv` e instala as dependências.

Variáveis de ambiente:

| Variável | Padrão | O que faz |
|---|---|---|
| `PEPTMASS_HOST` / `PEPTMASS_PORT` | `127.0.0.1` / `8010` | Endereço do `run_web.py` (o mesmo que `--host` / `--port`). |
| `PEPTMASS_DATA_DIR` | `~/.peptmass` | Pasta do banco e dos envios temporários. |
| `PEPTMASS_MAX_UPLOAD_MB` | `4096` | Tamanho máximo de arquivo de MS enviado, em MB. |
| `PEPTMASS_THERMO_PARSER` | — | Caminho do `ThermoRawFileParser.exe`, para abrir `.raw`. |

Para abrir `.raw` rodando pelo Python, instale o
[ThermoRawFileParser](https://github.com/compomics/ThermoRawFileParser) e
coloque a pasta `ThermoRawFileParser/` na raiz do projeto ou em `~/.peptmass/`,
ou aponte `PEPTMASS_THERMO_PARSER`. No Windows basta o .NET Framework (já vem
no Windows 10/11); no Linux e no macOS é preciso o `mono`. O botão **Instalar
leitor de .raw** aparece apenas no programa para Windows (`run_desktop.py` /
`.exe`).

---

## Problemas comuns

| Sintoma | Solução |
|---|---|
| "O Windows protegeu o computador" ao abrir o `.exe` | **Mais informações** → **Executar assim mesmo** (ver seção 1). |
| O `.exe` não abre ou fecha logo | Extraia o `.zip` inteiro antes (não rode de dentro dele) e não separe o `PeptMass.exe` da pasta `_internal`. |
| "Para abrir .raw é preciso o leitor ThermoRawFileParser…" | No `.exe`: botão **Instalar leitor de .raw** na tela Dados experimentais. Pelo Python: ver seção 3. Ou converta o `.raw` para mzML (msconvert ou ThermoRawFileParser). |
| Falha ao baixar o leitor de `.raw` | Precisa de internet com acesso ao GitHub. Em redes com bloqueio, tente de outra rede ou peça liberação de `github.com`. |
| "… passa do limite de envio deste servidor" | Aumente `PEPTMASS_MAX_UPLOAD_MB` (seção 2.5) e suba de novo com `docker compose up -d`. |
| `.raw` grande em perfil falha no Docker | Aumente `MEM_LIMIT` (por exemplo, `4g`). |
| `docker compose up` diz que a porta 8010 está ocupada | Use outra porta: `PORTA_HOST=8020` (seção 2.5). |
| `docker: command not found` / "Cannot connect to the Docker daemon" | Abra o Docker Desktop (Windows/macOS) ou inicie o serviço (`sudo systemctl start docker` no Linux). |
| Colegas não conseguem abrir pela rede | Use o IP do computador (não `localhost`) e libere a porta no firewall. Pelo Python, suba com `--host 0.0.0.0`. |
| A busca no PubChem falha | Precisa de internet com acesso a `pubchem.ncbi.nlm.nih.gov`. |

---

## Telas

**Início**, **Massa** (Aba 1), **Fragmentação** (Aba 2), **Dados
experimentais** (Aba 3), **Biblioteca** (aminoácidos não-naturais,
modificações e PubChem) e **Como usar** (demonstrações interativas). A tela
Como usar abre um arquivo de exemplo
(`peptmass/web/static/exemplos/exemplo_PEPTIDE.mzML`) para experimentar a Aba 3
sem dados próprios.

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
  desktop/          janela do executável
    app.py              servidor interno + interface web num QWebEngineView
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

A leitura usa `pyteomics`, `psims` e `lxml` (já em `requirements/`). O `.raw`
é convertido para mzML pelo **ThermoRawFileParser** 1.4.5. O container já o
traz (imagem oficial do Bioconda). O executável do Windows **não** o traz,
porque a licença da biblioteca da Thermo (RawFileReader) restringe
distribuí-la junto com software GPL: o próprio usuário o obtém pelo botão
**Instalar leitor de .raw**, que baixa o pacote oficial
([github.com/compomics/ThermoRawFileParser](https://github.com/compomics/ThermoRawFileParser)),
confere o SHA-256, mostra a licença da Thermo e só instala (em
`~/.peptmass/ThermoRawFileParser/`) se ele aceitar. O PeptMass procura o
conversor, nesta ordem, em `PEPTMASS_THERMO_PARSER`, numa pasta
`ThermoRawFileParser/` ao lado do `PeptMass.exe`, na raiz do projeto, em
`~/.peptmass/` e no `PATH`. O mzML convertido fica na pasta do envio e é
apagado quando o arquivo é fechado.

O arquivo de exemplo `peptmass/web/static/exemplos/exemplo_PEPTIDE.mzML` é
sintético, com os íons b/y do peptídeo PEPTIDE.

---

## Validação científica

Os cálculos foram conferidos contra valores publicados (PEPTIDE, bradicinina,
angiotensina II, substância P, séries de fragmentos, modificações), dentro de
±0.001 Da, e os limites dos critérios de identificação também foram
verificados.

Padrões usados:
- Massas monoisotópicas IUPAC.
- Massa do próton = `1.007276466812`.
- Precisão de 6 casas decimais.
- Suporte a proteínas acima de 100 kDa (parsing < 5 ms).

---

## Interface

- Tema **claro** e **escuro** e idiomas português, inglês e espanhol (menu do
  globo no topo).
- Tabelas ordenáveis e com botão de copiar.
- Atualização automática dos cálculos enquanto se digita.
- **Gráficos interativos** (Plotly): passe o mouse sobre os picos para ver íon,
  carga, m/z e subsequência; arraste para dar zoom e clique duas vezes para voltar.
- Tela **Como usar** com demonstrações interativas.

---

## Empacotamento (executável)

O `.zip` do Windows publicado em Releases é gerado pelo GitHub Actions
(`.github/workflows/executaveis.yml`) ao criar uma tag `v*`: empacota com **PyInstaller** e anexa
`PeptMass-<versão>-Windows.zip` à Release. Para macOS e Linux a forma
distribuída é o Docker (seção 2); o build local abaixo existe, mas esses
executáveis não são publicados nem testados.

Para gerar o executável localmente:

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
  scripts `build.bat` e `build.sh` criam uma venv de build isolada e empacotam.
- **onedir** (padrão) é mais confiável e tem startup mais rápido; **onefile**
  (`PEPTMASS_ONEFILE=1`) gera um único arquivo, porém com startup mais lento e
  maior chance de falso-positivo de antivírus no Windows.
- O `.spec` leva as telas, traduções e arquivos estáticos de `peptmass/web`, o
  navegador embutido (PyQt6-WebEngine) e os dados do `reportlab`; deixa de fora
  os módulos QML do Qt e as ferramentas de desenvolvedor do navegador. O pacote
  Windows fica com ~515 MB (~220 MB zipado).
- **Ícone:** `packaging/peptmass.ico` (o mascote); no macOS, `peptmass.icns` na
  raiz do projeto, se existir.
- O banco local continua em `~/.peptmass/peptmass.db`, criado em runtime — nada
  precisa ser embutido no pacote.
- O executável deve ser gerado **na plataforma de destino** (PyInstaller não faz
  cross-compile): builds Windows no Windows, builds macOS no macOS.
- **Distribuição**: no modo onedir, o resultado é a pasta `dist/PeptMass/`
  (executável + `_internal/`). Para levar a outro computador, **copie/zipe a
  pasta inteira** — o `PeptMass.exe` sozinho não roda. Não precisa de Python
  instalado no destino. O ThermoRawFileParser não é embutido; o usuário o
  instala pelo botão da tela de Dados experimentais (ver Aba 3).

## Recursos avançados implementados

1. Distribuição isotópica teórica (convolução de padrões elementares).
2. Visualização gráfica do espectro teórico e do envelope isotópico.
3. Matching experimental × teórico (Da/ppm).
4. Importação FASTA.
5. Exportação compatível com Skyline (transition list).
6. Biblioteca editável de modificações customizadas.
7. Fórmulas elementares completas dos peptídeos.
8. Base para ETD/ECD (íon z•) e CID/HCD (perdas neutras).
