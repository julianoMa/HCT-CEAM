def test_index_eventually_redirects_to_login_page(client):
    resp = client.get("/", follow_redirects=True)
    assert resp.status_code == 200
    assert "Se connecter avec Discord".encode("utf-8") in resp.data


def test_login_page_renders_directly(client):
    resp = client.get("/auth/login")
    assert resp.status_code == 200
    assert b"login/discord" in resp.data or b"Discord" in resp.data


def test_protected_route_redirects_anonymous(client):
    resp = client.get("/ceam/mes-dossiers", follow_redirects=False)
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_admin_route_forbidden_without_login(client):
    resp = client.get("/admin/utilisateurs", follow_redirects=False)
    # Non connecté : Flask-Login redirige vers la page de connexion.
    assert resp.status_code == 302