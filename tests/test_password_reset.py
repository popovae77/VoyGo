from unittest.mock import patch

from app.services.password_reset import generate_reset_token, hash_reset_token


def test_reset_token_hash_stable():
    raw, hashed = generate_reset_token()
    assert hash_reset_token(raw) == hashed
    assert len(hashed) == 64


def test_password_reset_flow(client):
    with patch("app.api.routes.auth.send_welcome_email", return_value=True):
        client.post(
            "/api/v1/auth/register",
            json={"email": "reset@example.com", "password": "oldpass1", "full_name": "Reset User"},
        )

    with patch("app.api.routes.auth.send_password_reset_email", return_value=True) as send_mock:
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "reset@example.com"},
        )
    assert response.status_code == 200
    assert response.json()["email_sent"] is True
    send_mock.assert_called_once()

    raw_token = send_mock.call_args.kwargs["reset_token"]
    reset = client.post(
        "/api/v1/auth/reset-password",
        json={"token": raw_token, "new_password": "newpass9"},
    )
    assert reset.status_code == 200

    bad_login = client.post(
        "/api/v1/auth/login",
        json={"email": "reset@example.com", "password": "oldpass1"},
    )
    assert bad_login.status_code == 401

    ok_login = client.post(
        "/api/v1/auth/login",
        json={"email": "reset@example.com", "password": "newpass9"},
    )
    assert ok_login.status_code == 200


def test_forgot_password_unknown_email_ok(client):
    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "nobody@example.com"},
    )
    assert response.status_code == 200
    assert response.json()["email_sent"] is False
