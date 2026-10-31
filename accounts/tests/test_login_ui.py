"""Tests for the compact application sign-in layout."""

from django.urls import reverse


def test_login_uses_a_dedicated_centred_layout(client):
    """Show a dedicated sign-in card with the shared navigation."""
    response = client.get(reverse("login"))

    assert response.status_code == 200
    content = response.content.decode()
    assert 'class="login__panel"' in content
    assert 'class="login__logo"' in content
    assert "Sign in to Aether" in content
    assert 'class="site-header"' in content
    assert 'css/pages/login.css' in content
    assert 'name="csrfmiddlewaretoken"' in content
    assert 'name="username"' in content
    assert 'name="password"' in content
    assert 'type="submit"' in content


def test_login_links_to_registration_preview(client):
    """Offer an accessible route to the registration form preview."""
    response = client.get(reverse("login"))
    content = response.content.decode()

    assert 'href="' + reverse("register") + '"' in content
    assert "Create an account" in content


def test_login_does_not_offer_unimplemented_sign_in_options(client):
    """Avoid unused social providers and password-reset links."""
    response = client.get(reverse("login"))
    content = response.content.decode()

    assert "Continue with Google" not in content
    assert "Continue with Apple" not in content
    assert "Forgot password" not in content
