from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.ceam.forms import InstructionForm, RapportForm
from app.models.ceam import Rapport
from app.models.user import User
from app.permissions import requires_role

bp = Blueprint("ceam", __name__, url_prefix="/ceam")


@bp.route("/depot", methods=["GET", "POST"])
@login_required
def depot():
    form = RapportForm()
    if form.validate_on_submit():
        Rapport.create(
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
        flash("Rapport envoyé à la commission.", "success")
        return redirect(url_for("ceam.mes_dossiers"))

    return render_template("ceam/depot.html", form=form)


@bp.route("/mes-dossiers")
@login_required
def mes_dossiers():
    rapports = Rapport.query_by_owner(current_user.id)
    return render_template("ceam/mes_dossiers.html", rapports=rapports)


@bp.route("/suivi")
@login_required
@requires_role(User.ROLE_MEMBRE_CEAM)
def suivi():
    status_filter = request.args.get("status", type=int)
    rapports = Rapport.query_open(status_filter=status_filter)
    return render_template(
        "ceam/suivi.html",
        rapports=rapports,
        status_labels=Rapport.STATUS_LABELS,
        status_filter=status_filter,
    )


@bp.route("/archives")
@login_required
@requires_role(User.ROLE_MEMBRE_CEAM)
def archives():
    rapports = Rapport.query_archived()
    return render_template("ceam/archives.html", rapports=rapports)


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

    form = None
    if is_ceam_member:
        form = InstructionForm(status=rapport.status, note=rapport.note, conclusion=rapport.conclusion)
        form.status.choices = list(Rapport.STATUS_LABELS.items())

        if form.validate_on_submit():
            can_close = current_user.role >= User.ROLE_PRESIDENT_CEAM
            if form.status.data == Rapport.STATUS_CLOTURE and not can_close:
                flash("Seul le président CEAM peut clôturer un dossier.", "danger")
            else:
                rapport.update_instruction(form.status.data, form.note.data, form.conclusion.data)
                flash("Dossier mis à jour.", "success")
            return redirect(url_for("ceam.detail", rapport_id=rapport.id))

    return render_template("ceam/detail.html", rapport=rapport, form=form, is_ceam_member=is_ceam_member)


@bp.route("/statistiques")
@login_required
@requires_role(User.ROLE_MEMBRE_CEAM)
def statistiques():
    counts = {label: Rapport.count_by_status(value) for value, label in Rapport.STATUS_LABELS.items()}
    total = Rapport.count_all()
    return render_template("ceam/statistiques.html", counts=counts, total=total)
