"""Authentication, sessions and password hashing (feature F1)."""

import os

from app.auth import hash_password, verify_password

DEMO_EMAIL = "cenius@cenius.ai"


def test_root_redirects_anonymous_visitors_to_signin(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/signin"


def test_signin_page_shows_the_demo_credentials(client):
    response = client.get("/signin")
    assert response.status_code == 200
    assert "Demo: cenius@cenius.ai / cenius" in response.text
    assert 'name="email"' in response.text
    assert 'type="password"' in response.text


def test_login_route_serves_the_same_signin_screen(client):
    response = client.get("/login")

    assert response.status_code == 200
    assert 'id="signin-email"' in response.text
    assert 'id="signin-password"' in response.text
    assert 'id="signin-submit"' in response.text
    assert "Demo: cenius@cenius.ai / cenius" in response.text


def test_login_route_accepts_the_demo_credentials(client):
    response = client.post(
        "/auth/signin",
        data={"email": "cenius@cenius.ai", "password": "cenius"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"
    assert client.get("/login", follow_redirects=False).status_code == 302


def test_signin_with_demo_credentials_establishes_a_session(auth_client):
    response = auth_client.get("/dashboard")
    assert response.status_code == 200
    assert DEMO_EMAIL in response.text


def test_wrong_password_gets_one_generic_message_and_keeps_the_email(client):
    response = client.post(
        "/auth/signin",
        data={"email": DEMO_EMAIL, "password": "***REDACTED-SECRET***"},
        follow_redirects=False,
    )
    assert response.status_code == 400
    assert "Email or password is incorrect." in response.text
    assert DEMO_EMAIL in response.text
    assert "definitely-wrong" not in response.text


def test_unknown_email_gets_the_same_message(client):
    response = client.post(
        "/auth/signin",
        data={"email": "nobody@example.com", "password": "whatever"},
        follow_redirects=False,
    )
    assert response.status_code == 400
    assert "Email or password is incorrect." in response.text


def test_signup_creates_the_account_and_lands_on_the_dashboard(client):
    email = "newcomer+%s@example.com" % os.urandom(4).hex()
    response = client.post(
        "/auth/signup",
        data={
            "display_name": "New Contributor",
            "email": email,
            "password": "***REDACTED-SECRET***",
            "confirm_password": "***REDACTED-SECRET***",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"

    dashboard = client.get("/dashboard")
    assert dashboard.status_code == 200
    assert email in dashboard.text
    assert "Paste your first commits" in dashboard.text


def test_signup_rejects_a_mismatched_confirmation(client):
    response = client.post(
        "/auth/signup",
        data={
            "display_name": "Careless Maintainer",
            "email": "careless@example.com",
            "password": "***REDACTED-SECRET***",
            "confirm_password": "different-pass",
        },
        follow_redirects=False,
    )
    assert response.status_code == 400
    assert "Passwords do not match." in response.text
    assert "careless@example.com" in response.text


def test_signup_rejects_a_duplicate_email(client):
    response = client.post(
        "/auth/signup",
        data={
            "display_name": "Second Cenius",
            "email": DEMO_EMAIL,
            "password": "***REDACTED-SECRET***",
            "confirm_password": "***REDACTED-SECRET***",
        },
        follow_redirects=False,
    )
    assert response.status_code == 400
    assert "An account with that email already exists." in response.text


def test_gated_pages_redirect_to_signin_with_a_flash(client):
    for path in ("/composer", "/dashboard", "/releases/1"):
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 302, path
        assert response.headers["location"].startswith("/signin"), path


def test_signout_clears_the_session(auth_client):
    response = auth_client.post("/auth/signout", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/signin"

    dead = auth_client.get("/dashboard", follow_redirects=False)
    assert dead.status_code == 302
    assert dead.headers["location"].startswith("/signin")


def test_session_cookie_is_httponly_and_lax(client):
    response = client.post(
        "/auth/signin",
        data={"email": DEMO_EMAIL, "password": "cenius"},
        follow_redirects=False,
    )
    cookie = response.headers.get("set-cookie", "").lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie


def test_password_hashing_is_salted_and_verifies():
    first_hash, first_salt = hash_password("correct horse battery staple")
    second_hash, second_salt = hash_password("correct horse battery staple")

    assert first_salt != second_salt
    assert first_hash != second_hash
    assert verify_password("correct horse battery staple", first_hash, first_salt)
    assert verify_password("correct horse battery staple", second_hash, second_salt)
    assert not verify_password("wrong password", first_hash, first_salt)


def test_healthz_answers_without_a_session(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_security_headers_are_present(client):
    response = client.get("/signin")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "default-src 'self'" in response.headers["content-security-policy"]
