from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, logout_user

from app.models.audit_log import AuditLog
from app.models.user import User
from app.permissions import requires_role

bp = Blueprint("admin", __name__, url_prefix="/admin")

RESET_CONFIRMATION_PHRASE = "RÉINITIALISER"


@bp.route("/utilisateurs")
@login_required
@requires_role(User.ROLE_PRESIDENT_CEAM)
def utilisateurs():
    search_query = request.args.get("q", "")
    limit = request.args.get("limit", type=int)
    if limit not in (10, 25, 50, 100):
        limit = 10
    page = request.args.get("page", type=int) or 1

    users = User.list_all()
    users = User.filter_by_search(users, search_query)
    total_count = len(users)
    total_pages = max(1, -(-total_count // limit))  # arrondi supérieur
    page = max(1, min(page, total_pages))
    start = (page - 1) * limit
    users = users[start:start + limit]

    return render_template(
        "admin/utilisateurs.html",
        users=users,
        role_labels=User.ROLE_LABELS,
        search_query=search_query,
        limit=limit,
        total_count=total_count,
        page=page,
        total_pages=total_pages,
    )


@bp.route("/utilisateurs/<int:user_id>/role", methods=["POST"])
@login_required
@requires_role(User.ROLE_PRESIDENT_CEAM)
def changer_role(user_id):
    user = User.get(user_id)
    nouveau_role = request.form.get("role", type=int)

    if user is None:
        flash("Utilisateur introuvable.", "danger")
    elif user.id == current_user.id:
        flash("Tu ne peux pas modifier ton propre rôle.", "danger")
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
@requires_role(User.ROLE_PRESIDENT_CEAM)
def logs():
    search_query = request.args.get("q", "")
    action_filter = request.args.get("action", "")
    limit = request.args.get("limit", type=int)
    if limit not in (10, 25, 50, 100):
        limit = 10
    page = request.args.get("page", type=int) or 1

    entries = AuditLog.list_recent()
    entries = AuditLog.filter_by_search(entries, search_query)
    if action_filter:
        entries = [e for e in entries if e.action == action_filter]

    total_count = len(entries)
    total_pages = max(1, -(-total_count // limit))  # arrondi supérieur
    page = max(1, min(page, total_pages))
    start = (page - 1) * limit
    entries = entries[start:start + limit]

    return render_template(
        "admin/logs.html",
        entries=entries,
        search_query=search_query,
        action_filter=action_filter,
        action_labels=AuditLog.ACTION_LABELS,
        limit=limit,
        total_count=total_count,
        page=page,
        total_pages=total_pages,
    )


@bp.route("/reset-database", methods=["POST"])
@login_required
@requires_role(User.ROLE_PRESIDENT_CEAM)
def reset_database_confirm():
    """Réinitialisation complète de la base (voir app/database_reset.py).
    Double confirmation déjà faite côté interface (deux modals) ; ici, on
    exige en plus une phrase de confirmation exacte comme dernier
    garde-fou avant une action irréversible."""
    confirmation_phrase = request.form.get("confirmation_phrase", "").strip()
    if confirmation_phrase != RESET_CONFIRMATION_PHRASE:
        flash(
            "Phrase de confirmation incorrecte : la base de données n'a pas été modifiée.",
            "danger",
        )
        return redirect(url_for("admin.logs"))

    from app.database_reset import reset_database  # import différé : évite un cycle d'import
    summary = reset_database()

    # Le compte de la personne qui vient d'effectuer l'action a lui-même
    # été supprimé (la collection utilisateurs est entièrement vidée) :
    # sa session ne correspond plus à rien, il faut la terminer proprement.
    logout_user()

    details = ", ".join(f"{count} {name}" for name, count in summary.items())
    flash(
        f"Base de données réinitialisée ({details}). Tous les comptes ont été "
        "supprimés — reconnecte-toi via Discord.",
        "success",
    )
    return redirect(url_for("auth.login"))


@bp.route("/utilisateurs/<int:user_id>/deconnecter", methods=["POST"])
@login_required
@requires_role(User.ROLE_PRESIDENT_CEAM)
def deconnecter_utilisateur(user_id):
    """Force la déconnexion d'un utilisateur : sa session actuelle devient
    invalide dès sa prochaine requête (voir User.force_logout)."""
    user = User.get(user_id)
    if user is None:
        flash("Utilisateur introuvable.", "danger")
        return redirect(url_for("admin.utilisateurs"))

    if user.id == current_user.id:
        flash("Tu ne peux pas te déconnecter toi-même depuis cette page.", "danger")
        return redirect(url_for("admin.utilisateurs"))

    user.force_logout()
    AuditLog.record(
        action=AuditLog.ACTION_FORCE_LOGOUT,
        actor_name=current_user.name,
        actor_id=current_user.id,
        details=f"{current_user.name} a déconnecté {user.name} à distance",
    )
    flash(f"{user.name} a été déconnecté(e). Sa session actuelle est invalidée.", "success")
    return redirect(url_for("admin.utilisateurs"))