from unittest.mock import patch


def test_register_login_and_me(client):
    with patch("app.api.routes.auth.send_welcome_email", return_value=False):
        register = client.post(
            "/api/v1/auth/register",
            json={"email": "demo@example.com", "password": "secret123", "full_name": "Demo User"},
        )
    assert register.status_code == 201
    assert register.json()["email"] == "demo@example.com"
    assert register.json()["welcome_email_sent"] is False

    login = client.post("/api/v1/auth/login", json={"email": "demo@example.com", "password": "secret123"})
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["currency"] == "RUB"
