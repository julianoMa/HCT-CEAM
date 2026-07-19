from flask import Blueprint, Response, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app.ceam.forms import ClotureForm, MessageForm, NoteForm, RapportForm, ReglementForm, ReponseForm, SuspensionForm
from app.models.audit_log import AuditLog
from app.models.ceam import Rapport
from app.models.notification import Notification
from app.models.reglement import Reglement
from app.models.user import User
from app.pdf_export import generate_dossier_pdf
from app.permissions import requires_role
from app.storage import fetch_attachment, upload_reponse_attachment

bp = Blueprint("ceam", __name__, url_prefix="/ceam")


@bp.route("/depot", methods=["GET", "POST"])
@login_required
def depot():
    form = RapportForm()
    if request.method == "GET":
        # Pré-remplissage à partir des rôles Discord de la personne (voir
        # app/discord_roles.py), synchronisés à chaque connexion. Reste
        # vide si aucun rôle de grade/affectation connu n'a été détecté.
        if current_user.rank:
            form.plaignant_rank.data = current_user.rank
        if current_user.affectation:
            form.plaignant_affectation.data = current_user.affectation
        # Nom/prénom déduits du pseudo du serveur HCT (ex: "Jean Dupont"),
        # en supposant l'ordre "Prénom Nom". Simple pré-remplissage,
        # modifiable si le pseudo ne suit pas exactement ce format (surnom,
        # grade inclus dans le pseudo, nom composé...).
        if current_user.name:
            prenom, _, nom = current_user.name.strip().partition(" ")
            form.plaignant_first_name.data = prenom
            if nom:
                form.plaignant_last_name.data = nom
    if form.validate_on_submit():
        rapport = Rapport.create(
            owner_id=current_user.id,
            plaignant_last_name=form.plaignant_last_name.data,
            plaignant_first_name=form.plaignant_first_name.data,
            plaignant_affectation=form.plaignant_affectation.data,
            plaignant_rank=form.plaignant_rank.data,
            concerne_last_name=form.concerne_last_name.data,
            concerne_first_name=form.concerne_first_name.data,
            concerne_affectation=form.concerne_affectation.data,
            concerne_rank=form.concerne_rank.data,
            event_date=form.event_date.data.isoformat(),
            event_hour=form.event_hour.data.strftime("%H:%M"),
            location=form.location.data,
            witness=form.witness.data,
            description=form.description.data,
            proof=form.proof.data,
        )

        # Les fichiers ne peuvent être uploadés qu'une fois l'ID du dossier
        # connu (le stockage est organisé par dossier) : on le fait donc
        # juste après la création, puis on rattache le résultat au rapport.
        attachments = []
        rejected = []
        for uploaded in request.files.getlist("proof_files"):
            if not uploaded or not uploaded.filename:
                continue
            try:
                meta = upload_reponse_attachment(rapport.id, uploaded)
            except Exception:  # noqa: BLE001 - un souci Storage ne doit pas bloquer le dépôt
                meta = None
            if meta:
                attachments.append(meta)
            else:
                rejected.append(uploaded.filename)
        if attachments:
            rapport.set_proof_attachments(attachments)

        AuditLog.record(
            action=AuditLog.ACTION_RAPPORT_CREATE,
            actor_name=current_user.name,
            actor_id=current_user.id,
            details=f"{current_user.name} a déposé le rapport {rapport.reference}",
        )
        if rejected:
            flash(
                "Rapport envoyé, mais certains fichiers de preuve ont été ignorés (type non "
                "autorisé, PDF/image uniquement, 650 Ko max) : " + ", ".join(rejected),
                "danger",
            )
        else:
            flash("Rapport envoyé à la commission.", "success")
        return redirect(url_for("ceam.mes_dossiers"))

    return render_template("ceam/depot.html", form=form)


@bp.route("/mes-dossiers")
@login_required
def mes_dossiers():
    search_query = request.args.get("q", "")
    rapports = Rapport.query_visible_to(current_user.id)
    rapports = Rapport.filter_by_search(rapports, search_query)
    return render_template("ceam/mes_dossiers.html", rapports=rapports, search_query=search_query)


@bp.route("/suivi")
@login_required
@requires_role(User.ROLE_MEMBRE_CEAM)
def suivi():
    status_filter = request.args.get("status", type=int)
    search_query = request.args.get("q", "")
    limit = request.args.get("limit", type=int)
    if limit not in (10, 25, 50, 100):
        limit = 10
    page = request.args.get("page", type=int) or 1

    rapports = Rapport.query_open(status_filter=status_filter)
    rapports = Rapport.filter_by_search(rapports, search_query)
    total_count = len(rapports)
    total_pages = max(1, -(-total_count // limit))  # arrondi supérieur
    page = max(1, min(page, total_pages))
    start = (page - 1) * limit
    rapports = rapports[start:start + limit]

    return render_template(
        "ceam/suivi.html",
        rapports=rapports,
        status_labels=Rapport.STATUS_LABELS,
        status_filter=status_filter,
        search_query=search_query,
        limit=limit,
        total_count=total_count,
        page=page,
        total_pages=total_pages,
    )


@bp.route("/archives")
@login_required
@requires_role(User.ROLE_MEMBRE_CEAM)
def archives():
    search_query = request.args.get("q", "")
    limit = request.args.get("limit", type=int)
    if limit not in (10, 25, 50, 100):
        limit = 10
    page = request.args.get("page", type=int) or 1

    rapports = Rapport.query_archived()
    rapports = Rapport.filter_by_search(rapports, search_query)
    total_count = len(rapports)
    total_pages = max(1, -(-total_count // limit))  # arrondi supérieur
    page = max(1, min(page, total_pages))
    start = (page - 1) * limit
    rapports = rapports[start:start + limit]

    return render_template(
        "ceam/archives.html",
        rapports=rapports,
        search_query=search_query,
        limit=limit,
        total_count=total_count,
        page=page,
        total_pages=total_pages,
    )


@bp.route("/dossier/<int:rapport_id>", methods=["GET", "POST"])
@login_required
def detail(rapport_id):
    rapport = Rapport.get(rapport_id)
    if rapport is None:
        abort(404)

    is_owner = rapport.owner_id == current_user.id
    is_tiers = current_user.id in rapport.tiers_ids
    is_ceam_member = current_user.role >= User.ROLE_MEMBRE_CEAM
    if not is_owner and not is_tiers and not is_ceam_member:
        abort(403)
    # Un dossier archivé n'est plus visible par le déclarant (ni un tiers),
    # même par lien direct (seule la commission continue d'y avoir accès,
    # via Archives).
    if rapport.archived and not is_ceam_member:
        abort(403)

    # Consulter son dossier marque automatiquement comme lues les
    # notifications qui s'y rapportent — mais seulement pour un vrai
    # déclarant ou tiers (pas membre CEAM). Un membre CEAM qui possède aussi
    # ce dossier (cas de test, ou personnel à double casquette) est
    # présumé y venir pour son travail de commission, pas pour lire ses
    # propres notifs : sans cette exception, changer soi-même le statut
    # de son propre dossier marquerait instantanément la notification
    # comme lue via la redirection qui suit, avant même de l'avoir vue.
    if (is_owner or is_tiers) and not is_ceam_member:
        Notification.mark_read_for_rapport(current_user.id, rapport_id)

    # Les messages de l'espace d'échanges, en revanche, sont marqués lus
    # pour QUICONQUE consulte le dossier (déclarant, tiers, ou membre
    # CEAM) : tout le monde a besoin de son propre suivi lu/non-lu sur la
    # conversation, contrairement aux notifications ci-dessus.
    # Le compteur de messages non lus est calculé AVANT de les marquer
    # comme lus juste après, pour que le badge de l'onglet Échanges
    # reflète bien "combien de nouveaux messages depuis ta dernière
    # visite" au moment où la page se charge.
    unread_messages_count = rapport.unread_messages_count(current_user.id)
    rapport.mark_messages_read(current_user.id)

    reponse_form = None
    message_form = MessageForm()
    note_form = None
    suspension_form = None
    cloture_form = None
    tiers_users = [u for u in (User.get(uid) for uid in rapport.tiers_ids) if u is not None]
    owner_user = User.get(rapport.owner_id)
    available_users = None
    if is_ceam_member:
        excluded_ids = {rapport.owner_id, *rapport.tiers_ids}
        available_users = [u for u in User.list_all() if u.id not in excluded_ids]

    action = request.form.get("action")

    if action == "toggle_lock" and is_ceam_member:
        rapport.set_messages_locked(not rapport.messages_locked)
        AuditLog.record(
            action=AuditLog.ACTION_MESSAGES_LOCK,
            actor_name=current_user.name,
            actor_id=current_user.id,
            details=(
                f"{current_user.name} a "
                f"{'désactivé' if rapport.messages_locked else 'réactivé'} "
                f"l'envoi de messages du déclarant sur le dossier {rapport.reference}"
            ),
        )
        flash(
            "Envoi de messages désactivé pour le déclarant." if rapport.messages_locked
            else "Envoi de messages réactivé pour le déclarant.",
            "success",
        )
        return redirect(url_for("ceam.detail", rapport_id=rapport.id, _anchor="echanges"))

    if action == "message" and rapport.messages_locked and not is_ceam_member:
        flash("La commission a désactivé l'envoi de messages sur ce dossier.", "danger")
        return redirect(url_for("ceam.detail", rapport_id=rapport.id, _anchor="echanges"))

    if action == "message" and message_form.validate_on_submit():
        attachments = []
        rejected = []
        for uploaded in request.files.getlist("attachments"):
            if not uploaded or not uploaded.filename:
                continue
            try:
                meta = upload_reponse_attachment(rapport.id, uploaded)
            except Exception:  # noqa: BLE001 - un souci Storage ne doit pas faire planter l'envoi
                meta = None
            if meta:
                attachments.append(meta)
            else:
                rejected.append(uploaded.filename)

        rapport.add_reponse(
            type_="Message",
            content=message_form.content.data,
            author_name=current_user.name,
            author_rank=current_user.role_label,
            author_id=current_user.id,
            author_is_ceam=is_ceam_member,
            attachments=attachments,
        )
        if rejected:
            flash(
                "Message envoyé, mais certains fichiers ont été ignorés (type non "
                "autorisé, PDF/image uniquement, 650 Ko max) : " + ", ".join(rejected),
                "danger",
            )
        else:
            flash("Message envoyé.", "success")
        return redirect(url_for("ceam.detail", rapport_id=rapport.id, _anchor="echanges"))

    note_form = None
    suspension_form = None
    cloture_form = None

    if is_ceam_member:
        note_form = NoteForm(note=rapport.note)
        suspension_form = SuspensionForm()
        cloture_form = ClotureForm(classement=rapport.classement)
        reponse_form = ReponseForm()
        can_close = current_user.role >= User.ROLE_PRESIDENT_CEAM

        if action == "note" and note_form.validate_on_submit():
            rapport.update_note(note_form.note.data)
            flash("Note interne mise à jour.", "success")
            return redirect(url_for("ceam.detail", rapport_id=rapport.id, _anchor="instruction"))

        if action == "lancer_examen":
            rapport.lancer_examen(current_user.name, current_user.role_label)
            flash("Examen préliminaire lancé.", "success")
            return redirect(url_for("ceam.detail", rapport_id=rapport.id, _anchor="instruction"))

        if action == "instruire":
            rapport.instruire(current_user.name, current_user.role_label)
            flash("Le dossier est maintenant en cours d'instruction.", "success")
            return redirect(url_for("ceam.detail", rapport_id=rapport.id, _anchor="instruction"))

        if action == "non_recevable":
            rapport.marquer_non_recevable(current_user.name, current_user.role_label)
            flash("Dossier marqué non recevable. Un classement a été pré-proposé.", "success")
            return redirect(url_for("ceam.detail", rapport_id=rapport.id, _anchor="instruction"))

        if action == "suspendre" and suspension_form.validate_on_submit():
            rapport.suspendre(current_user.name, current_user.role_label, suspension_form.motif.data)
            flash("Traitement suspendu.", "success")
            return redirect(url_for("ceam.detail", rapport_id=rapport.id, _anchor="instruction"))

        if action == "reprendre_instruction":
            rapport.reprendre_instruction(current_user.name, current_user.role_label)
            flash("Instruction reprise.", "success")
            return redirect(url_for("ceam.detail", rapport_id=rapport.id, _anchor="instruction"))

        if action == "marquer_decision_rendue":
            rapport.marquer_decision_rendue(current_user.name, current_user.role_label)
            flash("Décision marquée comme rendue. Sélectionne un classement pour clôturer.", "success")
            return redirect(url_for("ceam.detail", rapport_id=rapport.id, _anchor="instruction"))

        if action == "cloturer" and cloture_form.validate_on_submit():
            if not can_close:
                flash("Seul le président CEAM peut clôturer un dossier.", "danger")
            else:
                rapport.cloturer(current_user.name, current_user.role_label, cloture_form.classement.data)
                flash("Dossier clôturé. Les échanges sont désormais verrouillés.", "success")
            return redirect(url_for("ceam.detail", rapport_id=rapport.id, _anchor="instruction"))

        if action == "reponse" and reponse_form.validate_on_submit():
            attachments = []
            rejected = []
            for uploaded in request.files.getlist("attachments"):
                if not uploaded or not uploaded.filename:
                    continue
                try:
                    meta = upload_reponse_attachment(rapport.id, uploaded)
                except Exception:  # noqa: BLE001 - un souci Storage ne doit pas faire planter l'envoi
                    meta = None
                if meta:
                    attachments.append(meta)
                else:
                    rejected.append(uploaded.filename)

            rapport.add_reponse(
                type_=reponse_form.type.data,
                content=reponse_form.content.data,
                author_name=current_user.name,
                author_rank=current_user.role_label,
                author_id=current_user.id,
                author_is_ceam=True,
                attachments=attachments,
            )
            if rejected:
                flash(
                    "Réponse envoyée, mais certains fichiers ont été ignorés (type non "
                    "autorisé, PDF/image uniquement, 10 Mo max) : " + ", ".join(rejected),
                    "danger",
                )
            else:
                flash("Réponse envoyée et ajoutée à l'historique du dossier.", "success")
            return redirect(url_for("ceam.detail", rapport_id=rapport.id))

    branch_statuses = {Rapport.STATUS_TRAITEMENT_SUSPENDU, Rapport.STATUS_NON_RECEVABLE}
    visited_status_values = {h["status_value"] for h in rapport.status_history_affichage}
    # "Non recevable" est lui-même une décision finale : afficher "Décision
    # rendue" (Clôturé) comme prochaine étape n'aurait pas de sens tant
    # qu'elle n'a pas réellement été atteinte.
    hide_cloture = (
        rapport.status == Rapport.STATUS_NON_RECEVABLE
        and Rapport.STATUS_CLOTURE not in visited_status_values
    )
    status_steps = [
        (value, label) for value, label in Rapport.STATUS_LABELS.items()
        if value not in branch_statuses or value == rapport.status or value in visited_status_values
        if not (value == Rapport.STATUS_CLOTURE and hide_cloture)
    ]

    # Thème de couleur unique pour toute la barre, selon le statut ACTUEL
    # du dossier (pas historique par étape) : doré par défaut, bleu à la
    # réception, rouge en cas de suspension/non-recevabilité, vert une
    # fois clôturé.
    if rapport.status == Rapport.STATUS_NOUVEAU:
        stepper_theme = "blue"
    elif rapport.status in branch_statuses:
        stepper_theme = "red"
    elif rapport.status == Rapport.STATUS_DECISION_RENDUE:
        stepper_theme = "blue"
    elif rapport.status == Rapport.STATUS_CLOTURE:
        stepper_theme = "green"
    else:
        stepper_theme = "gold"

    return render_template(
        "ceam/detail.html",
        rapport=rapport,
        note_form=note_form,
        suspension_form=suspension_form,
        cloture_form=cloture_form,
        reponse_form=reponse_form,
        message_form=message_form,
        unread_messages_count=unread_messages_count,
        is_ceam_member=is_ceam_member,
        is_owner=is_owner,
        is_tiers=is_tiers,
        tiers_users=tiers_users,
        owner_user=owner_user,
        available_users=available_users,
        status_steps=status_steps,
        branch_statuses=branch_statuses,
        stepper_theme=stepper_theme,
        status_nouveau=Rapport.STATUS_NOUVEAU,
        status_cloture=Rapport.STATUS_CLOTURE,
        status_decision_rendue=Rapport.STATUS_DECISION_RENDUE,
        status_en_examen=Rapport.STATUS_EN_EXAMEN,
        status_en_instruction=Rapport.STATUS_EN_INSTRUCTION,
        status_suspendu=Rapport.STATUS_TRAITEMENT_SUSPENDU,
        status_non_recevable=Rapport.STATUS_NON_RECEVABLE,
        can_close=current_user.role >= User.ROLE_PRESIDENT_CEAM,
    )


@bp.route("/dossier/<int:rapport_id>/archiver", methods=["POST"])
@login_required
@requires_role(User.ROLE_PRESIDENT_CEAM)
def archiver(rapport_id):
    rapport = Rapport.get(rapport_id)
    if rapport is None:
        abort(404)
    rapport.archive()
    AuditLog.record(
        action=AuditLog.ACTION_RAPPORT_ARCHIVE,
        actor_name=current_user.name,
        actor_id=current_user.id,
        details=f"{current_user.name} a archivé le dossier {rapport.reference}",
    )
    flash(f"Dossier {rapport.reference} archivé. Il n'est plus visible par le déclarant.", "success")
    return redirect(request.referrer or url_for("ceam.suivi"))


@bp.route("/dossier/<int:rapport_id>/supprimer", methods=["POST"])
@login_required
@requires_role(User.ROLE_ADMIN)
def supprimer(rapport_id):
    rapport = Rapport.get(rapport_id)
    if rapport is None:
        abort(404)
    reference = rapport.reference
    Rapport.delete(rapport_id)
    AuditLog.record(
        action=AuditLog.ACTION_RAPPORT_DELETE,
        actor_name=current_user.name,
        actor_id=current_user.id,
        details=f"{current_user.name} a supprimé définitivement le dossier {reference}",
    )
    flash(f"Dossier {reference} supprimé définitivement.", "success")
    return redirect(url_for("ceam.archives"))


@bp.route("/statistiques")
@login_required
@requires_role(User.ROLE_MEMBRE_CEAM)
def statistiques():
    stats = Rapport.compute_statistiques()
    return render_template(
        "ceam/statistiques.html",
        stats=stats,
        status_labels=Rapport.STATUS_LABELS,
    )


@bp.route("/reglement", methods=["GET", "POST"])
@login_required
def reglement():
    """Règlement CEAM : visible par tout le monde (déclarants inclus),
    modifiable uniquement par les administrateurs."""
    doc = Reglement.get()
    is_admin = current_user.role >= User.ROLE_ADMIN

    form = None
    if is_admin:
        form = ReglementForm(content=doc.content)
        if form.validate_on_submit():
            doc.save(form.content.data, current_user.name)
            AuditLog.record(
                action=AuditLog.ACTION_REGLEMENT_UPDATE,
                actor_name=current_user.name,
                actor_id=current_user.id,
                details=f"{current_user.name} a modifié le règlement de la CEAM",
            )
            flash("Règlement mis à jour.", "success")
            return redirect(url_for("ceam.reglement"))

    return render_template("ceam/reglement.html", reglement=doc, form=form, is_admin=is_admin)


@bp.route("/dossier/<int:rapport_id>/piece-jointe/<attachment_id>")
@login_required
def piece_jointe(rapport_id, attachment_id):
    """Sert une pièce jointe en appliquant les mêmes règles d'accès que la
    page de détail (stockée dans Firestore, jamais exposée directement)."""
    rapport = Rapport.get(rapport_id)
    if rapport is None:
        abort(404)

    is_owner = rapport.owner_id == current_user.id
    is_ceam_member = current_user.role >= User.ROLE_MEMBRE_CEAM
    if not is_owner and not is_ceam_member:
        abort(403)
    if rapport.archived and not is_ceam_member:
        abort(403)

    data, content_type = fetch_attachment(attachment_id, rapport_id)
    if data is None:
        abort(404)

    display_name = secure_filename(request.args.get("name", "")) or "fichier"
    force_download = request.args.get("download") == "1"
    disposition = "attachment" if force_download else "inline"
    return Response(
        data,
        mimetype=content_type or "application/octet-stream",
        headers={"Content-Disposition": f'{disposition}; filename="{display_name}"'},
    )


@bp.route("/notifications")
@login_required
def notifications():
    limit = request.args.get("limit", type=int)
    if limit not in (10, 25, 50, 100):
        limit = 10
    page = request.args.get("page", type=int) or 1

    items = Notification.list_for_user(current_user.id)
    unread_count = sum(1 for n in items if not n.read)
    total_count = len(items)
    total_pages = max(1, -(-total_count // limit))  # arrondi supérieur
    page = max(1, min(page, total_pages))
    start = (page - 1) * limit
    items = items[start:start + limit]

    return render_template(
        "ceam/notifications.html",
        notifications=items,
        unread_count=unread_count,
        limit=limit,
        total_count=total_count,
        page=page,
        total_pages=total_pages,
    )


@bp.route("/notifications/<int:notification_id>/lire", methods=["POST"])
@login_required
def marquer_notification_lue(notification_id):
    Notification.mark_read(notification_id, current_user.id)
    return redirect(request.referrer or url_for("ceam.notifications"))


@bp.route("/notifications/tout-lire", methods=["POST"])
@login_required
def marquer_toutes_notifications_lues():
    Notification.mark_all_read(current_user.id)
    flash("Toutes les notifications ont été marquées comme lues.", "success")
    return redirect(url_for("ceam.notifications"))


@bp.route("/accueil")
@login_required
def accueil():
    """Page d'accueil pédagogique : présentation de la CEAM, son rôle, ses
    missions, et le fonctionnement général du traitement des dossiers."""
    return render_template("ceam/accueil.html")


@bp.route("/dossier/<int:rapport_id>/export-pdf")
@login_required
def export_pdf(rapport_id):
    """Export PDF d'un dossier (infos, historique des statuts, réponses),
    avec les mêmes règles d'accès que la page de détail."""
    rapport = Rapport.get(rapport_id)
    if rapport is None:
        abort(404)

    is_owner = rapport.owner_id == current_user.id
    is_tiers = current_user.id in rapport.tiers_ids
    is_ceam_member = current_user.role >= User.ROLE_MEMBRE_CEAM
    if not is_owner and not is_tiers and not is_ceam_member:
        abort(403)
    if rapport.archived and not is_ceam_member:
        abort(403)

    pdf_bytes = generate_dossier_pdf(rapport)
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{rapport.reference}.pdf"'},
    )


@bp.route("/dossier/<int:rapport_id>/tiers/ajouter", methods=["POST"])
@login_required
@requires_role(User.ROLE_MEMBRE_CEAM)
def ajouter_tiers(rapport_id):
    rapport = Rapport.get(rapport_id)
    if rapport is None:
        abort(404)

    user_id = request.form.get("user_id", type=int)
    user = User.get(user_id) if user_id else None

    if user is None:
        flash("Utilisateur introuvable.", "danger")
    elif not rapport.add_tiers(user_id):
        flash(f"{user.name} a déjà accès à ce dossier.", "danger")
    else:
        AuditLog.record(
            action=AuditLog.ACTION_TIERS_ADD,
            actor_name=current_user.name,
            actor_id=current_user.id,
            details=f"{current_user.name} a donné accès au dossier {rapport.reference} à {user.name}",
        )
        flash(f"{user.name} a été ajouté au dossier et peut désormais le consulter.", "success")

    return redirect(url_for("ceam.detail", rapport_id=rapport_id))


@bp.route("/dossier/<int:rapport_id>/tiers/<int:user_id>/retirer", methods=["POST"])
@login_required
@requires_role(User.ROLE_MEMBRE_CEAM)
def retirer_tiers(rapport_id, user_id):
    rapport = Rapport.get(rapport_id)
    if rapport is None:
        abort(404)

    user = User.get(user_id)
    if rapport.remove_tiers(user_id):
        AuditLog.record(
            action=AuditLog.ACTION_TIERS_REMOVE,
            actor_name=current_user.name,
            actor_id=current_user.id,
            details=(
                f"{current_user.name} a retiré l'accès au dossier {rapport.reference} "
                f"à {user.name if user else user_id}"
            ),
        )
        flash("Accès retiré.", "success")

    return redirect(url_for("ceam.detail", rapport_id=rapport_id))