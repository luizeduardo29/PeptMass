"""Erros: JSON para a API e as exportacoes, pagina para as telas."""

from __future__ import annotations

from flask import g, jsonify, render_template, request

from . import catalog


def _translate(key: str) -> str:
    # g._ pode faltar se o erro vier antes do before_request
    return getattr(g, "_", catalog.make_translator(None))(key)


def error_response(message: str, status: int):
    if request.path.startswith(("/api/", "/export/")):
        return jsonify(ok=False, error=message), status
    return render_template("error.html", message=message), status


def register_error_handlers(app) -> None:
    for status, key in ((404, "error.not_found"), (413, "error.too_large"),
                        (500, "error.internal")):
        app.register_error_handler(
            status, lambda _exc, status=status, key=key: error_response(_translate(key), status))
