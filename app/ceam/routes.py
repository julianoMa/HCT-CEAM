from flask import Blueprint, Response, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app.ceam.forms import InstructionForm, RapportForm, ReglementForm, ReponseForm
from app.models.audit_log import AuditLog
from app.models.ceam import Rapport
from app.models.reglement import Reglement
from app.models.user import User
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
            witness=form.witness.data,
            description=form.description.data,
            proof=form.proof.data,
        )
        AuditLog.record(
            action=AuditLog.ACTION_RAPPORT_CREATE,
            actor_name=current_user.name,
            actor_id=current_user.id,
            details=f"{current_user.name} a déposé le rapport {rapport.reference}",
        )
        flash("Rapport envoyé à la commission.", "success")
        return redirect(url_for("ceam.mes_dossiers"))

    return render_template("ceam/depot.html", form=form)


@bp.route("/mes-dossiers")
@login_required
def mes_dossiers():
    search_query = request.args.get("q", "")
    rapports = Rapport.query_by_owner(current_user.id)
    rapports = Rapport.filter_by_search(rapports, search_query)
    return render_template("ceam/mes_dossiers.html", rapports=rapports, search_query=search_query)


@bp.route("/suivi")
@login_required
@requires_role(User.ROLE_MEMBRE_CEAM)
def suivi():
    status_filter = request.args.get("status", type=int)
    search_query = request.args.get("q", "")
    rapports = Rapport.query_open(status_filter=status_filter)
    rapports = Rapport.filter_by_search(rapports, search_query)
    return render_template(
        "ceam/suivi.html",
        rapports=rapports,
        status_labels=Rapport.STATUS_LABELS,
        status_filter=status_filter,
        search_query=search_query,
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
    is_ceam_member = current_user.role >= User.ROLE_MEMBRE_CEAM
    if not is_owner and not is_ceam_member:
        abort(403)
    # Un dossier archivé n'est plus visible par le déclarant, même par lien
    # direct (seule la commission continue d'y avoir accès, via Archives).
    if rapport.archived and not is_ceam_member:
        abort(403)

    instruction_form = None
    reponse_form = None

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