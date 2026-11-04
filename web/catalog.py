"""Traducoes da interface web (pt-BR, en, es) e o helper `_()`.

Mesmo formato dos outros sistemas da Hub (DopingValidation, i18n.py de la):
catalogos JSON planos (chave pontuada -> texto) em web/locales, para que um
laboratorio traduza sem mexer em codigo. As mensagens do NUCLEO (calculo,
formulas, PubChem) continuam no i18n.py da raiz, ligado ao mesmo idioma por
requisicao (i18n.use_language).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

LOCALES_DIR = Path(__file__).resolve().parent / "locales"

DEFAULT_LANG = "pt-BR"
SUPPORTED_LANGS: tuple[str, ...] = ("pt-BR", "en", "es")

# Nome de cada idioma no proprio idioma: nome de idioma nao se traduz.
LANG_NAMES: dict[str, str] = {
    "pt-BR": "Português (Brasil)",
    "en": "English",
    "es": "Español",
}


@lru_cache(maxsize=None)
def load_catalog(lang: str) -> dict[str, str]:
    path = LOCALES_DIR / f"{lang}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}


def resolve_lang(value: Any, default: str = DEFAULT_LANG) -> str:
    """Aceita 'pt', 'pt_BR', 'PT-br', 'en-US', 'es-ES'... e cai no padrao."""
    if not value:
        return default
    lowered = str(value).strip().replace("_", "-").lower()
    for lang in SUPPORTED_LANGS:
        if lowered == lang.lower():
            return lang
    prefix = lowered.split("-", 1)[0]
    for lang in SUPPORTED_LANGS:
        if prefix == lang.lower().split("-", 1)[0]:
            return lang
    return default


def available_langs() -> list[dict[str, str]]:
    return [{"code": code, "name": LANG_NAMES[code]} for code in SUPPORTED_LANGS]


def translate(key: str, lang: str | None = None, **params: Any) -> str:
    """Idioma pedido -> idioma padrao -> a propria chave (nunca explode)."""
    code = resolve_lang(lang)
    text = load_catalog(code).get(key)
    if text is None and code != DEFAULT_LANG:
        text = load_catalog(DEFAULT_LANG).get(key)
    if text is None:
        text = key
    if params:
        try:
            return text.format(**params)
        except (KeyError, IndexError, ValueError):
            return text
    return text


def make_translator(lang: str | None) -> Callable[..., str]:
    code = resolve_lang(lang)

    def _(key: str, **params: Any) -> str:
        return translate(key, code, **params)

    return _
