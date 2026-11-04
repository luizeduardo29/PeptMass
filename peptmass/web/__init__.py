"""PeptMass na web: o template da Hub Dopinho (DopinGPT, DopingValidation,
DegradationFinder) na cor verde-limao, sobre o mesmo nucleo de calculo do desktop.

Idioma (pt-BR/en/es) e modo de cor (claro/escuro) seguem o padrao da Hub:
?lang= / ?tema= mandam, o servidor grava num cookie e o <html data-tema> ja sai
certo do servidor, sem piscar o claro antes.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets

from flask import Flask, g, jsonify, render_template, request

from peptmass.core import i18n as core_i18n
from peptmass.core.constants import PROTON_MASS

from . import catalog, state

APP_VERSION = "1.0"

LANG_COOKIE = "peptmass_lang"
THEME_COOKIE = "peptmass_tema"
THEMES = ("claro", "escuro")
DEFAULT_THEME = "claro"
_COOKIE_AGE = 365 * 24 * 3600


def _pick_lang() -> str:
    requested = request.args.get("lang")
    if requested:
        return catalog.resolve_lang(requested)
    cookie = request.cookies.get(LANG_COOKIE)
    if cookie:
        return catalog.resolve_lang(cookie)
    best = request.accept_languages.best_match(["pt-BR", "pt", "en", "es"])
    return catalog.resolve_lang(best)


def _pick_theme() -> str:
    requested = request.args.get("tema")
    if requested in THEMES:
        return requested
    cookie = request.cookies.get(THEME_COOKIE)
    return cookie if cookie in THEMES else DEFAULT_THEME


def _secret() -> bytes:
    """Segredo desta instalacao (na pasta de dados): o token CSRF sobrevive a
    reinicios, entao uma aba aberta antes de reiniciar continua funcionando."""
    path = os.path.join(state.data_dir(), "web_secret")
    try:
        with open(path, "rb") as fh:
            data = fh.read()
        if len(data) >= 32:
            return data
    except OSError:
        pass
    data = secrets.token_bytes(32)
    with open(path, "wb") as fh:
        fh.write(data)
    return data


def create_app() -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")
    max_mb = int(os.environ.get("PEPTMASS_MAX_UPLOAD_MB", "4096"))
    app.config["MAX_CONTENT_LENGTH"] = max_mb * 1024 * 1024
    csrf = hmac.new(_secret(), b"peptmass-csrf", hashlib.sha256).hexdigest()
    state.clear_stale_uploads()

    @app.before_request
    def _setup():
        g.lang = _pick_lang()
        g.tema = _pick_theme()
        g._ = catalog.make_translator(g.lang)
        core_i18n.use_language(g.lang)
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            sent = (request.headers.get("X-CSRF-Token")
                    or request.form.get("csrf_token") or "")
            if not hmac.compare_digest(sent, csrf):
                return _error(g._("error.csrf"), 403)
        return None

    @app.after_request
    def _persist(resp):
        if request.args.get("lang"):
            resp.set_cookie(LANG_COOKIE, g.lang, max_age=_COOKIE_AGE, samesite="Lax")
        if request.args.get("tema") in THEMES:
            resp.set_cookie(THEME_COOKIE, g.tema, max_age=_COOKIE_AGE, samesite="Lax")
        return resp

    @app.context_processor
    def _ctx():
        lang = getattr(g, "lang", catalog.DEFAULT_LANG)
        merged = dict(catalog.load_catalog(catalog.DEFAULT_LANG))
        merged.update(catalog.load_catalog(lang))
        return {
            "_": getattr(g, "_", catalog.make_translator(lang)),
            "lang": lang,
            "langs": catalog.available_langs(),
            "tema": getattr(g, "tema", DEFAULT_THEME),
            "temas": THEMES,
            "csrf_token": lambda: csrf,
            "i18n_catalog": merged,
            "app_version": APP_VERSION,
            "proton_mass": PROTON_MASS,
        }

    def _t(key: str) -> str:
        # g._ pode faltar se o erro vier antes do before_request
        return getattr(g, "_", catalog.make_translator(None))(key)

    def _error(message: str, status: int):
        if request.path.startswith("/api/") or request.path.startswith("/export/"):
            return jsonify(ok=False, error=message), status
        return render_template("error.html", message=message), status

    @app.errorhandler(404)
    def _not_found(_exc):
        return _error(_t("error.not_found"), 404)

    @app.errorhandler(413)
    def _too_large(_exc):
        return _error(_t("error.too_large"), 413)

    @app.errorhandler(500)
    def _internal(_exc):
        return _error(_t("error.internal"), 500)

    from .pages import bp as pages_bp
    from .api import bp as api_bp
    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp)
    return app
