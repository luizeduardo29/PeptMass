#!/usr/bin/env python3
"""
run_web.py
==========
Sobe o PeptMass web (Flask). O desktop continua em main.py.

    python run_web.py                 # http://127.0.0.1:8010
    python run_web.py --host 0.0.0.0 --port 8010

Variaveis de ambiente:
    PEPTMASS_HOST / PEPTMASS_PORT   endereco de escuta (padrao 127.0.0.1:8010)
    PEPTMASS_DATA_DIR               pasta do banco e dos envios (padrao ~/.peptmass,
                                    a mesma do desktop)
    PEPTMASS_MAX_UPLOAD_MB          limite de envio de arquivos de MS (padrao 4096)

Com o waitress instalado ele serve (producao, container); sem ele, o servidor
de desenvolvimento do Flask.
"""

import argparse
import os

from web import create_app


def main():
    parser = argparse.ArgumentParser(description="PeptMass web")
    parser.add_argument("--host", default=os.environ.get("PEPTMASS_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PEPTMASS_PORT", "8010")))
    parser.add_argument("--debug", action="store_true", help="servidor de desenvolvimento com recarga")
    args = parser.parse_args()

    app = create_app()
    if args.debug:
        app.run(host=args.host, port=args.port, debug=True)
        return
    try:
        from waitress import serve
    except ImportError:
        print("waitress nao instalado: usando o servidor de desenvolvimento do Flask.")
        app.run(host=args.host, port=args.port, threaded=True)
        return
    print(f"PeptMass web em http://{args.host}:{args.port}")
    serve(app, host=args.host, port=args.port, threads=8,
          max_request_body_size=app.config["MAX_CONTENT_LENGTH"])


if __name__ == "__main__":
    main()
