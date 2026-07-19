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

    def __init__(self, id, discord_id, name, role, avatar_url=None, affectation=None, rank=None, session_version=0):
        self.id = id
        self.discord_id = discord_id
        self.name = name
        self.role = role
        self.avatar_url = avatar_url
        # Déduits des rôles Discord à chaque connexion (voir
        # app/discord_roles.py) — utilisés pour pré-remplir le formulaire
        # de dépôt. None si la personne n'a aucun rôle de grade/affectation
        # connu.
        self.affectation = affectation
        self.rank = rank
        # Incrémenté pour forcer la déconnexion à distance de cette
        # personne (voir force_logout ci-dessous) : la session en cours
        # dans son navigateur devient invalide dès sa prochaine requête,
        # sans qu'on puisse toucher directement à son cookie.
        self.session_version = session_version or 0

    # --- Flask-Login ---
    def get_id(self):
        return f"{self.id}|{self.session_version}"

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
            "affectation": self.affectation,
            "rank": self.rank,
            "session_version": self.session_version,
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
            affectation=data.get("affectation"),
            rank=data.get("rank"),
            session_version=data.get("session_version", 0),
        )

    # --- Accès Firestore ---
    @classmethod
    def get(cls, user_id):
        db = get_db()
        doc = db.collection(COLLECTION).document(str(user_id)).get()
        return cls._from_doc(doc) if doc.exists else None

    @classmethod
    def get_for_session(cls, composite_id):
        """Charge un utilisateur à partir de l'identifiant composite stocké
        dans le cookie de session ('id|session_version'), et vérifie que la
        version de session correspond toujours à celle en base. Retourne
        None si la personne n'existe plus OU si sa session a été invalidée
        entre-temps (déconnexion forcée) — ce qui la déconnecte proprement
        au prochain chargement de page."""
        try:
            raw_id, raw_version = str(composite_id).split("|", 1)
            user_id, session_version = int(raw_id), int(raw_version)
        except (ValueError, AttributeError):
            return None
        user = cls.get(user_id)
        if user is None or user.session_version != session_version:
            return None
        return user

    def force_logout(self):
        """Invalide immédiatement la session actuelle de cette personne :
        elle sera déconnectée dès sa prochaine requête, sans avoir à
        toucher à son cookie (impossible à distance de toute façon)."""
        db = get_db()
        new_version = self.session_version + 1
        db.collection(COLLECTION).document(str(self.id)).update({"session_version": new_version})
        self.session_version = new_version

    @classmethod
    def get_by_discord_id(cls, discord_id):
        db = get_db()
        doc = db.collection(COLLECTION).document(str(int(discord_id))).get()
        return cls._from_doc(doc) if doc.exists else None

    @classmethod
    def create(cls, discord_id, name, role=ROLE_DECLARANT, avatar_url=None, affectation=None, rank=None):
        db = get_db()
        doc_id = str(int(discord_id))

        if db.collection(COLLECTION).document(doc_id).get().exists:
            raise ValueError(f"Un utilisateur avec le Discord ID {discord_id} existe déjà.")
    
        user = cls(
            id=int(doc_id),  # Conservé en int pour la compatibilité avec get_id() et les sessions
            discord_id=int(discord_id),
            name=name,
            role=role,
            avatar_url=avatar_url,
            affectation=affectation,
            rank=rank,
        )
        db.collection(COLLECTION).document(doc_id).set(user.to_dict())
        return user

    @classmethod
    def list_all(cls):
        db = get_db()
        docs = db.collection(COLLECTION).order_by("name").stream()
        return [cls._from_doc(d) for d in docs]

    @staticmethod
    def filter_by_search(users, query):
        """Filtre une liste d'utilisateurs déjà chargée par nom ou Discord
        ID (recherche insensible à la casse)."""
        query = (query or "").strip().lower()
        if not query:
            return users

        def matches(user):
            haystack = f"{user.name} {user.discord_id}".lower()
            return query in haystack

        return [u for u in users if matches(u)]

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

    def update_profile(self, name, avatar_url, affectation=None, rank=None):
        """Garde le pseudo, la photo de profil, l'affectation et le grade
        synchronisés avec Discord, appelé à chaque connexion (voir
        auth/routes.py). L'affectation et le grade sont déduits des rôles
        Discord actuels de la personne — s'ils ne correspondent plus à
        aucun rôle connu, ils sont remis à None plutôt que de garder une
        ancienne valeur potentiellement obsolète."""
        db = get_db()
        db.collection(COLLECTION).document(str(self.id)).update(
            {"name": name, "avatar_url": avatar_url, "affectation": affectation, "rank": rank}
        )
        self.name = name
        self.avatar_url = avatar_url
        self.affectation = affectation
        self.rank = rank

    def __repr__(self):
        return f"<User {self.name} ({self.role_label})>"