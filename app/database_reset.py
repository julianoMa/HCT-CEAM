"""
Réinitialisation complète de la base de données — action strictement
réservée aux administrateurs, protégée côté interface par une double
confirmation (deux modals en cascade) et une phrase de confirmation à
taper à la main (voir app/admin/routes.py et templates/admin/logs.html).

Supprime : les dossiers CEAM (et leurs pièces jointes), les comptes
utilisateurs, les notifications, le journal d'activité, et remet à zéro
les compteurs d'identifiants (les prochains dossiers/utilisateurs
repartiront de 1).

Conservé : le contenu du règlement CEAM (collection `config`), qui est
considéré comme du contenu éditorial, pas une donnée d'exploitation.
"""

from app.extensions import get_db

COLLECTIONS_TO_WIPE = ["ceam", "utilisateurs", "notifications", "logs", "attachments", "counters"]


def reset_database():
    """Supprime tous les documents des collections listées ci-dessus.
    Irréversible — aucune sauvegarde n'est faite avant suppression.
    Retourne un résumé {nom_collection: nombre_de_documents_supprimés}."""
    db = get_db()
    summary = {}
    for collection_name in COLLECTIONS_TO_WIPE:
        docs = list(db.collection(collection_name).stream())
        for doc in docs:
            doc.reference.delete()
        summary[collection_name] = len(docs)
    return summary