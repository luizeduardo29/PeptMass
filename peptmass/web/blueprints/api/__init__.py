"""API JSON das telas e as exportacoes, que devolvem arquivo."""

from flask import Blueprint, jsonify

from .common import ApiError

bp = Blueprint("api", __name__)


@bp.errorhandler(ApiError)
def _api_error(exc: ApiError):
    return jsonify(ok=False, error=exc.message, **exc.extra), exc.status


# As rotas se registram em `bp` ao serem importadas.
from . import fragments, library, mass, spectra  # noqa: E402,F401
