"""Idioma e modo de cor: ?lang= / ?tema= mandam e ficam gravados em cookie."""

from __future__ import annotations

from flask import g, request

from . import catalog

LANG_COOKIE = "peptmass_lang"
THEME_COOKIE = "peptmass_tema"
THEMES = ("claro", "escuro")
DEFAULT_THEME = "claro"
_COOKIE_AGE = 365 * 24 * 3600


def pick_lang() -> str:
    requested = request.args.get("lang")
    if requested:
        return catalog.resolve_lang(requested)
    cookie = request.cookies.get(LANG_COOKIE)
    if cookie:
        return catalog.resolve_lang(cookie)
    best = request.accept_languages.best_match(["pt-BR", "pt", "en", "es"])
    return catalog.resolve_lang(best)


def pick_theme() -> str:
    requested = request.args.get("tema")
    if requested in THEMES:
        return requested
    cookie = request.cookies.get(THEME_COOKIE)
    return cookie if cookie in THEMES else DEFAULT_THEME


def remember(response):
    """Grava a escolha feita pela URL nesta requisicao."""
    if request.args.get("lang"):
        response.set_cookie(LANG_COOKIE, g.lang, max_age=_COOKIE_AGE, samesite="Lax")
    if request.args.get("tema") in THEMES:
        response.set_cookie(THEME_COOKIE, g.tema, max_age=_COOKIE_AGE, samesite="Lax")
    return response
