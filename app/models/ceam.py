from datetime import datetime, timedelta

from google.api_core.exceptions import FailedPrecondition
from google.cloud.firestore_v1 import FieldFilter

from app.extensions import get_db
from app.firestore_utils import next_id
from app.timezone_utils import chat_date_label, format_utc, local_date

COLLECTION = "ceam"


def _group_chat_messages(messages, gap_minutes=0.5):
    """Regroupe des messages consécutifs du même auteur, espacés de moins
    de `gap_minutes` minutes entre eux, en un seul bloc visuel — comme le
    fait Discord/Slack. Un bloc = un seul en-tête (nom/avatar), un seul
    horodatage affiché à la fin, plusieurs contenus empilés dans la même
    carte. Si l'écart dépasse `gap_minutes`, ou que l'auteur change, un
    nouveau bloc démarre."""
    groups = []
    for m in messages:
        merged = False
        if groups:
            last_group = groups[-1]
            same_author = m["author_id"] is not None and m["author_id"] == last_group["author_id"]
            if same_author:
                try:
                    t1 = datetime.fromisoformat(last_group["entries"][-1]["sent_at_raw"])
                    t2 = datetime.fromisoformat(m["sent_at_raw"])
                    merged = 0 <= (t2 - t1).total_seconds() <= gap_minutes * 60
                except (ValueError, TypeError):
                    merged = False
        if merged:
            groups[-1]["entries"].append(m)
        else:
            groups.append({
                "author_id": m["author_id"],
                "author_name": m["author_name"],
                "author_rank": m["author_rank"],
                "entries": [m],
            })

    # Séparateur de date : un libellé de jour ("Aujourd'hui", "Hier",
    # "12 janvier") au-dessus du premier bloc de chaque nouvelle journée
    # civile (fuseau Europe/Paris) — jamais répété pour les blocs suivants
    # du même jour, même s'ils appartiennent à un auteur différent.
    last_date_key = None
    for group in groups:
        first_msg = group["entries"][0]
        try:
            date_key = local_date(first_msg["sent_at_raw"])
        except (ValueError, TypeError):
            date_key = None
        if date_key is not None and date_key != last_date_key:
            group["date_label"] = chat_date_label(first_msg["sent_at_raw"])
            last_date_key = date_key
        else:
            group["date_label"] = None

    return groups


class Rapport:
    # Statuts (schéma : status de 0 à 6)
    STATUS_NOUVEAU = 0
    STATUS_EN_EXAMEN = 1
    STATUS_EN_INSTRUCTION = 2
    STATUS_TRAITEMENT_SUSPENDU = 3
    STATUS_NON_RECEVABLE = 4
    STATUS_DECISION_RENDUE = 5
    STATUS_CLOTURE = 6

    STATUS_LABELS = {
        STATUS_NOUVEAU: "Nouveau",
        STATUS_EN_EXAMEN: "En cours d'examen",
        STATUS_EN_INSTRUCTION: "En cours d'instruction",
        STATUS_TRAITEMENT_SUSPENDU: "Traitement suspendu",
        STATUS_NON_RECEVABLE: "Non recevable",
        STATUS_DECISION_RENDUE: "Décision rendue",
        STATUS_CLOTURE: "Clôturé",
    }

    # Tous les statuts sauf "Clôturé" sont considérés comme des dossiers ouverts.
    OPEN_STATUSES = [
        STATUS_NOUVEAU,
        STATUS_EN_EXAMEN,
        STATUS_EN_INSTRUCTION,
        STATUS_TRAITEMENT_SUSPENDU,
        STATUS_NON_RECEVABLE,
        STATUS_DECISION_RENDUE,
    ]

    AFFECTATIONS = ["TMC", "NMH"]

    # Classement final au moment de la clôture (obligatoire avant de
    # pouvoir clôturer, sauf "Sans objet" qui est pré-proposé pour les
    # dossiers déclarés non recevables).
    CLASSEMENT_SANS_SUITE = "Classement sans suite"
    CLASSEMENT_AVEC_SANCTION = "Classement avec sanction"
    CLASSEMENT_SANS_SANCTION = "Classement sans sanction"
    CLASSEMENT_SANS_OBJET = "Sans objet"
    CLASSEMENTS = [
        CLASSEMENT_SANS_SUITE,
        CLASSEMENT_AVEC_SANCTION,
        CLASSEMENT_SANS_SANCTION,
        CLASSEMENT_SANS_OBJET,
    ]

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
                 proof_attachments=None, tiers_ids=None, tiers_roles=None, messages_locked=False,
                 classement=None, decision_rendered=False):
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

        self.tiers_roles = tiers_roles or {}

        # Si activé par la commission, bloque l'envoi de nouveaux messages
        # par le déclarant et les tiers (ils gardent la lecture de tout
        # l'historique) — la commission, elle, peut toujours écrire.
        self.messages_locked = messages_locked
        # Classement final, renseigné à la clôture (ou pré-proposé "Sans
        # objet" pour un dossier non recevable).
        self.classement = classement
        # True dès que "Marquer la décision comme rendue" a été cliqué :
        # bascule l'onglet Instruction CEAM vers l'écran de classement +
        # clôture, sans changer le statut tant que la clôture n'est pas
        # confirmée.
        self.decision_rendered = decision_rendered

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
        """Historique complet des réponses, prêt à afficher (libellé de
        type + date FR), SANS filtrage de visibilité — utilisé pour les
        exports/contextes où la vue complète est nécessaire (PDF CEAM,
        etc.). Pour l'affichage dans l'onglet Échanges, voir
        `visible_reponses` ci-dessous, qui applique la confidentialité."""
        affichage = []
        for r in self.reponses:
            sent_at = r.get("sent_at", "")
            sent_at_fr = format_utc(sent_at)
            affichage.append({
                "type_label": r.get("type") or "Réponse",
                "content": r.get("content", ""),
                "author_name": r.get("author_name", ""),
                "author_rank": r.get("author_rank", ""),
                "author_id": r.get("author_id"),
                "sent_at_fr": sent_at_fr,
                "sent_at_time": format_utc(sent_at, "%H:%M"),
                "sent_at_raw": sent_at,
                "attachments": r.get("attachments") or [],
                "read_by": r.get("read_by") or [],
                "visibility": r.get("visibility", "everyone"),
            })
        return affichage

    def _is_reponse_visible_to(self, r, user_id, is_ceam_member):
        """Règle de confidentialité d'un message. `visibility` identifie le
        FIL de discussion auquel appartient le message :
        - "everyone" : le fil général, visible par tout le monde.
        - un user_id : le fil privé entre la commission et CE participant
          externe précis (déclarant ou tiers) — peu importe lequel des
          deux a réellement écrit le message, le fil appartient à ce
          participant. La commission voit tous les fils (supervision
          complète) ; un participant externe ne voit que le fil général
          et SON PROPRE fil privé, jamais celui d'un autre participant."""
        if is_ceam_member:
            return True
        visibility = r.get("visibility", "everyone")
        if visibility == "everyone":
            return True
        return visibility == user_id

    def visible_reponses(self, user_id, is_ceam_member):
        """Messages de l'espace d'échanges réellement visibles par cette
        personne précise, tous fils confondus (voir _is_reponse_visible_to).
        Utilisé pour les compteurs globaux ; pour l'affichage par fil de
        discussion, voir `conversations_for` ci-dessous."""
        return [
            r for r in self.reponses_affichage
            if self._is_reponse_visible_to(
                {"visibility": r["visibility"], "author_id": r["author_id"]}, user_id, is_ceam_member,
            )
        ]

    def conversations_for(self, user_id, is_ceam_member, owner_user=None, tiers_users=None, group_gap_minutes=0.5):
        """Regroupe les messages en fils de discussion distincts, adaptés
        à qui regarde :
        - un membre CEAM voit le fil général + un fil privé par
          participant externe (déclarant, chaque tiers) — même vide, pour
          pouvoir en démarrer un ;
        - un participant externe (déclarant/tiers) ne voit que le fil
          général + SON PROPRE fil privé avec la commission.
        Chaque fil est un dict : {key, label, messages, groups, unread_count}.
        `messages` est la liste brute (chronologique) ; `groups` la même
        liste regroupée par blocs visuels (même auteur, moins de
        `group_gap_minutes` minutes d'écart — comme Discord/Slack).
        `key` vaut "everyone" ou l'ID (int) du participant externe
        propriétaire du fil — c'est aussi la valeur à soumettre dans le
        formulaire pour écrire dans ce fil précis.

        IMPORTANT : à appeler AVANT mark_messages_read — le marquage "lu"
        est déterminé ici via read_by, donc si les messages sont déjà
        marqués lus pour cette personne avant cet appel, plus aucun
        message n'apparaîtra jamais comme "Nouveau"."""
        all_messages = self.reponses_affichage

        def build_thread(key, label):
            if key == "everyone":
                messages = [m for m in all_messages if m["visibility"] == "everyone"]
            else:
                messages = [m for m in all_messages if m["visibility"] == key]
            unread = 0
            for m in messages:
                m["is_new"] = user_id not in (m.get("read_by") or []) and m["author_id"] != user_id
                if m["is_new"]:
                    unread += 1
            groups = _group_chat_messages(messages, group_gap_minutes)
            return {"key": key, "label": label, "messages": messages, "groups": groups, "unread_count": unread}

        threads = [build_thread("everyone", "Tout le monde")]

        if is_ceam_member:
            if owner_user is not None:
                threads.append(build_thread(owner_user.id, f"{owner_user.name} (Plaignant)"))

            for u in (tiers_users or []):
                role = (self.tiers_roles or {}).get(str(u.id), "Tiers")
                threads.append(build_thread(u.id, f"{u.name} ({role})"))
        else:
            threads.append(build_thread(user_id, "La commission"))

        return threads

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
                "motif": h.get("motif"),
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
            "tiers_roles": self.tiers_roles,
            "messages_locked": self.messages_locked,
            "classement": self.classement,
            "decision_rendered": self.decision_rendered,
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
        data.setdefault("tiers_roles", {})
        data.setdefault("messages_locked", False)
        data.setdefault("classement", None)
        data.setdefault("decision_rendered", False)
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

    @staticmethod
    def _count_query(query):
        """Compte les résultats d'une requête via l'agrégation Firestore
        native (COUNT) : ne lit que des entrées d'index, pas les documents
        eux-mêmes — une fraction du coût d'un streaming complet suivi d'un
        comptage en Python, quelle que soit la taille de la collection."""
        results = query.count(alias="total").get()
        return int(results[0][0].value)

    @classmethod
    def query_open(cls, status_filter=None, limit=None):
        """Dossiers non archivés : tous statuts confondus si status_filter
        n'est pas fourni (y compris Clôturé), ou un statut précis sinon.
        Un dossier archivé n'apparaît plus ici, quel que soit son statut.

        `limit`, si fourni, plafonne le nombre de documents réellement lus
        (trié par date d'envoi décroissante côté Firestore) — utile pour
        n'aller chercher que ce qu'il faut pour les N premières pages
        plutôt que toute la collection à chaque visite. Nécessite un index
        composite (archived [+ status] + send_date) ; s'il n'existe pas
        encore, on retombe automatiquement sur l'ancien comportement (tout
        charger, trier en Python) pour ne jamais casser la page en
        attendant sa création."""
        db = get_db()
        query = db.collection(COLLECTION).where(filter=FieldFilter("archived", "==", False))
        if status_filter is not None:
            query = query.where(filter=FieldFilter("status", "==", status_filter))
        if limit is not None:
            try:
                ordered = query.order_by("send_date", direction="DESCENDING").limit(limit)
                return [cls._from_doc(d) for d in ordered.stream()]
            except FailedPrecondition:
                pass  # index composite pas encore créé -> repli ci-dessous
        docs = query.stream()
        return cls._sort_by_send_date_desc([cls._from_doc(d) for d in docs])

    @classmethod
    def count_open(cls, status_filter=None):
        """Nombre de dossiers non archivés correspondant, sans lire leur
        contenu (voir _count_query)."""
        db = get_db()
        query = db.collection(COLLECTION).where(filter=FieldFilter("archived", "==", False))
        if status_filter is not None:
            query = query.where(filter=FieldFilter("status", "==", status_filter))
        return cls._count_query(query)

    @classmethod
    def query_archived(cls, limit=None):
        """Dossiers archivés par le président CEAM (indépendant du statut).
        Voir query_open pour le comportement de `limit`."""
        db = get_db()
        query = db.collection(COLLECTION).where(filter=FieldFilter("archived", "==", True))
        if limit is not None:
            try:
                ordered = query.order_by("send_date", direction="DESCENDING").limit(limit)
                return [cls._from_doc(d) for d in ordered.stream()]
            except FailedPrecondition:
                pass
        docs = query.stream()
        return cls._sort_by_send_date_desc([cls._from_doc(d) for d in docs])

    @classmethod
    def count_archived(cls):
        db = get_db()
        query = db.collection(COLLECTION).where(filter=FieldFilter("archived", "==", True))
        return cls._count_query(query)

    @classmethod
    def count_by_status(cls, status):
        db = get_db()
        query = db.collection(COLLECTION).where(filter=FieldFilter("status", "==", status))
        return cls._count_query(query)

    @classmethod
    def count_all(cls):
        db = get_db()
        return cls._count_query(db.collection(COLLECTION))

    # Dimensions du graphique en aire (évolution hebdomadaire), en unités SVG.
    _CHART_WIDTH = 700
    _CHART_HEIGHT = 180
    _CHART_PADDING_TOP = 16
    _CHART_PADDING_BOTTOM = 24
    _CHART_WEEKS = 12

    @classmethod
    def _build_weekly_chart(cls, rapports):
        """Construit la série des dépôts par semaine (12 dernières semaines,
        y compris celles à 0 dossier) et les coordonnées SVG prêtes à
        afficher pour un graphique en aire, sans dépendance JS."""
        weekly_counts = {}
        for r in rapports:
            if not r.send_date:
                continue
            try:
                dt = datetime.fromisoformat(r.send_date)
            except (ValueError, TypeError):
                continue
            monday = dt.date() - timedelta(days=dt.weekday())
            weekly_counts[monday] = weekly_counts.get(monday, 0) + 1

        today = datetime.utcnow().date()
        current_monday = today - timedelta(days=today.weekday())
        weeks = [current_monday - timedelta(weeks=i) for i in range(cls._CHART_WEEKS - 1, -1, -1)]
        series = [{"label": w.strftime("%d/%m"), "count": weekly_counts.get(w, 0)} for w in weeks]

        max_count = max((w["count"] for w in series), default=0)
        max_count_safe = max_count or 1  # évite une division par zéro si tout est à 0
        usable_height = cls._CHART_HEIGHT - cls._CHART_PADDING_TOP - cls._CHART_PADDING_BOTTOM
        baseline_y = cls._CHART_HEIGHT - cls._CHART_PADDING_BOTTOM
        step_x = cls._CHART_WIDTH / (len(series) - 1) if len(series) > 1 else 0

        coords = [
            (
                round(i * step_x, 1),
                round(baseline_y - (w["count"] / max_count_safe) * usable_height, 1),
            )
            for i, w in enumerate(series)
        ]
        points = " ".join(f"{x},{y}" for x, y in coords)
        area_points = f"0,{baseline_y} {points} {cls._CHART_WIDTH},{baseline_y}"

        return {
            "series": series,
            "points": points,
            "area_points": area_points,
            "max_count": max_count,
            "width": cls._CHART_WIDTH,
            "height": cls._CHART_HEIGHT,
        }

    @staticmethod
    def _affectation_breakdown(rapports, field_name):
        counts = {a: 0 for a in Rapport.AFFECTATIONS}
        for r in rapports:
            value = getattr(r, field_name, None)
            if value in counts:
                counts[value] += 1
        total = sum(counts.values())
        if total:
            percentages = {a: round(counts[a] / total * 100, 1) for a in Rapport.AFFECTATIONS}
        else:
            percentages = {a: 0 for a in Rapport.AFFECTATIONS}
        return {"counts": counts, "total": total, "percentages": percentages}

    # Clés courtes (sans espaces/accents) pour manipuler les classements
    # facilement côté template — l'ordre définit aussi l'ordre des
    # tranches dans le camembert.
    _CLASSEMENT_KEYS = [
        ("sans_suite", "CLASSEMENT_SANS_SUITE"),
        ("avec_sanction", "CLASSEMENT_AVEC_SANCTION"),
        ("sans_sanction", "CLASSEMENT_SANS_SANCTION"),
        ("sans_objet", "CLASSEMENT_SANS_OBJET"),
    ]

    @classmethod
    def _classement_breakdown(cls, rapports):
        """Répartition des classements finaux, uniquement sur les
        dossiers réellement clôturés (un dossier encore ouvert n'a pas de
        classement définitif). Calcule aussi les bornes cumulées prêtes à
        l'emploi pour dessiner un camembert CSS (conic-gradient) sans
        calcul dans le template."""
        keys = [(key, getattr(cls, attr_name)) for key, attr_name in cls._CLASSEMENT_KEYS]
        counts = {key: 0 for key, _ in keys}
        for r in rapports:
            if r.status == cls.STATUS_CLOTURE and r.classement in dict(keys).values():
                for key, value in keys:
                    if r.classement == value:
                        counts[key] += 1
                        break
        total = sum(counts.values())
        percentages = {}
        cumulative = {}
        running = 0.0
        for key, _ in keys:
            pct = round(counts[key] / total * 100, 1) if total else 0
            percentages[key] = pct
            running += pct
            cumulative[key] = round(running, 1)
        # Éviter qu'un arrondi laisse la dernière tranche un chouïa avant
        # 100% (visuellement, un tout petit trou dans le camembert).
        if total:
            last_key = keys[-1][0]
            cumulative[last_key] = 100
        return {
            "labels": {key: getattr(cls, attr_name) for key, attr_name in cls._CLASSEMENT_KEYS},
            "counts": counts,
            "total": total,
            "percentages": percentages,
            "cumulative": cumulative,
        }

    @classmethod
    def compute_statistiques(cls):
        """Calcule toutes les statistiques de la page Statistiques en un
        seul passage sur la collection (comptages par statut, répartition
        TMC/NMH du plaignant et du mis en cause, répartition des
        classements finaux, évolution hebdomadaire des dépôts)."""
        db = get_db()
        rapports = [cls._from_doc(d) for d in db.collection(COLLECTION).stream()]

        counts_by_status = {value: 0 for value in cls.STATUS_LABELS}
        for r in rapports:
            counts_by_status[r.status] = counts_by_status.get(r.status, 0) + 1

        plaignant_affectation = cls._affectation_breakdown(rapports, "plaignant_affectation")
        concerne_affectation = cls._affectation_breakdown(rapports, "concerne_affectation")
        classement_breakdown = cls._classement_breakdown(rapports)
        weekly_chart = cls._build_weekly_chart(rapports)

        return {
            "total": len(rapports),
            "counts_by_status": counts_by_status,
            "affectation_counts": plaignant_affectation["counts"],
            "affectation_total": plaignant_affectation["total"],
            "affectation_percentages": plaignant_affectation["percentages"],
            "concerne_affectation_counts": concerne_affectation["counts"],
            "concerne_affectation_total": concerne_affectation["total"],
            "concerne_affectation_percentages": concerne_affectation["percentages"],
            "classement_breakdown": classement_breakdown,
            "weekly_chart": weekly_chart,
        }

    def update_note(self, note):
        """Met à jour la note interne privée (visible uniquement par la
        commission), indépendamment de tout changement de statut."""
        db = get_db()
        db.collection(COLLECTION).document(str(self.id)).update({"note": note})
        self.note = note

    def _change_status(self, new_status, author_name, author_rank, motif=None):
        """Change le statut, ajoute l'entrée correspondante à l'historique
        (avec motif éventuel, ex: suspension), notifie le déclarant, et
        journalise l'action. Ne fait rien si le statut ne change pas
        réellement (idempotent)."""
        from app.models.audit_log import AuditLog  # import différé : évite un cycle d'import
        from app.models.notification import Notification  # idem

        if new_status == self.status:
            return
        db = get_db()
        ancien_label = self.status_label
        entry = {
            "status": new_status,
            "author_name": author_name,
            "author_rank": author_rank,
            "changed_at": datetime.utcnow().isoformat(timespec="minutes"),
        }
        if motif:
            entry["motif"] = motif
        new_history = self.status_history + [entry]

        db.collection(COLLECTION).document(str(self.id)).update({
            "status": new_status,
            "status_history": new_history,
        })
        self.status = new_status
        self.status_history = new_history
        self._notifier_changement_statut(entry)
        AuditLog.record(
            action=AuditLog.ACTION_STATUS_CHANGE,
            actor_name=author_name,
            details=(
                f"{author_name} ({author_rank}) a changé le statut du dossier "
                f"{self.reference} : « {ancien_label} » → « {self.status_label} »"
                + (f" (motif : {motif})" if motif else "")
            ),
        )
        Notification.create(
            user_id=self.owner_id,
            type=Notification.TYPE_STATUT_CHANGE,
            message=f"Le statut de ton dossier {self.reference} est passé à : {self.status_label}.",
            rapport_id=self.id,
        )

    def set_classement(self, classement):
        """Enregistre le classement final (ou pré-proposé), sans changer le
        statut ni ajouter d'entrée d'historique."""
        db = get_db()
        db.collection(COLLECTION).document(str(self.id)).update({"classement": classement})
        self.classement = classement

    def lancer_examen(self, author_name, author_rank):
        """Étape 1 → 2 : lance officiellement l'examen préliminaire."""
        self._change_status(self.STATUS_EN_EXAMEN, author_name, author_rank)

    def instruire(self, author_name, author_rank):
        """Étape 2 → 3 : l'examen préliminaire conclut à la nécessité
        d'instruire le dossier."""
        self._change_status(self.STATUS_EN_INSTRUCTION, author_name, author_rank)

    def marquer_non_recevable(self, author_name, author_rank):
        """Étape 2 (issue alternative) : le dossier est jugé non recevable.
        Oriente automatiquement vers la clôture, classement pré-proposé
        "Sans objet" (modifiable avant la confirmation finale)."""
        self._change_status(self.STATUS_NON_RECEVABLE, author_name, author_rank)
        if not self.classement:
            self.set_classement(self.CLASSEMENT_SANS_OBJET)

    def suspendre(self, author_name, author_rank, motif):
        """Étape 3 (pause) : suspend temporairement le traitement, avec un
        motif obligatoire (vérifié côté formulaire/route)."""
        self._change_status(self.STATUS_TRAITEMENT_SUSPENDU, author_name, author_rank, motif=motif)

    def reprendre_instruction(self, author_name, author_rank):
        """Depuis une suspension : reprend l'instruction normalement."""
        db = get_db()
        self._change_status(self.STATUS_EN_INSTRUCTION, author_name, author_rank)
        db.collection(COLLECTION).document(str(self.id)).update({"decision_rendered": False})
        self.decision_rendered = False

    def marquer_decision_rendue(self, author_name, author_rank):
        """Étape 3 → 4 : l'instruction est terminée, une décision a été
        prise. Ne clôture pas encore le dossier — fait juste apparaître
        l'espace de classement + clôture. Disponible aussi depuis une
        suspension (auquel cas le statut revient d'abord à "En cours
        d'instruction")."""
        from app.models.audit_log import AuditLog  # import différé : évite un cycle d'import

        if self.status == self.STATUS_TRAITEMENT_SUSPENDU:
            self._change_status(self.STATUS_EN_INSTRUCTION, author_name, author_rank)

        self._change_status(self.STATUS_DECISION_RENDUE, author_name, author_rank)

        db = get_db()
        db.collection(COLLECTION).document(str(self.id)).update({"decision_rendered": True})
        self.decision_rendered = True
        
        AuditLog.record(
            action=AuditLog.ACTION_STATUS_CHANGE,
            actor_name=author_name,
            details=f"{author_name} ({author_rank}) a marqué la décision comme rendue sur le dossier {self.reference}",
        )

    def cloturer(self, author_name, author_rank, classement):
        """Étape finale : clôture définitivement le dossier. Verrouille
        automatiquement les échanges (voir set_messages_locked)."""
        self.set_classement(classement)
        self._change_status(self.STATUS_CLOTURE, author_name, author_rank)
        self.set_messages_locked(True)

    def add_reponse(self, type_, content, author_name, author_rank, author_id=None, author_is_ceam=True,
                    attachments=None, visibility="everyone"):
        """Ajoute un message à un fil de discussion du dossier (réponse
        officielle CEAM, ou message libre d'un déclarant/tiers/membre CEAM),
        le persiste, et notifie les personnes autorisées à le voir.

        visibility identifie le FIL auquel appartient le message :
        - "everyone" : le fil général, visible par tout le monde — défaut.
        - un user_id (int) : le fil privé entre la commission et ce
          participant externe précis (déclarant ou tiers), peu importe
          lequel des deux écrit dans ce fil. La commission voit toujours
          tous les fils (supervision complète du dossier)."""
        from app.models.audit_log import AuditLog  # import différé : évite un cycle d'import
        from app.models.notification import Notification  # idem

        db = get_db()
        reponse = {
            "type": type_,
            "content": content,
            "author_name": author_name,
            "author_rank": author_rank,
            "author_id": author_id,
            "sent_at": datetime.utcnow().isoformat(timespec="minutes"),
            "attachments": attachments or [],
            # L'auteur a évidemment déjà "lu" son propre message.
            "read_by": [author_id] if author_id is not None else [],
            "visibility": visibility,
        }
        reponses = self.reponses + [reponse]
        db.collection(COLLECTION).document(str(self.id)).update({"reponses": reponses})
        self.reponses = reponses
        self._notifier_message(reponse, author_id, author_is_ceam)
        AuditLog.record(
            action=AuditLog.ACTION_REPONSE_ADD,
            actor_name=author_name,
            details=f"{author_name} ({author_rank}) a envoyé un message « {type_} » sur le dossier {self.reference}",
        )
        # L'accusé de réception automatique est déjà couvert par la
        # notification "Rapport envoyé" créée à la création du dossier —
        # pas besoin de doublonner ici.
        if type_ != self.ACCUSE_RECEPTION_TYPE:
            destinataires = set()
            if visibility == "everyone":
                if author_id != self.owner_id:
                    destinataires.add(self.owner_id)
                destinataires.update(t for t in self.tiers_ids if t != author_id)
            else:
                # visibility est l'ID du participant externe propriétaire
                # du fil privé. Si c'est LUI qui vient d'écrire, aucune
                # notification in-app n'est créée : la commission n'a pas
                # de notification in-app individuelle (seulement des MP
                # Discord, voir _notifier_message), et il n'y a personne
                # d'autre à prévenir sur ce fil. Si c'est la commission qui
                # cible ce participant, on le notifie en in-app.
                if visibility != author_id:
                    destinataires.add(visibility)
            for user_id in destinataires:
                Notification.create(
                    user_id=user_id,
                    type=Notification.TYPE_REPONSE_AJOUTEE,
                    message=f"{author_name} a ajouté un message ({type_}) sur le dossier {self.reference}.",
                    rapport_id=self.id,
                )
        return reponse

    def mark_messages_read(self, user_id, is_ceam_member=False):
        """Marque comme lus, pour cette personne, tous les messages
        qu'elle peut réellement voir (respecte la confidentialité —
        inutile et incorrect de marquer "lu" un message qu'elle ne voit
        même pas)."""
        changed = False
        reponses = []
        for r in self.reponses:
            read_by = r.get("read_by") or []
            visible = self._is_reponse_visible_to(r, user_id, is_ceam_member)
            if visible and user_id not in read_by:
                read_by = read_by + [user_id]
                changed = True
            reponses.append({**r, "read_by": read_by})
        if changed:
            db = get_db()
            db.collection(COLLECTION).document(str(self.id)).update({"reponses": reponses})
            self.reponses = reponses

    def unread_messages_count(self, user_id, is_ceam_member=False):
        return sum(
            1 for r in self.reponses
            if self._is_reponse_visible_to(r, user_id, is_ceam_member)
            and user_id not in (r.get("read_by") or [])
        )

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

    def _notifier_message(self, reponse, author_id, author_is_ceam):
        """MP Discord aux personnes autorisées à voir ce message précis,
        selon le fil auquel il appartient :
        - "everyone" : déclarant + tiers (si auteur CEAM) ou toute la
          commission (si auteur externe), comme avant.
        - un fil privé (visibility = user_id du participant externe
          propriétaire du fil) :
          - si c'est CE participant qui vient d'écrire, on notifie toute
            la commission (c'est elle qui doit être mise au courant) ;
          - si c'est la commission qui vient d'écrire (ciblant ce
            participant), on ne notifie que lui."""
        from app.models.user import User  # import différé : évite un cycle d'import
        from app.notifications import build_embed, send_discord_dm

        embed = build_embed(
            title=f"📬 Mise à jour de ton dossier {self.reference}",
            description=f"{reponse['author_name']} a ajouté un message dans les échanges du dossier.",
            fields=[{"name": "Type", "value": reponse["type"], "inline": False}],
            url=self._detail_url(),
        )
        visibility = reponse.get("visibility", "everyone")

        if isinstance(visibility, int):
            if visibility == author_id:
                # Le propriétaire du fil privé vient d'y écrire -> notifier
                # toute la commission.
                for membre in User.list_ceam_members():
                    if membre.id != author_id:
                        send_discord_dm(membre.discord_id, embed=embed)
            else:
                # La commission vient d'écrire dans le fil privé de ce
                # participant -> ne notifier que lui.
                cible = User.get(visibility)
                if cible is not None:
                    send_discord_dm(cible.discord_id, embed=embed)
            return

        # visibility == "everyone"
        if author_is_ceam:
            destinataires_ids = {self.owner_id, *self.tiers_ids} - {author_id}
            for user_id in destinataires_ids:
                user = User.get(user_id)
                if user is not None:
                    send_discord_dm(user.discord_id, embed=embed)
        else:
            for membre in User.list_ceam_members():
                if membre.id != author_id:
                    send_discord_dm(membre.discord_id, embed=embed)

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

    def set_messages_locked(self, locked):
        """Active/désactive la possibilité pour le déclarant et les tiers
        d'envoyer de nouveaux messages dans les échanges. La commission
        peut toujours écrire, et tout le monde garde la lecture de
        l'historique quel que soit l'état du verrou."""
        db = get_db()
        db.collection(COLLECTION).document(str(self.id)).update({"messages_locked": locked})
        self.messages_locked = locked

    def add_tiers(self, user_id, role_ajout="Tiers"):
        """Ajoute un utilisateur tiers, qui pourra désormais consulter ce
        dossier (et sera notifié in-app + Discord). Retourne False sans
        rien faire si la personne est déjà le déclarant ou déjà tiers.

        `role_ajout` (Tiers / Mis en cause / Témoin) n'affecte QUE le
        texte du MP Discord envoyé à la personne — ses droits d'accès
        réels au dossier restent ceux d'un tiers classique, quel que soit
        le rôle choisi ici."""
        if user_id == self.owner_id or user_id in self.tiers_ids:
            return False
        db = get_db()
        tiers_ids = self.tiers_ids + [user_id]

        tiers_roles = dict(self.tiers_roles or {})
        tiers_roles[str(user_id)] = role_ajout

        db.collection(COLLECTION).document(str(self.id)).update({"tiers_ids": tiers_ids, "tiers_roles": tiers_roles})
        self.tiers_ids = tiers_ids
        self.tiers_roles = tiers_roles
        self._notifier_tiers_ajoute(user_id, role_ajout)
        return True

    def remove_tiers(self, user_id):
        """Retire l'accès d'un tiers précédemment ajouté."""
        if user_id not in self.tiers_ids:
            return False
        db = get_db()
        tiers_ids = [t for t in self.tiers_ids if t != user_id]

        tiers_roles = dict(self.tiers_roles or {})
        tiers_roles.pop(str(user_id), None)

        db.collection(COLLECTION).document(str(self.id)).update({"tiers_ids": tiers_ids, "tiers_roles": tiers_roles})
        self.tiers_ids = tiers_ids
        self.tiers_roles = tiers_roles
        return True

    def _notifier_tiers_ajoute(self, user_id, role_ajout="Tiers"):
        """Notifie (in-app + MP Discord) la personne ajoutée comme tiers.
        Le message in-app reste générique ; seul le MP Discord précise en
        tant que quoi (Tiers / Mis en cause / Témoin) elle a été ajoutée —
        purement informatif, sans effet sur ses droits d'accès réels."""
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
                f"La commission t'a ajouté(e) à ce dossier en tant que "
                f"{role_ajout.lower()} : tu peux désormais le consulter."
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