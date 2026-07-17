import pytest
from flask import Flask
from flask_login import LoginManager, UserMixin, login_user

from app.permissions import requires_role


class FakeUser(UserMixin):
    def __init__(self, id, role):
        self.id = id
        self.role = role

    def get_id(self):
        return str(self.id)


@pytest.fixture
def permissions_app():
    flask_app = Flask(__name__)
    flask_app.config.update(SECRET_KEY="test", TESTING=True)

    login_manager = LoginManager()
    login_manager.init_app(flask_app)

    users = {"1": FakeUser(1, role=0), "2": FakeUser(2, role=3)}

    @login_manager.user_loader
    def load_user(user_id):
        return users.get(user_id)

    @flask_app.route("/declarant-only")
    @requires_role(0)
    def declarant_only():
        return "ok", 200

    @flask_app.route("/admin-only")
    @requires_role(3)
    def admin_only():
        return "ok", 200

    @flask_app.route("/login-as/<user_id>")
    def login_as(user_id):
        login_user(users[user_id])
        return "logged in"

    return flask_app


def test_requires_role_blocks_anonymous(permissions_app):
    client = permissions_app.test_client()
    resp = client.get("/admin-only")
    assert resp.status_code == 401


def test_requires_role_blocks_insufficient_role(permissions_app):
    client = permissions_app.test_client()
    client.get("/login-as/1")
    resp = client.get("/admin-only")
    assert resp.status_code == 403


def test_requires_role_allows_sufficient_role(permissions_app):
    client = permissions_app.test_client()
    client.get("/login-as/2")
    resp = client.get("/admin-only")
    assert resp.status_code == 200


def test_requires_role_allows_exact_threshold(permissions_app):
    client = permissions_app.test_client()
    client.get("/login-as/1")
    resp = client.get("/declarant-only")
    assert resp.status_code == 200