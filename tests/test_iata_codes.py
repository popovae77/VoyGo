from app.services.iata_codes import resolve_iata, resolve_origin_iata
from app.services.destinations_catalog import resolve_place_iata


def test_resolve_by_title():
    assert resolve_iata("Сочи") == "AER"
    assert resolve_iata("сочи") == "AER"


def test_resolve_by_alias():
    assert resolve_iata("испания") == "MAD"
    assert resolve_iata("spain") == "MAD"


def test_resolve_by_raw_iata():
    assert resolve_iata("AER") == "AER"
    assert resolve_place_iata("mow") == "MOW"


def test_resolve_unknown():
    assert resolve_iata("несуществующий город") is None


def test_resolve_origin_defaults():
    assert resolve_origin_iata(None) == "MOW"
    assert resolve_origin_iata("Казань") == "KZN"


def test_resolve_expanded_destinations():
    assert resolve_place_iata("Аланья") == "GZP"
    assert resolve_place_iata("сингапур") == "SIN"
    assert resolve_place_iata("токио") == "TYO"
    assert resolve_place_iata("хорватия") == "ZAG"
    assert resolve_place_iata("занзибар") == "ZNZ"
    assert resolve_place_iata("симферополь") == "SIP"


def test_destinations_catalog_size():
    from app.services.destinations_catalog import DESTINATIONS

    assert len(DESTINATIONS) >= 180
