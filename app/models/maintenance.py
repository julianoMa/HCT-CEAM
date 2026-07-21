"""
État du mode maintenance du site — un simple drapeau stocké dans la
collection `config` (à côté du règlement CEAM), consulté avant chaque
requête (voir app/__init__.py) pour bloquer l'accès à tout le monde sauf
le président CEAM et l'administrateur pendant une intervention.
"""

from datetime import datetime

from app.extensions import get_db

COLLECTION = "config"
DOCUMENT_ID = "maintenance"


def is_active():
    """Le mode maintenance est-il actuellement activé ? Retourne False
    (jamais bloquant) si le document n'existe pas encore, si son contenu
    n'a pas la forme attendue, ou en cas de souci de lecture — un
    problème de configuration ne doit jamais, par accident, rendre tout
    le site inaccessible à tout le monde."""
    try:
        db = get_db()
        doc = db.collection(COLLECTION).document(DOCUMENT_ID).get()
        if not isinstance(doc.exists, bool) or not doc.exists:
            return False
        data = doc.to_dict()
        if not isinstance(data, dict):
            return False
        return data.get("active") is True
    except Exception:  # noqa: BLE001 - voir la docstring : jamais bloquant par défaut
        return False


def activate(actor_name):
    db = get_db()
    db.collection(COLLECTION).document(DOCUMENT_ID).set({
        "active": True,
        "activated_by": actor_name,
        "activated_at": datetime.utcnow().isoformat(timespec="minutes"),
    })


def deactivate(actor_name):
    db = get_db()
    db.collection(COLLECTION).document(DOCUMENT_ID).set({
        "active": False,
        "deactivated_by": actor_name,
        "deactivated_at": datetime.utcnow().isoformat(timespec="minutes"),
    })