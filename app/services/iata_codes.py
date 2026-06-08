from app.core.config import get_settings
from app.services.destinations_catalog import DEFAULT_ORIGIN_TITLE, resolve_place_iata


def resolve_iata(destination: str) -> str | None:
    return resolve_place_iata(destination)


def resolve_origin_iata(origin: str | None = None) -> str:
    settings = get_settings()
    default = settings.default_origin_iata.upper()
    if not origin or not origin.strip():
        return default
    return resolve_place_iata(origin) or default
