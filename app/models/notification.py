"""
Notifications in-app (cloche + historique dans la sidebar), indépendantes
des MP Discord (qui existent déjà en parallèle sur les mêmes événements).
Une notification appartient toujours à un seul utilisateur (le déclarant
propriétaire du dossier concerné).
"""

from datetime import datetime

from google.cloud.firestore_v1 import FieldFilter

from app.extensions import get_db
from app.firestore_utils import next_id
from app.timezone_utils import format_utc

COLLECTION = "notifications"


class Notification:
    TYPE_RAPPORT_ENVOYE = "rapport_envoye"
    TYPE_STATUT_CHANGE = "statut_change"
    TYPE_REPONSE_AJOUTEE = "reponse_ajoutee"
    TYPE_TIERS_AJOUTE = "tiers_ajoute"
    TYPE_MENTION = "mention"

    def __init__(self, id, user_id, type, message, rapport_id, read, created_at):
        self.id = id
        self.user_id = user_id
        self.type = type
        self.message = message
        self.rapport_id = rapport_id
        self.read = read
        self.created_at = created_at  # string ISO 8601

    @property
    def created_at_fr(self):
        return format_utc(self.created_at)

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "type": self.type,
            "message": self.message,
            "rapport_id": self.rapport_id,
            "read": self.read,
            "created_at": self.created_at,
        }

    @classmethod
    def _from_doc(cls, doc):
        data = doc.to_dict()
        return cls(id=int(doc.id), **data)

    @classmethod
    def create(cls, user_id, type, message, rapport_id=None):
        """Crée une notification. Échoue silencieusement (log absent
        volontairement simple) plutôt que de faire planter l'action métier
        associée (dépôt, changement de statut, envoi de réponse...)."""
        try:
            db = get_db()
            new_id = next_id(db, COLLECTION)
            notif = cls(
                id=new_id,
                user_id=user_id,
                type=type,
                message=message,
                rapport_id=rapport_id,
                read=False,
                created_at=datetime.utcnow().isoformat(timespec="minutes"),
            )
            db.collection(COLLECTION).document(str(new_id)).set(notif.to_dict())
            return notif
        except Exception:  # noqa: BLE001 - une notif ratée ne doit jamais bloquer l'action réelle
            return None

    @classmethod
    def list_for_user(cls, user_id, limit=200):
        db = get_db()
        docs = (
            db.collection(COLLECTION)
            .where(filter=FieldFilter("user_id", "==", user_id))
            .order_by("created_at", direction="DESCENDING")
            .limit(limit)
            .stream()
        )
        return [cls._from_doc(d) for d in docs]

    @classmethod
    def count_unread(cls, user_id):
        db = get_db()
        docs = (
            db.collection(COLLECTION)
            .where(filter=FieldFilter("user_id", "==", user_id))
            .where(filter=FieldFilter("read", "==", False))
            .stream()
        )
        return sum(1 for _ in docs)

    @classmethod
    def mark_read(cls, notification_id, user_id):
        """Marque une notification comme lue, seulement si elle appartient
        bien à l'utilisateur demandeur."""
        db = get_db()
        doc_ref = db.collection(COLLECTION).document(str(notification_id))
        doc = doc_ref.get()
        if not doc.exists or doc.to_dict().get("user_id") != user_id:
            return False
        doc_ref.update({"read": True})
        return True

    @classmethod
    def mark_all_read(cls, user_id):
        db = get_db()
        docs = (
            db.collection(COLLECTION)
            .where(filter=FieldFilter("user_id", "==", user_id))
            .where(filter=FieldFilter("read", "==", False))
            .stream()
        )
        count = 0
        for doc in docs:
            doc.reference.update({"read": True})
            count += 1
        return count

    @classmethod
    def mark_read_for_rapport(cls, user_id, rapport_id):
        """Marque comme lues toutes les notifications d'un utilisateur liées
        à un dossier précis — appelé automatiquement à la consultation du
        dossier (voir ceam.detail)."""
        db = get_db()
        docs = (
            db.collection(COLLECTION)
            .where(filter=FieldFilter("user_id", "==", user_id))
            .where(filter=FieldFilter("rapport_id", "==", rapport_id))
            .where(filter=FieldFilter("read", "==", False))
            .stream()
        )
        for doc in docs:
            doc.reference.update({"read": True})