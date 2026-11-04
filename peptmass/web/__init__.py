"""PeptMass na web: o template da Hub Dopinho (DopinGPT, DopingValidation,
DegradationFinder) na cor verde-limao, sobre o mesmo nucleo de calculo do desktop.
"""

from __future__ import annotations

import os

from flask import Flask, g, request

from peptmass import __version__
from peptmass.core import i18n as core_i18n
from peptmass.core.constants import PROTON_MASS

from . import catalog, preferences, security, state
from .blueprints.api import bp as api_bp
from .blueprints.pages import bp as pages_bp
from .errors import error_response, register_error_handlers


def create_app() -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")
    max_mb = int(os.environ.get("PEPTMASS_MAX_UPLOAD_MB", "4096"))
    app.config["MAX_CONTENT_LENGTH"] = max_mb * 1024 * 1024
    csrf_token = security.make_csrf_token()
    state.clear_stale_uploads()

    @app.before_request
    def _prepare_request():
        g.lang = preferences.pick_lang()
        g.tema = preferences.pick_theme()
        g._ = catalog.make_translator(g.lang)
        core_i18n.use_language(g.lang)
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            sent = (request.headers.get("X-CSRF-Token")
                    or request.form.get("csrf_token") or "")
            if not security.is_valid_csrf(sent, csrf_token):
                return error_response(g._("error.csrf"), 403)
        return None

    app.after_request(preferences.remember)

    @app.context_processor
    def _template_context():
        lang = getattr(g, "lang", catalog.DEFAULT_LANG)
        merged = dict(catalog.load_catalog(catalog.DEFAULT_LANG))
        merged.update(catalog.load_catalog(lang))
        return {
            "_": getattr(g, "_", catalog.make_translator(lang)),
            "lang": lang,
            "langs": catalog.available_langs(),
            "tema": getattr(g, "tema", preferences.DEFAULT_THEME),
            "temas": preferences.THEMES,
            "csrf_token": lambda: csrf_token,
            "i18n_catalog": merged,
            "app_version": __version__,
            "proton_mass": PROTON_MASS,
        }

    register_error_handlers(app)
    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp)
    return app
