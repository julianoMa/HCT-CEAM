from flask import Blueprint, Response, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app.ceam.forms import InstructionForm, RapportForm, ReglementForm, ReponseForm
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
        limit = 25

    rapports = Rapport.query_open(status_filter=status_filter)
    rapports = Rapport.filter_by_search(rapports, search_query)
    total_count = len(rapports)
    rapports = rapports[:limit]

    return render_template(
        "ceam/suivi.html",
        rapports=rapports,
        status_labels=Rapport.STATUS_LABELS,
        status_filter=status_filter,
        search_query=search_query,
        limit=limit,
        total_count=total_count,
    )


@bp.route("/archives")
@login_required
@requires_role(User.ROLE_MEMBRE_CEAM)
def archives():
    search_query = request.args.get("q", "")
    rapports = Rapport.query_archived()
    rapports = Rapport.filter_by_search(rapports, search_query)
    return render_template("ceam/archives.html", rapports=rapports, search_query=search_query)


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

    instruction_form = None
    reponse_form = None
    tiers_users = [u for u in (User.get(uid) for uid in rapport.tiers_ids) if u is not None]
    available_users = None
    if is_ceam_member:
        excluded_ids = {rapport.owner_id, *rapport.tiers_ids}
        available_users = [u for u in User.list_all() if u.id not in excluded_ids]

    if is_ceam_member:
        instruction_form = InstructionForm(status=rapport.status, note=rapport.note)
        instruction_form.status.choices = list(Rapport.STATUS_LABELS.items())
        reponse_form = ReponseForm()

        action = request.form.get("action")

        if action == "instruction" and instruction_form.validate_on_submit():
            can_close = current_user.role >= User.ROLE_PRESIDENT_CEAM
            if instruction_form.status.data == Rapport.STATUS_CLOTURE and not can_close:
                flash("Seul le président CEAM peut clôturer un dossier.", "danger")
            else:
                rapport.update_instruction(
                    instruction_form.status.data, instruction_form.note.data,
                    current_user.name, current_user.role_label,
                )
                flash("Suivi interne mis à jour.", "success")
            return redirect(url_for("ceam.detail", rapport_id=rapport.id))

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

    return render_template(
        "ceam/detail.html",
        rapport=rapport,
        instruction_form=instruction_form,
        reponse_form=reponse_form,
        is_ceam_member=is_ceam_member,
        tiers_users=tiers_users,
        available_users=available_users,
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
        seuil_relance=Rapport.STALE_NOUVEAU_JOURS,
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
    return Response(
        data,
        mimetype=content_type or "application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="{display_name}"'},
    )


@bp.route("/notifications")
@login_required
def notifications():
    limit = request.args.get("limit", type=int)
    if limit not in (10, 25, 50, 100):
        limit = 25

    items = Notification.list_for_user(current_user.id)
    unread_count = sum(1 for n in items if not n.read)
    total_count = len(items)
    items = items[:limit]

    return render_template(
        "ceam/notifications.html",
        notifications=items,
        unread_count=unread_count,
        limit=limit,
        total_count=total_count,
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