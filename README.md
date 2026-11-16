# PeptMass

**Molecular mass and MS/MS fragmentation calculator for peptides and proteins**

Python software for exact masses, charge states, theoretical MS/MS fragment
series, chemical modifications, non-natural amino acids and annotation of
experimental spectra (`.mzML`, `.mzXML` and Thermo `.raw`), with light/dark
themes and an interface in Portuguese, English and Spanish.

License: [GPL-3.0](LICENSE).

---

## How to use: pick one of three ways

All three have **the same screens and the same features**. Pick the simplest
one for your case:

| Way | System | What to install | For whom |
|---|---|---|---|
| [**1. Windows program (.exe)**](#1-windows-program-exe) | Windows 10 or 11 (64-bit) | Nothing | Anyone who just wants to use the program |
| [**2. Docker**](#2-docker-windows-macos-and-linux) | Windows, macOS (including M1 or newer) and Linux | Docker | macOS and Linux, or a server for a team on the network |
| [**3. Python (source code)**](#3-python-source-code) | Any system with Python 3.10+ | Python | Anyone who will study or change the code |

---

## 1. Windows program (.exe)

No Python or any other installation is needed.

1. On the project's GitHub page, open **Releases** (on the right) and download
   `PeptMass-<version>-Windows.zip` (about 230 MB).
2. Right-click the `.zip` → **Extract All…** and choose a folder (for example,
   `Documents\PeptMass`). Do not run the program from inside the `.zip`:
   extract it first.
3. In the extracted folder, open **`PeptMass\PeptMass.exe`** (double-click).
   The PeptMass window opens in a few seconds.

> **"Windows protected your PC" warning.** The first time, Windows may show
> this blue screen (SmartScreen), because the program does not yet have a
> company's digital signature. To open it:
> click **More info** → **Run anyway**. The warning does not come back
> afterwards. If your institution's antivirus blocks the program, ask IT
> support to allow the PeptMass folder.

**Keep the whole folder.** `PeptMass.exe` needs the `_internal` folder next to
it. To take the program to another computer, copy the entire `PeptMass`
folder. To create a desktop shortcut, right-click `PeptMass.exe` → **Show more
options** → **Send to** → **Desktop (create shortcut)**.

**Opening Thermo `.raw` files.** The program does not ship the `.raw` reader
(ThermoRawFileParser), because the license of Thermo's library does not allow
distributing it together with PeptMass. To install it, once:

1. Open the **Experimental data** screen.
2. Click **Install .raw reader** (internet required).
3. Read the Thermo license that appears and click **Accept and install**.

PeptMass downloads the official
[ThermoRawFileParser](https://github.com/compomics/ThermoRawFileParser) release,
checks that the file is the original one (SHA-256) and installs it only if you
accept. If you decline, nothing is left on the computer. `.mzML` and `.mzXML`
files open without the reader.

**Where the data lives.** Saved peptides and your registered amino acids and
modifications are stored in `C:\Users\<your user>\.peptmass\peptmass.db`,
together with the `.raw` reader (if installed). Updating the program
(downloading a new `.zip`) does not erase this data.

**Updating.** Download the new version's `.zip` from Releases, extract it and
use the new folder. The old folder can be deleted.

**Uninstalling.** Delete the program folder. To delete the data as well,
delete the `C:\Users\<your user>\.peptmass` folder.

---

## 2. Docker (Windows, macOS and Linux)

Docker runs PeptMass in a "container" and you use the program in your web
browser. The container **already includes the `.raw` reader**: nothing else
needs to be installed.

### 2.1 Install Docker (once)

- **Windows and macOS:** install
  [Docker Desktop](https://www.docker.com/products/docker-desktop/) and open it.
  Wait until the whale icon shows that Docker is running. On Windows, the
  installer may ask you to enable WSL 2 and restart the computer.
- **Mac with Apple chip (M1 or newer):** the `.raw` reader only exists for
  Intel/AMD processors (amd64), so Docker Desktop runs PeptMass through Rosetta
  emulation. If Docker asks, accept installing Rosetta; in **Settings →
  General**, keep *Use Rosetta for x86_64/amd64 emulation on Apple Silicon*
  checked.
- **Linux:** install [Docker Engine](https://docs.docker.com/engine/install/)
  with the `docker compose` plugin. To avoid needing `sudo`:
  `sudo usermod -aG docker $USER` and log in again.

To check, open a terminal (on Windows, **PowerShell**) and run:

```bash
docker compose version
```

### 2.2 Download PeptMass

With git:

```bash
git clone https://github.com/luizeduardo29/PeptMass.git
cd PeptMass
```

Without git: on the project's GitHub page, click **Code → Download ZIP**,
extract the `.zip` and open the terminal inside the extracted folder (the one
that contains `docker-compose.yml`).

### 2.3 Start PeptMass

Inside the project folder:

```bash
docker compose up -d --build
```

The first time takes a few minutes (it downloads and builds the image, about
900 MB). Then open in your browser: **<http://localhost:8010>**

The container keeps running in the background and comes back by itself when
Docker restarts (for example, after rebooting the computer).

### 2.4 Everyday commands

Run them all inside the project folder.

| To | Command |
|---|---|
| Check that it is running | `docker compose ps` |
| Stop (data is kept) | `docker compose stop` |
| Start again | `docker compose start` |
| See the log | `docker compose logs -f` (Ctrl+C exits) |
| Update to a new version | `git pull` (or download the new ZIP), then `docker compose up -d --build` |
| Remove the container (data is kept) | `docker compose down` |
| Remove the container **and delete the data** | `docker compose down -v` |
| Copy the database to the current folder (backup) | `docker compose cp peptmass:/data/peptmass.db ./peptmass.db` |

### 2.5 Settings

Settings go before the command (Linux and macOS) or in a `.env` file in the
project folder (any system, including Windows), one per line, for example
`PORTA_HOST=8020`.

| Variable | Default | What it does |
|---|---|---|
| `PORTA_HOST` | `8010` | Port on the computer. Use another one if 8010 is taken. |
| `PEPTMASS_MAX_UPLOAD_MB` | `4096` | Maximum size of an uploaded MS file, in MB. |
| `MEM_LIMIT` | `2g` | Maximum memory of the container. Raise it for large `.raw` files in profile mode. |
| `PEPTMASS_INSTANCIA` | `peptmass` | Instance name (and name of the data volume). |

Example (Linux/macOS): `PORTA_HOST=8020 docker compose up -d`.

**Using it from other computers on the network.** The container accepts
network connections: colleagues open `http://<your computer's IP>:8010`. On
Windows, you may need to allow port 8010 in Windows Firewall. PeptMass **has
no login**: keep it reachable only on an internal network, never directly on
the internet.

**Running two instances** (for example, one per team, each with its own
database): give the second one another name and another port.

```bash
PEPTMASS_INSTANCIA=peptmass2 PORTA_HOST=8011 docker compose up -d
```

On Windows (PowerShell):

```powershell
$env:PEPTMASS_INSTANCIA="peptmass2"; $env:PORTA_HOST="8011"; docker compose up -d
```

To stop or update that second instance, use the same `PEPTMASS_INSTANCIA` in
the commands.

**Where the data lives.** In the Docker volume `peptmass_dados` (or
`<instance>_dados`). It survives `stop`, `down`, updates and restarts; only
`docker compose down -v` deletes it. Uploaded MS files are temporary: they
leave the disk when the file is closed (PeptMass keeps up to 3 open) and when
the container restarts.

---

## 3. Python (source code)

Requires **Python 3.10 or newer**
([python.org](https://www.python.org/downloads/); on Windows, check *Add
python.exe to PATH* during installation).

```bash
git clone https://github.com/luizeduardo29/PeptMass.git
cd PeptMass
python -m venv .venv
# Windows:      .venv\Scripts\activate
# Linux/macOS:  source .venv/bin/activate
```

**In the browser** (the same version as the container):

```bash
pip install -r requirements/web.txt
python run_web.py                         # http://127.0.0.1:8010, this computer only
python run_web.py --host 0.0.0.0          # also on the network (no login: internal network only)
python run_web.py --port 8020             # another port
```

**In its own window** (the same program as the `.exe`):

```bash
pip install -r requirements/desktop.txt
python run_desktop.py
```

On Windows, `scripts\run_desktop.bat` does all of this with a double-click:
the first time it creates the `.venv` and installs the dependencies.

Environment variables:

| Variable | Default | What it does |
|---|---|---|
| `PEPTMASS_HOST` / `PEPTMASS_PORT` | `127.0.0.1` / `8010` | Address of `run_web.py` (same as `--host` / `--port`). |
| `PEPTMASS_DATA_DIR` | `~/.peptmass` | Folder for the database and temporary uploads. |
| `PEPTMASS_MAX_UPLOAD_MB` | `4096` | Maximum size of an uploaded MS file, in MB. |
| `PEPTMASS_THERMO_PARSER` | — | Path to `ThermoRawFileParser.exe`, to open `.raw`. |

To open `.raw` when running from Python, install
[ThermoRawFileParser](https://github.com/compomics/ThermoRawFileParser) and put
the `ThermoRawFileParser/` folder in the project root or in `~/.peptmass/`, or
point `PEPTMASS_THERMO_PARSER` to it. On Windows the .NET Framework is enough
(it comes with Windows 10/11); on Linux and macOS `mono` is required. The
**Install .raw reader** button only appears in the Windows program
(`run_desktop.py` / `.exe`).

---

## Troubleshooting

| Symptom | Solution |
|---|---|
| "Windows protected your PC" when opening the `.exe` | **More info** → **Run anyway** (see section 1). |
| The `.exe` does not open or closes right away | Extract the whole `.zip` first (do not run it from inside the `.zip`) and do not separate `PeptMass.exe` from the `_internal` folder. |
| "Opening .raw files requires the ThermoRawFileParser reader…" | In the `.exe`: the **Install .raw reader** button on the Experimental data screen. From Python: see section 3. Or convert the `.raw` to mzML (msconvert or ThermoRawFileParser). |
| Downloading the `.raw` reader fails | Internet access to GitHub is required. On restricted networks, try another network or ask for `github.com` to be allowed. |
| "… above this server's upload limit" | Raise `PEPTMASS_MAX_UPLOAD_MB` (section 2.5) and start again with `docker compose up -d`. |
| A large `.raw` in profile mode fails in Docker | Raise `MEM_LIMIT` (for example, `4g`). |
| `docker compose up` says port 8010 is in use | Use another port: `PORTA_HOST=8020` (section 2.5). |
| `docker: command not found` / "Cannot connect to the Docker daemon" | Open Docker Desktop (Windows/macOS) or start the service (`sudo systemctl start docker` on Linux). |
| Colleagues cannot open it over the network | Use the computer's IP (not `localhost`) and allow the port in the firewall. From Python, start with `--host 0.0.0.0`. |
| PubChem search fails | Internet access to `pubchem.ncbi.nlm.nih.gov` is required. |

---

## Screens

**Home**, **Mass** (Tab 1), **Fragmentation** (Tab 2), **Experimental data**
(Tab 3), **Library** (non-natural amino acids, modifications and PubChem) and
**How to use** (interactive demos). The How to use screen opens an example
file (`peptmass/web/static/exemplos/exemplo_PEPTIDE.mzML`) so you can try Tab 3
without your own data.

---

## Architecture

```text
peptmass/
  core/             scientific computation, no interface
    constants.py        atomic masses, isotopes, natural amino acids
    formula_parser.py   molecular formulas and composition mass
    modifications.py    modification library
    custom_residues.py  non-natural amino acids
    mass_calculator.py  sequence, masses, m/z and isotope distribution
    fragmentation.py    a/b/c/x/y/z series, neutral losses, matching
    scoring.py          Morpheus score and mass error
    identification.py   charge, isotope fit and identification criteria
    presets.py          preloaded peptides
    workspace.py        database + libraries + calculator (web and desktop)
    i18n.py             core messages
  infra/            external access
    database.py         local SQLite
    spectra_io.py       mzML, mzXML, .raw and centroiding
    raw_reader.py       user-driven install of the .raw reader (Windows program)
    pubchem.py          PubChem (PUG REST)
    exporters.py        CSV, XLSX, PDF, TXT, FASTA, Skyline
  web/              Flask
    __init__.py         create_app
    blueprints/         pages.py (screens) and api/ (mass, fragments, library, spectra)
    templates/  static/  locales/
  desktop/          window of the executable
    app.py              internal server + web interface in a QWebEngineView
packaging/          PyInstaller (peptmass.spec, build.bat, build.sh)
scripts/            Windows desktop shortcuts
requirements/       desktop.txt, web.txt, build.txt
run_web.py          web entry point
run_desktop.py      desktop entry point
```

Dependencies flow one way: `web` and `desktop` use `infra` and `core`;
`infra` uses `core`; `core` knows no interface.

---

## TAB 1 — Molecular mass

- Sequence input with **automatic validation**.
- 20 natural amino acids (IUPAC monoisotopic masses).
- **Modifications**: N-terminal, C-terminal and per residue (Acetyl, PyroGlu,
  Formyl, Amidation, Oxidation, Phosphorylation, Carbamidomethyl, Deamidation,
  Sulfation and others).
- **Inline** modifications: `PEPT(Phosphorylation)IDE`.
- **Multiple chains**: separate chains with `/`; each one contributes its own
  terminal water. E.g. insulin = `GIVEQCC.../FVNQHLC...`. Disulfide bridges are
  entered as the `Disulfide (-2H)` modification on one Cys per bridge.
  (MS/MS fragmentation in Tab 2 does not apply to multiple chains.)
- **Lysine acylations of GLP analogues** (applicable to `K`): side chains of
  liraglutide, semaglutide, tirzepatide and retatrutide; each delta validated
  by rebuilding the whole drug's formula against PubChem.
- **Built-in catalog** of common non-natural residues, always available
  (not editable): Aib, pGlu, Mpa, Orn, Nle, Nva, Hyp, Cit, Sar, Abu, Dab,
  Dap, Pen, aMeLeu (α-methyl-leucine), Nal (2-naphthylalanine), MeW
  (2-methyl-Trp), SertBu (O-tert-butyl-Ser). They are marked as built-in in the
  table.
- **Custom amino acids**: register non-natural residues by molecular formula;
  the mass is calculated and stored in the local database.
  The **code can have 1 to 3+ letters**; in the sequence, multi-character
  residues go **in brackets**: `A[Orn]G[Nle]K` (a single letter = natural amino
  acid). One-letter codes work with or without brackets.
- **Unknown residues**: when a sequence contains an unregistered code (e.g.
  `[Aib]`), the *"Define unknown residue(s)…"* button opens an assisted
  registration (with PubChem search) and saves it to the database.
- **PubChem search**: search by name, CID or formula and the molecular formula
  is filled in automatically (with 2D structure and masses for checking).
  Available on the Library screen. Requires an internet connection.
- **Saved peptides**: store the sequence + modifications (N/C-terminal and per
  residue) under a name in the local database and reload them with one click.
  They come **preloaded**, with masses validated against PubChem:
  **GLP** analogues (liraglutide, semaglutide, tirzepatide, retatrutide) and
  **anti-doping** peptides (WADA S2): GnRH and agonists (gonadorelin,
  triptorelin, leuprolide, nafarelin, buserelin, goserelin), GHRPs (GHRP-1,
  GHRP-2, GHRP-6, hexarelin, ipamorelin, alexamorelin), GHRH/GRF (sermorelin,
  Mod GRF 1-29, CJC-1295 with DAC, tesamorelin), hGH (somatropin), IGF-1,
  thymosin β4 (43 aa) and its active fragment **TB-500** (Ac-LKKTETQ, residues
  17–23), melanotan I and II, nootropics (semax, selank), MOTS-c, vasopressin
  and analogues, ghrelin, BPC-157, ARA-290, corticotropins
  (tetracosactide/Synacthen, ACTH 1-39), oxytocin, PT-141, thymosin α1,
  epitalon, IGF-1 LR3, MGF, a set of fragments/metabolites from the screening
  method, and the two-chain **insulins** (human, lispro/Humalog,
  aspart/NovoLog, glulisine/Apidra, glargine/Lantus, detemir/Levemir,
  degludec/Tresiba).
- **Monoisotopic mass** and **average mass** (6 decimal places).
- Complete **elemental formula**.
- **Charge state table** (configurable range + extras such as +15, +20).
- **Theoretical isotope distribution** (chart).
- **FASTA import**.

m/z formula:

```
m/z = (M + z × 1.007276466812) / z
```

## TAB 2 — MS/MS fragmentation

- Series selection: **a, b, c, x, y, z** (and radical z• for ETD/ECD).
- **Neutral losses**: −NH₃, −H₂O, −CO (combinable).
- Fragment **charge states**: +1 to +5.
- Sortable table with ion, charge, m/z, loss, neutral mass and subsequence.
- **Quick search** of fragments.
- **Matching** against an experimental m/z list (tolerance in Da or ppm).
- **Theoretical spectrum** (chart).
- **Export**: CSV, Excel (.xlsx), PDF, TXT and Skyline transition list.

## TAB 3 — Experimental data

Compares the **theoretical** spectrum (generated in Tab 2) with a **real**
spectrum from a data file:

1. **Open file**: `.mzML`, `.mzXML` or `.raw` (Thermo).
2. **Scan filter** (Xcalibur style): choose one of the filters present in the
   file (`FTMS + p NSI Full ms`, `... Full ms2 ...@hcd27`, etc.) to restrict the
   chromatogram, XIC and scan selection. In DDA, the **group** option masks the
   precursor m/z, reducing thousands of filters to a few types.
3. **Chromatogram** by MS level / filter: **TIC** or **XIC** (extracted ion:
   enter an m/z and the tolerance in Da). **Click a point** to choose the scan
   at that retention time.
   - **Profile × centroid**: check *"open .raw in profile"* to convert without
     peak picking. Profile scans are detected automatically, drawn as a
     **continuous line**, and centroided internally (local maximum + parabolic
     refinement in log space) for matching.
4. The **scan spectrum** is shown.
5. **Match with fragments**: annotates the peaks against the theoretical series
   and shows a **mirror plot** (experimental ↑ / theoretical ↓) with labeled
   ions, plus an annotation table. Matching automatically considers **neutral
   losses** (−NH₃/−H₂O/−CO) and **multiple charges** (1..max z), with tolerance
   in Da or ppm. **Double-click** a table row to see the **XIC of that ion**.
   - **Identification score**: each match gets the **Morpheus score** (Wenger &
     Coon, *J. Proteome Res.* 2013), i.e. number of matched ions + fraction of
     ion current explained, plus ion **coverage** and **mass error** (median,
     max and RMSE in ppm/Da) as quality control.
   - **Identification criteria (WADA style)**: evaluates and flags (✓/✗)
     **precursor mass** (ppm error vs. the Tab 2 peptide), **retention time**
     (within the given window), **diagnostic ions** (number matched + relative
     abundance in the table) and the **isotope envelope fit** of the precursor
     (theoretical × experimental cosine, from the preceding MS1).
   - **Precursor charge**: read from the file or **estimated automatically**
     from the isotope cluster spacing (deconvolution).

Reading uses `pyteomics`, `psims` and `lxml` (already in `requirements/`).
`.raw` files are converted to mzML by **ThermoRawFileParser** 1.4.5. The
container already includes it (official Bioconda image). The Windows program
does **not**, because the license of Thermo's library (RawFileReader)
restricts distributing it together with GPL software: users obtain it
themselves with the **Install .raw reader** button, which downloads the
official package
([github.com/compomics/ThermoRawFileParser](https://github.com/compomics/ThermoRawFileParser)),
checks its SHA-256, shows the Thermo license and installs it (into
`~/.peptmass/ThermoRawFileParser/`) only if the user accepts. PeptMass looks
for the converter, in this order, in `PEPTMASS_THERMO_PARSER`, in a
`ThermoRawFileParser/` folder next to `PeptMass.exe`, in the project root, in
`~/.peptmass/` and on the `PATH`. The converted mzML is kept in the upload
folder and deleted when the file is closed.

The example file `peptmass/web/static/exemplos/exemplo_PEPTIDE.mzML` is
synthetic, with the b/y ions of the peptide PEPTIDE.

---

## Scientific validation

The calculations were checked against published values (PEPTIDE, bradykinin,
angiotensin II, substance P, fragment series, modifications) within
±0.001 Da, and the thresholds of the identification criteria were also
verified.

Standards used:
- IUPAC monoisotopic masses.
- Proton mass = `1.007276466812`.
- 6 decimal places.
- Supports proteins above 100 kDa (parsing < 5 ms).

---

## Interface

- **Light** and **dark** themes and Portuguese, English and Spanish (globe
  menu at the top).
- Sortable tables with a copy button.
- Calculations update automatically while typing.
- **Interactive charts** (Plotly): hover over peaks to see ion, charge, m/z
  and subsequence; drag to zoom and double-click to reset.
- **How to use** screen with interactive demos.

---

## Packaging (executable)

The Windows `.zip` published in Releases is built by GitHub Actions
(`.github/workflows/executaveis.yml`) when a `v*` tag is pushed: it packages
with **PyInstaller** and attaches `PeptMass-<version>-Windows.zip` to the
Release. For macOS and Linux the distributed form is Docker (section 2); the
local build below exists, but those executables are neither published nor
tested.

To build the executable locally:

```bash
pip install -r requirements/build.txt
```

**Windows:**

```bat
packaging\build.bat              :: onedir in dist\PeptMass\PeptMass.exe
packaging\build.bat onefile      :: a single dist\PeptMass.exe
```

**macOS / Linux:**

```bash
chmod +x packaging/build.sh
packaging/build.sh             # builds dist/PeptMass/ (+ dist/PeptMass.app on macOS)
packaging/build.sh --onefile   # single executable
```

Or directly, on any platform:

```bash
pyinstaller packaging/peptmass.spec --noconfirm --clean
```

Details:

- The recipe is in [`packaging/peptmass.spec`](packaging/peptmass.spec); the
  `build.bat` and `build.sh` scripts create an isolated build venv and package.
- **onedir** (default) is more reliable and starts faster; **onefile**
  (`PEPTMASS_ONEFILE=1`) produces a single file, but starts slower and is more
  likely to trigger antivirus false positives on Windows.
- The `.spec` bundles the screens, translations and static files of
  `peptmass/web`, the embedded browser (PyQt6-WebEngine) and the `reportlab`
  data; it leaves out Qt's QML modules and the browser developer tools. The
  Windows package is ~515 MB (~230 MB zipped).
- **Icon:** `packaging/peptmass.ico` (the mascot); on macOS, `peptmass.icns` in
  the project root, if present.
- The local database stays in `~/.peptmass/peptmass.db`, created at runtime;
  nothing needs to be bundled.
- The executable must be built **on the target platform** (PyInstaller does
  not cross-compile): Windows builds on Windows, macOS builds on macOS.
- **Distribution**: in onedir mode, the result is the `dist/PeptMass/` folder
  (executable + `_internal/`). To take it to another computer, **copy/zip the
  whole folder**; `PeptMass.exe` alone does not run. No Python is needed on the
  target. ThermoRawFileParser is not bundled; users install it with the button
  on the Experimental data screen (see Tab 3).

## Advanced features

1. Theoretical isotope distribution (convolution of elemental patterns).
2. Charts of the theoretical spectrum and isotope envelope.
3. Experimental × theoretical matching (Da/ppm).
4. FASTA import.
5. Skyline-compatible export (transition list).
6. Editable library of custom modifications.
7. Complete elemental formulas of peptides.
8. Groundwork for ETD/ECD (z• ion) and CID/HCD (neutral losses).
