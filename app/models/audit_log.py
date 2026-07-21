"""
Journal d'audit des actions sensibles de la plateforme (rôles, rapports,
statuts, réponses...), consultable uniquement par les administrateurs
(voir app/admin/routes.py). Chaque entrée est indépendante et immuable
(on ne modifie ni ne supprime jamais une entrée existante).
"""

from datetime import datetime

from app.extensions import get_db
from app.firestore_utils import next_id
from app.timezone_utils import format_utc

COLLECTION = "logs"


class AuditLog:
    ACTION_ROLE_CHANGE = "role_change"
    ACTION_RAPPORT_CREATE = "rapport_create"
    ACTION_RAPPORT_ARCHIVE = "rapport_archive"
    ACTION_RAPPORT_DELETE = "rapport_delete"
    ACTION_STATUS_CHANGE = "status_change"
    ACTION_REPONSE_ADD = "reponse_add"
    ACTION_REGLEMENT_UPDATE = "reglement_update"
    ACTION_TIERS_ADD = "tiers_add"
    ACTION_TIERS_REMOVE = "tiers_remove"
    ACTION_FORCE_LOGOUT = "force_logout"
    ACTION_MESSAGES_LOCK = "messages_lock"
    ACTION_REPONSE_DELETE = "reponse_delete"
    ACTION_REPONSE_EDIT = "reponse_edit"

    ACTION_LABELS = {
        ACTION_ROLE_CHANGE: "Changement de rôle",
        ACTION_RAPPORT_CREATE: "Création de rapport",
        ACTION_RAPPORT_ARCHIVE: "Archivage de rapport",
        ACTION_RAPPORT_DELETE: "Suppression de rapport",
        ACTION_STATUS_CHANGE: "Changement de statut",
        ACTION_REPONSE_ADD: "Envoi de réponse",
        ACTION_REGLEMENT_UPDATE: "Modification du règlement",
        ACTION_TIERS_ADD: "Ajout d'un tiers",
        ACTION_TIERS_REMOVE: "Retrait d'un tiers",
        ACTION_FORCE_LOGOUT: "Déconnexion forcée",
        ACTION_MESSAGES_LOCK: "Verrouillage des messages",
        ACTION_REPONSE_DELETE: "Suppression de message",
        ACTION_REPONSE_EDIT: "Modification de message",
    }

    def __init__(self, id, action, actor_name, actor_id, details, created_at):
        self.id = id
        self.action = action
        self.actor_name = actor_name
        self.actor_id = actor_id
        self.details = details
        self.created_at = created_at  # string ISO 8601

    @property
    def action_label(self):
        return self.ACTION_LABELS.get(self.action, self.action)

    @property
    def created_at_fr(self):
        return format_utc(self.created_at)

    def to_dict(self):
        return {
            "action": self.action,
            "actor_name": self.actor_name,
            "actor_id": self.actor_id,
            "details": self.details,
            "created_at": self.created_at,
        }

    @classmethod
    def _from_doc(cls, doc):
        data = doc.to_dict()
        return cls(id=int(doc.id), **data)

    @classmethod
    def record(cls, action, actor_name, details, actor_id=None):
        """Enregistre une entrée de journal. Échoue silencieusement (log
        d'erreur uniquement) plutôt que de faire planter l'action métier
        associée : un souci d'écriture du journal ne doit jamais empêcher
        de créer un rapport, changer un rôle, etc."""
        try:
            db = get_db()
            new_id = next_id(db, COLLECTION)
            entry = cls(
                id=new_id,
                action=action,
                actor_name=actor_name,
                actor_id=actor_id,
                details=details,
                created_at=datetime.utcnow().isoformat(timespec="minutes"),
            )
            db.collection(COLLECTION).document(str(new_id)).set(entry.to_dict())
            return entry
        except Exception:  # noqa: BLE001 - le journal ne doit jamais bloquer l'action réelle
            return None

    @classmethod
    def list_recent(cls, limit=500):
        db = get_db()
        docs = (
            db.collection(COLLECTION)
            .order_by("created_at", direction="DESCENDING")
            .limit(limit)
            .stream()
        )
        return [cls._from_doc(d) for d in docs]

    @staticmethod
    def filter_by_search(entries, query):
        """Filtre une liste d'entrées déjà chargée par nom d'auteur ou
        contenu des détails (recherche insensible à la casse)."""
        query = (query or "").strip().lower()
        if not query:
            return entries

        def matches(entry):
            haystack = f"{entry.actor_name} {entry.details}".lower()
            return query in haystack

        return [e for e in entries if matches(e)]