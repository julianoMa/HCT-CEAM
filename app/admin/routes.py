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
    search_query = request.args.get("q", "")
    action_filter = request.args.get("action", "")
    limit = request.args.get("limit", type=int)
    if limit not in (10, 25, 50, 100):
        limit = 25

    entries = AuditLog.list_recent()
    entries = AuditLog.filter_by_search(entries, search_query)
    if action_filter:
        entries = [e for e in entries if e.action == action_filter]

    total_count = len(entries)
    entries = entries[:limit]

    return render_template(
        "admin/logs.html",
        entries=entries,
        search_query=search_query,
        action_filter=action_filter,
        action_labels=AuditLog.ACTION_LABELS,
        limit=limit,
        total_count=total_count,
    )