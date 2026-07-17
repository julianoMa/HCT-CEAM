from flask_login import UserMixin
from google.cloud.firestore_v1 import FieldFilter

from app.extensions import get_db
from app.firestore_utils import next_id

COLLECTION = "utilisateurs"


class User(UserMixin):
    # Rôles (schéma : role de 0 à 3)
    ROLE_DECLARANT = 0
    ROLE_MEMBRE_CEAM = 1
    ROLE_PRESIDENT_CEAM = 2
    ROLE_ADMIN = 3

    ROLE_LABELS = {
        ROLE_DECLARANT: "Déclarant",
        ROLE_MEMBRE_CEAM: "Membre CEAM",
        ROLE_PRESIDENT_CEAM: "Président CEAM",
        ROLE_ADMIN: "Administrateur",
    }

    def __init__(self, id, discord_id, name, role, avatar_url=None):
        self.id = id
        self.discord_id = discord_id
        self.name = name
        self.role = role
        self.avatar_url = avatar_url

    # --- Flask-Login ---
    def get_id(self):
        return str(self.id)

    # --- Confort ---
    @property
    def role_label(self):
        return self.ROLE_LABELS.get(self.role, "Inconnu")

    def to_dict(self):
        return {
            "discord_id": self.discord_id,
            "name": self.name,
            "role": self.role,
            "avatar_url": self.avatar_url,
        }

    @classmethod
    def _from_doc(cls, doc):
        data = doc.to_dict()
        return cls(
            id=int(doc.id),
            discord_id=data["discord_id"],
            name=data["name"],
            role=data["role"],
            avatar_url=data.get("avatar_url"),
        )

    # --- Accès Firestore ---
    @classmethod
    def get(cls, user_id):
        db = get_db()
        doc = db.collection(COLLECTION).document(str(user_id)).get()
        return cls._from_doc(doc) if doc.exists else None

    @classmethod
    def get_by_discord_id(cls, discord_id):
        db = get_db()
        query = db.collection(COLLECTION).where(filter=FieldFilter("discord_id", "==", int(discord_id))).limit(1)
        docs = list(query.stream())
        return cls._from_doc(docs[0]) if docs else None

    @classmethod
    def create(cls, discord_id, name, role=ROLE_DECLARANT, avatar_url=None):
        db = get_db()
        new_id = next_id(db, COLLECTION)
        user = cls(id=new_id, discord_id=int(discord_id), name=name, role=role, avatar_url=avatar_url)
        db.collection(COLLECTION).document(str(new_id)).set(user.to_dict())
        return user

    @classmethod
    def list_all(cls):
        db = get_db()
        docs = db.collection(COLLECTION).order_by("name").stream()
        return [cls._from_doc(d) for d in docs]

    @classmethod
    def list_ceam_members(cls):
        """Tous les membres de la commission (Membre CEAM et au-dessus),
        utilisé pour les notifications de nouveau rapport."""
        db = get_db()
        docs = db.collection(COLLECTION).where(filter=FieldFilter("role", ">=", cls.ROLE_MEMBRE_CEAM)).stream()
        return [cls._from_doc(d) for d in docs]

    def update_role(self, new_role):
        db = get_db()
        db.collection(COLLECTION).document(str(self.id)).update({"role": new_role})
        self.role = new_role

    def update_profile(self, name, avatar_url):
        """Garde le pseudo et la photo de profil synchronisés avec Discord,
        appelé à chaque connexion (voir auth/routes.py)."""
        db = get_db()
        db.collection(COLLECTION).document(str(self.id)).update(
            {"name": name, "avatar_url": avatar_url}
        )
        self.name = name
        self.avatar_url = avatar_url

    def __repr__(self):
        return f"<User {self.name} ({self.role_label})>"