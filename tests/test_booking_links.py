from datetime import date

from app.services.booking_links import build_booking_links, resolve_aviasales_ticket_link


def test_resolve_aviasales_ticket_link():
    url = resolve_aviasales_ticket_link("/search/MOW0101AER07012", "12345")
    assert url.startswith("https://www.aviasales.ru/search/")
    assert "marker=12345" in url


def test_build_booking_links_marks_specific_flight():
    links = build_booking_links(
        "Сочи",
        date(2026, 7, 1),
        date(2026, 7, 8),
        2,
        origin_iata="MOW",
        flight_booking_url="https://www.aviasales.ru/search/MOW0101AER07012",
        flight_link_is_specific=True,
        hotel_name="Hotel Sochi",
        hotel_booking_url="https://www.booking.com/hotel/ru/example.html",
        hotel_link_is_specific=True,
    )
    assert links["flight_specific"] is True
    assert links["hotel_specific"] is True
