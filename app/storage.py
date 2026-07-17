"""
Stockage des pièces jointes (PDF, images) des réponses officielles CEAM,
directement dans Firestore (encodées en base64) — solution 100% gratuite,
sans dépendre de Firebase Storage (qui nécessite le plan payant Blaze
depuis fin 2024).

Limite importante à connaître : un document Firestore ne peut pas dépasser
1 Mo. Une fois encodé en base64 (+33% de volume environ), un fichier doit
donc rester nettement en dessous de cette limite. MAX_FILE_SIZE_BYTES
ci-dessous (650 Ko avant encodage) est calibré pour ça — largement
suffisant pour des photos compressées ou de courts PDF, mais insuffisant
pour un PDF scanné de plusieurs dizaines de pages en haute résolution.

Chaque pièce jointe est stockée comme un document indépendant dans sa
propre collection (`attachments`), plutôt que directement dans le document
du rapport, pour ne jamais faire grossir ce dernier au point d'atteindre
lui-même la limite de 1 Mo au fil des réponses envoyées.
"""

import base64
import uuid

from app.extensions import get_db

COLLECTION = "attachments"

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "gif", "webp"}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
}
MAX_FILE_SIZE_BYTES = 650 * 1024  # 650 Ko avant encodage (limite Firestore : 1 Mo/document)


def _extension(filename):
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def is_allowed_file(file_storage):
    """Vérifie l'extension ET le type MIME déclaré. Ce n'est pas une
    protection antivirus, juste un premier filtre de bon sens (le type MIME
    envoyé par le navigateur peut être falsifié par une personne motivée)."""
    ext = _extension(file_storage.filename)
    return ext in ALLOWED_EXTENSIONS and file_storage.content_type in ALLOWED_CONTENT_TYPES


def upload_reponse_attachment(rapport_id, file_storage):
    """Enregistre un fichier dans Firestore (encodé en base64, dans sa
    propre collection). Retourne un dict de métadonnées
    {name, attachment_id, content_type, size}, ou None si le fichier est
    invalide (type non autorisé ou trop volumineux)."""
    if not file_storage or not file_storage.filename:
        return None
    if not is_allowed_file(file_storage):
        return None

    raw = file_storage.stream.read()
    size = len(raw)
    if size > MAX_FILE_SIZE_BYTES:
        return None

    attachment_id = uuid.uuid4().hex
    db = get_db()
    db.collection(COLLECTION).document(attachment_id).set({
        "rapport_id": rapport_id,
        "name": file_storage.filename,
        "content_type": file_storage.content_type,
        "size": size,
        "data_base64": base64.b64encode(raw).decode("ascii"),
    })

    return {
        "name": file_storage.filename,
        "attachment_id": attachment_id,
        "content_type": file_storage.content_type,
        "size": size,
    }


def fetch_attachment(attachment_id, rapport_id):
    """Récupère le contenu d'une pièce jointe. Vérifie que `rapport_id`
    correspond bien au dossier attendu, pour empêcher qu'un identifiant
    deviné donne accès à la pièce jointe d'un autre dossier.
    Retourne (bytes, content_type), ou (None, None) si absent/non autorisé."""
    db = get_db()
    doc = db.collection(COLLECTION).document(attachment_id).get()
    if not doc.exists:
        return None, None
    data = doc.to_dict()
    if data.get("rapport_id") != rapport_id:
        return None, None
    raw = base64.b64decode(data["data_base64"])
    return raw, data.get("content_type")