from datetime import date, timedelta


def auth_headers(client):
    client.post("/api/v1/auth/register", json={"email": "trip@example.com", "password": "secret123"})
    login = client.post("/api/v1/auth/login", json={"email": "trip@example.com", "password": "secret123"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def trip_payload(budget):
    start = date.today() + timedelta(days=20)
    end = start + timedelta(days=7)
    return {
        "destination": "Сочи",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "people_count": 2,
        "budget": budget,
        "travel_type": "beach",
        "comfort_level": "standard",
    }


def test_trip_search_in_budget(client):
    response = client.post("/api/v1/trips/search", json=trip_payload("200000"), headers=auth_headers(client))
    assert response.status_code == 201
    data = response.json()
    assert len(data["offers"]) >= 1
    assert data["offers"][0]["fits_budget"] is True
    assert "flight" in data["offers"][0]["breakdown_json"]


def test_trip_search_over_budget_returns_alternatives(client):
    response = client.post("/api/v1/trips/search", json=trip_payload("10000"), headers=auth_headers(client))
    assert response.status_code == 201
    data = response.json()
    assert data["offers"][0]["fits_budget"] is False
    assert len(data["offers"]) > 1
