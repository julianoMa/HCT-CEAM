from app.models.user import User


def test_role_label_known():
    u = User(id=1, discord_id=123, name="Test", role=User.ROLE_PRESIDENT_CEAM)
    assert u.role_label == "Président CEAM"


def test_role_label_unknown_role():
    u = User(id=1, discord_id=123, name="Test", role=99)
    assert u.role_label == "Inconnu"


def test_get_id_returns_string():
    u = User(id=42, discord_id=123, name="Test", role=User.ROLE_DECLARANT)
    assert u.get_id() == "42"


def test_to_dict_contains_expected_fields():
    u = User(id=1, discord_id=123, name="Test", role=0, avatar_url="http://x/y.png")
    assert u.to_dict() == {
        "discord_id": 123, "name": "Test", "role": 0, "avatar_url": "http://x/y.png",
    }