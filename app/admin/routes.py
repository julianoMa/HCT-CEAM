from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.models.audit_log import AuditLog
from app.models.user import User
from app.permissions import requires_role

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/utilisateurs")
@login_required
@requires_role(User.ROLE_ADMIN)
def utilisateurs():
    users = User.list_all()
    return render_template("admin/utilisateurs.html", users=users, role_labels=User.ROLE_LABELS)


@bp.route("/utilisateurs/<int:user_id>/role", methods=["POST"])
@login_required
@requires_role(User.ROLE_ADMIN)
def changer_role(user_id):
    user = User.get(user_id)
    nouveau_role = request.form.get("role", type=int)

    if user is None:
        flash("Utilisateur introuvable.", "danger")
    elif nouveau_role not in User.ROLE_LABELS:
        flash("Rôle invalide.", "danger")
    else:
        ancien_label = user.role_label
        user.update_role(nouveau_role)
        AuditLog.record(
            action=AuditLog.ACTION_ROLE_CHANGE,
            actor_name=current_user.name,
            actor_id=current_user.id,
            details=(
                f"{current_user.name} a changé le rôle de {user.name} : "
                f"« {ancien_label} » → « {user.role_label} »"
            ),
        )
        flash(f"Rôle de {user.name} mis à jour : {user.role_label}.", "success")

    return redirect(url_for("admin.utilisateurs"))


@bp.route("/logs")
@login_required
@requires_role(User.ROLE_ADMIN)
def logs():
    entries = AuditLog.list_recent()
    return render_template("admin/logs.html", entries=entries)