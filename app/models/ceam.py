from datetime import datetime

from google.cloud.firestore_v1 import FieldFilter

from app.extensions import get_db
from app.firestore_utils import next_id
from app.timezone_utils import format_utc

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

    # Nombre de jours au-delà duquel un dossier resté au statut "Nouveau"
    # déclenche une alerte de relance dans les statistiques.
    STALE_NOUVEAU_JOURS = 5

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
                 event_date, event_hour, location, witness, description, proof,
                 send_date, owner_id, status, note, reponses=None, archived=False, status_history=None,
                 proof_attachments=None, tiers_ids=None):
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
        self.location = location            # lieu précis de l'incident
        self.witness = witness
        self.description = description
        self.proof = proof                  # liens (texte libre)
        self.proof_attachments = proof_attachments or []  # fichiers uploadés (PDF, images)
        self.send_date = send_date          # string ISO 8601 (conforme au schéma : string)
        self.owner_id = owner_id
        self.status = status
        self.note = note
        # Historique des réponses officielles envoyées au plaignant : liste de
        # dicts {type, content, author_name, author_rank, sent_at}.
        # Remplace l'ancien champ unique `conclusion`.
        self.reponses = reponses or []
        # Archivage : indépendant du statut. Un dossier clôturé (status =
        # STATUS_CLOTURE) reste visible par le déclarant tant qu'il n'a pas
        # été explicitement archivé par le président CEAM.
        self.archived = archived
        # Historique des changements de statut : liste de dicts
        # {status, author_name, author_rank, changed_at}.
        self.status_history = status_history or []
        # Tiers ajoutés par la commission : utilisateurs (autres que le
        # déclarant) autorisés à consulter ce dossier, en plus de la CEAM.
        self.tiers_ids = tiers_ids or []

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
        return format_utc(self.send_date, "%d/%m/%Y %H:%M")

    @property
    def reponses_affichage(self):
        """Historique des réponses, prêt à afficher (libellé de type + date
        FR), dans l'ordre chronologique d'envoi."""
        affichage = []
        for r in self.reponses:
            sent_at = r.get("sent_at", "")
            sent_at_fr = format_utc(sent_at)
            affichage.append({
                "type_label": r.get("type") or "Réponse",
                "content": r.get("content", ""),
                "author_name": r.get("author_name", ""),
                "author_rank": r.get("author_rank", ""),
                "sent_at_fr": sent_at_fr,
                "attachments": r.get("attachments") or [],
            })
        return affichage

    @property
    def status_history_affichage(self):
        """Historique des changements de statut, prêt à afficher."""
        affichage = []
        for h in self.status_history:
            changed_at = h.get("changed_at", "")
            changed_at_fr = format_utc(changed_at)
            affichage.append({
                "status_value": h.get("status"),
                "status_label": self.STATUS_LABELS.get(h.get("status"), "Inconnu"),
                "author_name": h.get("author_name", ""),
                "author_rank": h.get("author_rank", ""),
                "changed_at_fr": changed_at_fr,
            })
        return affichage

    @property
    def delai_traitement_jours(self):
        """Nombre de jours entre le dépôt et la 1ère clôture, ou None si le
        dossier n'a jamais été clôturé."""
        cloture_entries = [h for h in self.status_history if h.get("status") == self.STATUS_CLOTURE]
        if not cloture_entries or not self.send_date:
            return None
        try:
            depot = datetime.fromisoformat(self.send_date)
            cloture = datetime.fromisoformat(cloture_entries[0]["changed_at"])
            return (cloture - depot).total_seconds() / 86400
        except (ValueError, TypeError, KeyError):
            return None

    @property
    def jours_depuis_depot(self):
        """Nombre de jours écoulés depuis le dépôt du rapport (à l'instant présent)."""
        if not self.send_date:
            return None
        try:
            depot = datetime.fromisoformat(self.send_date)
            return (datetime.utcnow() - depot).total_seconds() / 86400
        except (ValueError, TypeError):
            return None

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
            "location": self.location,
            "witness": self.witness,
            "description": self.description,
            "proof": self.proof,
            "proof_attachments": self.proof_attachments,
            "send_date": self.send_date,
            "owner_id": self.owner_id,
            "status": self.status,
            "note": self.note,
            "reponses": self.reponses,
            "archived": self.archived,
            "status_history": self.status_history,
            "tiers_ids": self.tiers_ids,
        }

    @classmethod
    def _from_doc(cls, doc):
        data = doc.to_dict()
        # `conclusion` : ancien champ (avant l'historique des réponses),
        # ignoré s'il traîne encore sur d'anciens documents Firestore.
        data.pop("conclusion", None)
        data.setdefault("reponses", [])
        data.setdefault("archived", False)
        data.setdefault("status_history", [])
        data.setdefault("location", "")
        data.setdefault("proof_attachments", [])
        data.setdefault("tiers_ids", [])
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
               event_date, event_hour, location, witness, description, proof):
        db = get_db()
        new_id = next_id(db, COLLECTION)
        send_date = datetime.utcnow().isoformat(timespec="minutes")
        rapport = cls(
            id=new_id,
            plaignant_last_name=plaignant_last_name, plaignant_first_name=plaignant_first_name,
            plaignant_affectation=plaignant_affectation, plaignant_rank=plaignant_rank,
            concerne_last_name=concerne_last_name, concerne_first_name=concerne_first_name,
            concerne_affectation=concerne_affectation, concerne_rank=concerne_rank,
            event_date=event_date, event_hour=event_hour, location=location, witness=witness,
            description=description, proof=proof, proof_attachments=[],
            send_date=send_date,
            owner_id=owner_id, status=cls.STATUS_NOUVEAU, note="", reponses=[],
            status_history=[{
                "status": cls.STATUS_NOUVEAU,
                "author_name": "Commission CEAM",
                "author_rank": "Création du dossier",
                "changed_at": send_date,
            }],
        )
        db.collection(COLLECTION).document(str(new_id)).set(rapport.to_dict())
        # Accusé de réception automatique, immédiatement après la création.
        rapport.add_reponse(
            type_=cls.ACCUSE_RECEPTION_TYPE,
            content=cls.ACCUSE_RECEPTION_TEXTE,
            author_name="Commission CEAM",
            author_rank="Envoi automatique",
        )
        rapport._notifier_nouveau_rapport()

        from app.models.notification import Notification  # import différé : évite un cycle d'import
        Notification.create(
            user_id=owner_id,
            type=Notification.TYPE_RAPPORT_ENVOYE,
            message=f"Ton rapport {rapport.reference} a bien été envoyé à la commission.",
            rapport_id=rapport.id,
        )

        return rapport

    @staticmethod
    def _sort_by_send_date_desc(rapports):
        return sorted(rapports, key=lambda r: r.send_date or "", reverse=True)

    @classmethod
    def query_visible_to(cls, user_id):
        """Dossiers visibles pour un déclarant : les siens, plus ceux où il
        a été ajouté comme tiers par la commission (non archivés)."""
        db = get_db()
        docs_owner = (
            db.collection(COLLECTION)
            .where(filter=FieldFilter("owner_id", "==", user_id))
            .where(filter=FieldFilter("archived", "==", False))
            .stream()
        )
        docs_tiers = (
            db.collection(COLLECTION)
            .where(filter=FieldFilter("tiers_ids", "array_contains", user_id))
            .where(filter=FieldFilter("archived", "==", False))
            .stream()
        )
        rapports_by_id = {}
        for d in docs_owner:
            r = cls._from_doc(d)
            rapports_by_id[r.id] = r
        for d in docs_tiers:
            r = cls._from_doc(d)
            rapports_by_id[r.id] = r
        return cls._sort_by_send_date_desc(list(rapports_by_id.values()))

    @classmethod
    def query_open(cls, status_filter=None):
        """Dossiers non archivés : tous statuts confondus si status_filter
        n'est pas fourni (y compris Clôturé), ou un statut précis sinon.
        Un dossier archivé n'apparaît plus ici, quel que soit son statut."""
        db = get_db()
        query = db.collection(COLLECTION).where(filter=FieldFilter("archived", "==", False))
        if status_filter is not None:
            query = query.where(filter=FieldFilter("status", "==", status_filter))
        docs = query.stream()
        return cls._sort_by_send_date_desc([cls._from_doc(d) for d in docs])

    @classmethod
    def query_archived(cls):
        """Dossiers archivés par le président CEAM (indépendant du statut)."""
        db = get_db()
        docs = (
            db.collection(COLLECTION)
            .where(filter=FieldFilter("archived", "==", True))
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

    @classmethod
    def compute_statistiques(cls):
        """Calcule toutes les statistiques de la page Statistiques en un
        seul passage sur la collection (comptages par statut, délai moyen
        de traitement, répartition TMC/NMH, alertes de relance)."""
        db = get_db()
        rapports = [cls._from_doc(d) for d in db.collection(COLLECTION).stream()]

        counts_by_status = {value: 0 for value in cls.STATUS_LABELS}
        affectation_counts = {a: 0 for a in cls.AFFECTATIONS}
        delais = []
        relances = []

        for r in rapports:
            counts_by_status[r.status] = counts_by_status.get(r.status, 0) + 1

            if r.plaignant_affectation in affectation_counts:
                affectation_counts[r.plaignant_affectation] += 1

            delai = r.delai_traitement_jours
            if delai is not None:
                delais.append(delai)

            jours = r.jours_depuis_depot
            if (
                not r.archived
                and r.status == cls.STATUS_NOUVEAU
                and jours is not None
                and jours >= cls.STALE_NOUVEAU_JOURS
            ):
                relances.append(r)

        relances.sort(key=lambda r: r.send_date or "")

        affectation_total = sum(affectation_counts.values())
        if affectation_total:
            affectation_percentages = {
                a: round(affectation_counts[a] / affectation_total * 100, 1) for a in cls.AFFECTATIONS
            }
        else:
            affectation_percentages = {a: 0 for a in cls.AFFECTATIONS}

        return {
            "total": len(rapports),
            "counts_by_status": counts_by_status,
            "delai_moyen_jours": (sum(delais) / len(delais)) if delais else None,
            "delai_moyen_dossiers": len(delais),
            "affectation_counts": affectation_counts,
            "affectation_total": affectation_total,
            "affectation_percentages": affectation_percentages,
            "relances": relances,
        }

    def update_instruction(self, status, note, author_name, author_rank):
        """Met à jour le suivi interne (statut + note), indépendant des
        réponses officielles envoyées au plaignant. N'ajoute une entrée à
        l'historique que si le statut change réellement (pas si seule la
        note est modifiée)."""
        from app.models.audit_log import AuditLog  # import différé : évite un cycle d'import
        from app.models.notification import Notification  # idem

        db = get_db()
        updates = {"status": status, "note": note}
        status_changed = status != self.status
        ancien_label = self.status_label

        if status_changed:
            entry = {
                "status": status,
                "author_name": author_name,
                "author_rank": author_rank,
                "changed_at": datetime.utcnow().isoformat(timespec="minutes"),
            }
            new_history = self.status_history + [entry]
            updates["status_history"] = new_history

        db.collection(COLLECTION).document(str(self.id)).update(updates)
        self.status = status
        self.note = note
        if status_changed:
            self.status_history = new_history
            self._notifier_changement_statut(entry)
            AuditLog.record(
                action=AuditLog.ACTION_STATUS_CHANGE,
                actor_name=author_name,
                details=(
                    f"{author_name} ({author_rank}) a changé le statut du dossier "
                    f"{self.reference} : « {ancien_label} » → « {self.status_label} »"
                ),
            )
            Notification.create(
                user_id=self.owner_id,
                type=Notification.TYPE_STATUT_CHANGE,
                message=f"Le statut de ton dossier {self.reference} est passé à : {self.status_label}.",
                rapport_id=self.id,
            )

    def add_reponse(self, type_, content, author_name, author_rank, attachments=None):
        """Ajoute une réponse officielle à l'historique, la persiste, et
        notifie le déclarant par MP Discord."""
        from app.models.audit_log import AuditLog  # import différé : évite un cycle d'import
        from app.models.notification import Notification  # idem

        db = get_db()
        reponse = {
            "type": type_,
            "content": content,
            "author_name": author_name,
            "author_rank": author_rank,
            "sent_at": datetime.utcnow().isoformat(timespec="minutes"),
            "attachments": attachments or [],
        }
        reponses = self.reponses + [reponse]
        db.collection(COLLECTION).document(str(self.id)).update({"reponses": reponses})
        self.reponses = reponses
        self._notifier_nouvelle_reponse(reponse)
        AuditLog.record(
            action=AuditLog.ACTION_REPONSE_ADD,
            actor_name=author_name,
            details=f"{author_name} ({author_rank}) a envoyé une réponse « {type_} » sur le dossier {self.reference}",
        )
        # L'accusé de réception automatique est déjà couvert par la
        # notification "Rapport envoyé" créée à la création du dossier —
        # pas besoin de doublonner ici.
        if type_ != self.ACCUSE_RECEPTION_TYPE:
            Notification.create(
                user_id=self.owner_id,
                type=Notification.TYPE_REPONSE_AJOUTEE,
                message=f"La commission a ajouté une réponse ({type_}) à ton dossier {self.reference}.",
                rapport_id=self.id,
            )
        return reponse

    def _notifier_nouveau_rapport(self):
        """MP à tous les membres de la commission lors du dépôt d'un rapport."""
        from app.models.user import User  # import différé : évite un cycle d'import
        from app.notifications import build_embed, send_discord_dm

        embed = build_embed(
            title=f"📋 Nouveau rapport : {self.reference}",
            description=(
                f"{self.plaignant_first_name} {self.plaignant_last_name} c/ "
                f"{self.concerne_first_name} {self.concerne_last_name}"
            ),
            fields=[
                {"name": "Affectation", "value": self.plaignant_affectation, "inline": True},
                {"name": "Statut", "value": self.status_label, "inline": True},
            ],
            url=self._detail_url(),
        )
        for membre in User.list_ceam_members():
            send_discord_dm(membre.discord_id, embed=embed)

    def _notifier_nouvelle_reponse(self, reponse):
        """MP au déclarant lors de l'ajout d'une réponse officielle."""
        from app.models.user import User  # import différé : évite un cycle d'import
        from app.notifications import build_embed, send_discord_dm

        owner = User.get(self.owner_id)
        if owner is None:
            return
        embed = build_embed(
            title=f"📬 Mise à jour de ton dossier {self.reference}",
            description="La commission a ajouté une nouvelle réponse officielle à ton dossier.",
            fields=[{"name": "Type de réponse", "value": reponse["type"], "inline": False}],
            url=self._detail_url(),
        )
        send_discord_dm(owner.discord_id, embed=embed)

    def _notifier_changement_statut(self, entry):
        """MP au déclarant lors d'un changement de statut."""
        from app.models.user import User  # import différé : évite un cycle d'import
        from app.notifications import build_embed, send_discord_dm

        owner = User.get(self.owner_id)
        if owner is None:
            return
        label = self.STATUS_LABELS.get(entry["status"], "Inconnu")
        embed = build_embed(
            title=f"🔄 Mise à jour de ton dossier {self.reference}",
            description="Le statut de ton dossier a changé.",
            fields=[{"name": "Nouveau statut", "value": label, "inline": False}],
            url=self._detail_url(),
        )
        send_discord_dm(owner.discord_id, embed=embed)

    def _detail_url(self):
        """URL absolue vers la page de détail de ce dossier, ou None si
        appelé hors contexte de requête (ex: script, tests)."""
        try:
            from flask import url_for
            return url_for("ceam.detail", rapport_id=self.id, _external=True)
        except RuntimeError:
            return None

    def set_proof_attachments(self, attachments):
        """Enregistre les fichiers de preuve uploadés au dépôt. Appelé après
        Rapport.create(), une fois l'ID du dossier connu (nécessaire pour
        organiser le stockage des fichiers)."""
        db = get_db()
        db.collection(COLLECTION).document(str(self.id)).update({"proof_attachments": attachments})
        self.proof_attachments = attachments

    def add_tiers(self, user_id):
        """Ajoute un utilisateur tiers, qui pourra désormais consulter ce
        dossier (et sera notifié in-app + Discord). Retourne False sans
        rien faire si la personne est déjà le déclarant ou déjà tiers."""
        if user_id == self.owner_id or user_id in self.tiers_ids:
            return False
        db = get_db()
        tiers_ids = self.tiers_ids + [user_id]
        db.collection(COLLECTION).document(str(self.id)).update({"tiers_ids": tiers_ids})
        self.tiers_ids = tiers_ids
        self._notifier_tiers_ajoute(user_id)
        return True

    def remove_tiers(self, user_id):
        """Retire l'accès d'un tiers précédemment ajouté."""
        if user_id not in self.tiers_ids:
            return False
        db = get_db()
        tiers_ids = [t for t in self.tiers_ids if t != user_id]
        db.collection(COLLECTION).document(str(self.id)).update({"tiers_ids": tiers_ids})
        self.tiers_ids = tiers_ids
        return True

    def _notifier_tiers_ajoute(self, user_id):
        """Notifie (in-app + MP Discord) la personne ajoutée comme tiers."""
        from app.models.notification import Notification  # import différé : évite un cycle d'import
        from app.models.user import User
        from app.notifications import build_embed, send_discord_dm

        Notification.create(
            user_id=user_id,
            type=Notification.TYPE_TIERS_AJOUTE,
            message=f"Tu as été ajouté(e) au dossier {self.reference} et peux désormais le consulter.",
            rapport_id=self.id,
        )
        user = User.get(user_id)
        if user is None:
            return
        embed = build_embed(
            title=f"👥 Accès au dossier {self.reference}",
            description=(
                "La commission t'a ajouté(e) à ce dossier en tant que tiers : "
                "tu peux désormais le consulter."
            ),
            url=self._detail_url(),
        )
        send_discord_dm(user.discord_id, embed=embed)

    def archive(self):
        """Archive le dossier : il disparaît des vues du déclarant et du
        Suivi CEAM, et n'est plus visible que dans Archives."""
        db = get_db()
        db.collection(COLLECTION).document(str(self.id)).update({"archived": True})
        self.archived = True

    @classmethod
    def delete(cls, rapport_id):
        """Supprime définitivement un dossier (irréversible)."""
        db = get_db()
        db.collection(COLLECTION).document(str(rapport_id)).delete()

    @staticmethod
    def filter_by_search(rapports, query):
        """Filtre une liste de Rapport déjà chargée par référence, nom du
        plaignant ou du concerné (recherche insensible à la casse).
        Firestore ne fait pas de recherche texte native ; pour le volume
        d'un outil interne, filtrer en mémoire après la requête Firestore
        est largement suffisant et évite d'ajouter un service tiers."""
        query = (query or "").strip().lower()
        if not query:
            return rapports

        def matches(r):
            haystack = " ".join([
                r.reference,
                r.plaignant_first_name, r.plaignant_last_name,
                r.concerne_first_name, r.concerne_last_name,
            ]).lower()
            return query in haystack

        return [r for r in rapports if matches(r)]

    def __repr__(self):
        return f"<Rapport {self.reference} ({self.status_label})>"