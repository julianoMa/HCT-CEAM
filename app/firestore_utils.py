"""
Firestore ne génère pas nativement d'identifiants entiers auto-incrémentés
(contrairement à une base SQL) : ses documents ont par défaut un ID de type
chaîne. Pour rester fidèle au schéma fourni (id int64 qui commence à 1 et
incrémente), on maintient un compteur dédié par collection dans un document
`counters/{collection}`, incrémenté de façon atomique via une transaction.
"""

from google.cloud.firestore_v1 import transactional


@transactional
def _increment_counter(transaction, counter_ref):
    snapshot = counter_ref.get(transaction=transaction)
    current = snapshot.get("value") if snapshot.exists else 0
    new_value = (current or 0) + 1
    transaction.set(counter_ref, {"value": new_value})
    return new_value


def next_id(db, collection_name):
    """Retourne le prochain identifiant entier pour une collection donnée,
    en l'incrémentant de façon atomique (sûr en cas d'accès concurrents)."""
    counter_ref = db.collection("counters").document(collection_name)
    transaction = db.transaction()
    return _increment_counter(transaction, counter_ref)
