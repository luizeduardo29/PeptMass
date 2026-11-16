# syntax=docker/dockerfile:1
# PeptMass web em container (Flask + waitress), no padrao dos outros modulos
# da Hub (DopingValidation, DegradationFinder).
#
#   docker build -t peptmass:1.0 .
#   docker compose up -d          # http://localhost:8010
#
# Le .mzML, .mzXML e .raw da Thermo. O ThermoRawFileParser vem pronto da
# imagem oficial do Bioconda (so existe para amd64; em Mac M1 o Docker Desktop
# roda a imagem pelo Rosetta, ver docker-compose.yml) e roda no mono do Debian.

FROM quay.io/biocontainers/thermorawfileparser:1.4.5--h05cac1d_1 AS trfp

FROM python:3.12-slim-bookworm

# mono-devel traz as fachadas .NET (netstandard.dll) que o conversor exige.
RUN apt-get update \
    && apt-get install -y --no-install-recommends mono-runtime mono-devel \
    && rm -rf /var/lib/apt/lists/*
COPY --from=trfp /usr/local/bin/*.dll /usr/local/bin/*.exe /usr/local/bin/*.config \
     /usr/local/bin/LICENSE /usr/local/bin/THERMO_LICENSE /opt/trfp/

WORKDIR /app

COPY requirements/web.txt /app/
RUN pip install --no-cache-dir -r web.txt

# peptmass/desktop (PyQt6) fica de fora pelo .dockerignore.
COPY peptmass/ /app/peptmass/
COPY run_web.py /app/

RUN useradd -m -u 1000 peptmass \
    && mkdir -p /data && chown peptmass:peptmass /data
USER peptmass

ENV PEPTMASS_THERMO_PARSER=/opt/trfp/ThermoRawFileParser.exe \
    PEPTMASS_DATA_DIR=/data \
    PEPTMASS_HOST=0.0.0.0 \
    PEPTMASS_PORT=8010 \
    PYTHONUNBUFFERED=1

EXPOSE 8010

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8010/', timeout=4).status == 200 else 1)"]

CMD ["python", "run_web.py"]
