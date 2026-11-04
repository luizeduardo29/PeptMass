"""Token CSRF derivado de um segredo guardado na pasta de dados."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets

from . import state


def _load_secret() -> bytes:
    """O segredo persiste: uma aba aberta antes de reiniciar continua funcionando."""
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


def make_csrf_token() -> str:
    return hmac.new(_load_secret(), b"peptmass-csrf", hashlib.sha256).hexdigest()


def is_valid_csrf(sent: str, token: str) -> bool:
    return hmac.compare_digest(sent, token)
