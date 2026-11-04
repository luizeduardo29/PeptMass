# syntax=docker/dockerfile:1
# PeptMass web em container (Flask + waitress), no padrao dos outros modulos
# da Hub (DopingValidation, DegradationFinder).
#
#   docker build -t peptmass:1.0 .
#   docker compose up -d          # http://localhost:8010
#
# Sem ThermoRawFileParser: o .exe e' Windows/.NET. No container le-se
# mzML/mzXML; converta o .raw antes (ThermoRawFileParser ou msconvert).

FROM python:3.12-slim

WORKDIR /app

COPY requirements-web.txt /app/
RUN pip install --no-cache-dir -r requirements-web.txt

# So o nucleo de calculo e a web: gui.py (PyQt6) fica de fora.
COPY constants.py custom_residues.py database.py denovo.py exporters.py \
     formula_parser.py fragmentation.py i18n.py identification.py \
     mass_calculator.py modifications.py presets.py pubchem.py scoring.py \
     spectra_io.py run_web.py test_suite.py /app/
COPY web/ /app/web/

RUN useradd -m -u 1000 peptmass \
    && mkdir -p /data && chown peptmass:peptmass /data
USER peptmass

ENV PEPTMASS_DATA_DIR=/data \
    PEPTMASS_HOST=0.0.0.0 \
    PEPTMASS_PORT=8010 \
    PYTHONUNBUFFERED=1

EXPOSE 8010

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8010/', timeout=4).status == 200 else 1)"]

CMD ["python", "run_web.py"]
