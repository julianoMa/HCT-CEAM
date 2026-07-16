from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

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
        user.update_role(nouveau_role)
        flash(f"Rôle de {user.name} mis à jour : {user.role_label}.", "success")

    return redirect(url_for("admin.utilisateurs"))
