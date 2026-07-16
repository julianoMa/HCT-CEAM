from datetime import datetime

from google.cloud.firestore_v1 import FieldFilter

from app.extensions import get_db
from app.firestore_utils import next_id

COLLECTION = "ceam"


class Rapport:
    # Statuts (schéma : status de 0 à 5)
    STATUS_NOUVEAU = 0
    STATUS_EN_EXAMEN = 1
    STATUS_EN_INSTRUCTION = 2
    STATUS_TRAITEMENT_SUSPENDU = 3
    STATUS_NON_RECEVABLE = 4
    STATUS_CLOTURE = 5

    STATUS_LABELS = {
        STATUS_NOUVEAU: "Nouveau",
        STATUS_EN_EXAMEN: "En cours d'examen",
        STATUS_EN_INSTRUCTION: "En cours d'instruction",
        STATUS_TRAITEMENT_SUSPENDU: "Traitement suspendu",
        STATUS_NON_RECEVABLE: "Non recevable",
        STATUS_CLOTURE: "Clôturé",
    }

    # Tous les statuts sauf "Clôturé" sont considérés comme des dossiers ouverts.
    OPEN_STATUSES = [
        STATUS_NOUVEAU,
        STATUS_EN_EXAMEN,
        STATUS_EN_INSTRUCTION,
        STATUS_TRAITEMENT_SUSPENDU,
        STATUS_NON_RECEVABLE,
    ]

    AFFECTATIONS = ["TMC", "NMH"]

    # --- Réponses officielles envoyées au plaignant ---
    # Le type est désormais un texte libre saisi par la commission (voir
    # ReponseForm). Seul l'accusé de réception automatique utilise un texte
    # de type fixe, généré à la création du rapport.
    ACCUSE_RECEPTION_TYPE = "Accusé de réception"

    ACCUSE_RECEPTION_TEXTE = (
        "Votre rapport a bien été reçu par la commission d'éthique des affaires "
        "médicales (CEAM). Il sera examiné dans les meilleurs délais ; vous "
        "recevrez une réponse sur l'issue de l'examen préliminaire dès que "
        "celui-ci sera terminé."
    )

    def __init__(self, id, plaignant_last_name, plaignant_first_name, plaignant_affectation, plaignant_rank,
                 concerne_last_name, concerne_first_name, concerne_affectation, concerne_rank,
                 event_date, event_hour, witness, description, proof,
                 send_date, owner_id, status, note, reponses=None):
        self.id = id
        self.plaignant_last_name = plaignant_last_name
        self.plaignant_first_name = plaignant_first_name
        self.plaignant_affectation = plaignant_affectation
        self.plaignant_rank = plaignant_rank
        self.concerne_last_name = concerne_last_name
        self.concerne_first_name = concerne_first_name
        self.concerne_affectation = concerne_affectation
        self.concerne_rank = concerne_rank
        self.event_date = event_date        # string "YYYY-MM-DD" (conforme au schéma : string)
        self.event_hour = event_hour        # string "HH:MM" (conforme au schéma : string)
        self.witness = witness
        self.description = description
        self.proof = proof
        self.send_date = send_date          # string ISO 8601 (conforme au schéma : string)
        self.owner_id = owner_id
        self.status = status
        self.note = note
        # Historique des réponses officielles envoyées au plaignant : liste de
        # dicts {type, content, author_name, author_rank, sent_at}.
        # Remplace l'ancien champ unique `conclusion`.
        self.reponses = reponses or []

    # --- Confort d'affichage ---
    @property
    def status_label(self):
        return self.STATUS_LABELS.get(self.status, "Inconnu")

    @property
    def reference(self):
        year = self.send_date[:4] if self.send_date else "0000"
        return f"CEAM-{year}-{self.id:04d}"

    @property
    def event_date_fr(self):
        try:
            return datetime.strptime(self.event_date, "%Y-%m-%d").strftime("%d/%m/%Y")
        except (ValueError, TypeError):
            return self.event_date

    @property
    def send_date_fr(self):
        try:
            return datetime.fromisoformat(self.send_date).strftime("%d/%m/%Y %H:%M")
        except (ValueError, TypeError):
            return self.send_date

    @property
    def reponses_affichage(self):
        """Historique des réponses, prêt à afficher (libellé de type + date
        FR), dans l'ordre chronologique d'envoi."""
        affichage = []
        for r in self.reponses:
            sent_at = r.get("sent_at", "")
            try:
                sent_at_fr = datetime.fromisoformat(sent_at).strftime("%d/%m/%Y à %H:%M")
            except (ValueError, TypeError):
                sent_at_fr = sent_at
            affichage.append({
                "type_label": r.get("type") or "Réponse",
                "content": r.get("content", ""),
                "author_name": r.get("author_name", ""),
                "author_rank": r.get("author_rank", ""),
                "sent_at_fr": sent_at_fr,
            })
        return affichage

    def to_dict(self):
        return {
            "plaignant_last_name": self.plaignant_last_name,
            "plaignant_first_name": self.plaignant_first_name,
            "plaignant_affectation": self.plaignant_affectation,
            "plaignant_rank": self.plaignant_rank,
            "concerne_last_name": self.concerne_last_name,
            "concerne_first_name": self.concerne_first_name,
            "concerne_affectation": self.concerne_affectation,
            "concerne_rank": self.concerne_rank,
            "event_date": self.event_date,
            "event_hour": self.event_hour,
            "witness": self.witness,
            "description": self.description,
            "proof": self.proof,
            "send_date": self.send_date,
            "owner_id": self.owner_id,
            "status": self.status,
            "note": self.note,
            "reponses": self.reponses,
        }

    @classmethod
    def _from_doc(cls, doc):
        data = doc.to_dict()
        # `conclusion` : ancien champ (avant l'historique des réponses),
        # ignoré s'il traîne encore sur d'anciens documents Firestore.
        data.pop("conclusion", None)
        data.setdefault("reponses", [])
        return cls(id=int(doc.id), **data)

    # --- Accès Firestore ---
    @classmethod
    def get(cls, rapport_id):
        db = get_db()
        doc = db.collection(COLLECTION).document(str(rapport_id)).get()
        return cls._from_doc(doc) if doc.exists else None

    @classmethod
    def create(cls, owner_id, plaignant_last_name, plaignant_first_name, plaignant_affectation, plaignant_rank,
               concerne_last_name, concerne_first_name, concerne_affectation, concerne_rank,
               event_date, event_hour, witness, description, proof):
        db = get_db()
        new_id = next_id(db, COLLECTION)
        rapport = cls(
            id=new_id,
            plaignant_last_name=plaignant_last_name, plaignant_first_name=plaignant_first_name,
            plaignant_affectation=plaignant_affectation, plaignant_rank=plaignant_rank,
            concerne_last_name=concerne_last_name, concerne_first_name=concerne_first_name,
            concerne_affectation=concerne_affectation, concerne_rank=concerne_rank,
            event_date=event_date, event_hour=event_hour, witness=witness,
            description=description, proof=proof,
            send_date=datetime.utcnow().isoformat(timespec="minutes"),
            owner_id=owner_id, status=cls.STATUS_NOUVEAU, note="", reponses=[],
        )
        db.collection(COLLECTION).document(str(new_id)).set(rapport.to_dict())
        # Accusé de réception automatique, immédiatement après la création.
        rapport.add_reponse(
            type_=cls.ACCUSE_RECEPTION_TYPE,
            content=cls.ACCUSE_RECEPTION_TEXTE,
            author_name="Commission CEAM",
            author_rank="Envoi automatique",
        )
        return rapport

    @staticmethod
    def _sort_by_send_date_desc(rapports):
        return sorted(rapports, key=lambda r: r.send_date or "", reverse=True)

    @classmethod
    def query_by_owner(cls, owner_id):
        db = get_db()
        docs = db.collection(COLLECTION).where(filter=FieldFilter("owner_id", "==", owner_id)).stream()
        return cls._sort_by_send_date_desc([cls._from_doc(d) for d in docs])

    @classmethod
    def query_open(cls, status_filter=None):
        """Dossiers non clôturés (ou d'un statut précis si status_filter est fourni)."""
        db = get_db()
        query = db.collection(COLLECTION)
        if status_filter is not None:
            query = query.where(filter=FieldFilter("status", "==", status_filter))
        else:
            query = query.where(filter=FieldFilter("status", "in", cls.OPEN_STATUSES))
        docs = query.stream()
        return cls._sort_by_send_date_desc([cls._from_doc(d) for d in docs])

    @classmethod
    def query_archived(cls):
        db = get_db()
        docs = (
            db.collection(COLLECTION)
            .where(filter=FieldFilter("status", "==", cls.STATUS_CLOTURE))
            .stream()
        )
        return cls._sort_by_send_date_desc([cls._from_doc(d) for d in docs])

    @classmethod
    def count_by_status(cls, status):
        db = get_db()
        docs = db.collection(COLLECTION).where(filter=FieldFilter("status", "==", status)).stream()
        return sum(1 for _ in docs)

    @classmethod
    def count_all(cls):
        db = get_db()
        docs = db.collection(COLLECTION).stream()
        return sum(1 for _ in docs)

    def update_instruction(self, status, note):
        """Met à jour le suivi interne (statut + note), indépendant des
        réponses officielles envoyées au plaignant."""
        db = get_db()
        db.collection(COLLECTION).document(str(self.id)).update(
            {"status": status, "note": note}
        )
        self.status = status
        self.note = note

    def add_reponse(self, type_, content, author_name, author_rank):
        """Ajoute une réponse officielle à l'historique et la persiste."""
        db = get_db()
        reponse = {
            "type": type_,
            "content": content,
            "author_name": author_name,
            "author_rank": author_rank,
            "sent_at": datetime.utcnow().isoformat(timespec="minutes"),
        }
        reponses = self.reponses + [reponse]
        db.collection(COLLECTION).document(str(self.id)).update({"reponses": reponses})
        self.reponses = reponses
        return reponse

    def __repr__(self):
        return f"<Rapport {self.reference} ({self.status_label})>"