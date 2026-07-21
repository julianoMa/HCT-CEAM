import secrets
from datetime import datetime, timedelta

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, logout_user

from app.models.audit_log import AuditLog
from app.models.user import User
from app.permissions import requires_role

bp = Blueprint("admin", __name__, url_prefix="/admin")

RESET_CONFIRMATION_PHRASE = "RÉINITIALISER"
# Sans 0/O, 1/I/L : trop facilement confondus à l'oral ou sur un écran de
# téléphone, quand on relit le code reçu par MP Discord pour le retaper.
RESET_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


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


@bp.route("/systeme")
@login_required
@requires_role(User.ROLE_PRESIDENT_CEAM)
def systeme():
    from app.models import maintenance as maintenance_model
    return render_template("admin/systeme.html", maintenance_active=maintenance_model.is_active())


@bp.route("/systeme/maintenance", methods=["POST"])
@login_required
@requires_role(User.ROLE_PRESIDENT_CEAM)
def toggle_maintenance():
    from app.models import maintenance as maintenance_model

    activate = request.form.get("activate") == "1"
    actor_name = f"{current_user.name} ({current_user.role_label})"
    if activate:
        maintenance_model.activate(actor_name)
        AuditLog.record(
            action=AuditLog.ACTION_MAINTENANCE_TOGGLE,
            actor_name=actor_name,
            details=f"{actor_name} a activé le mode maintenance.",
        )
        flash(
            "Mode maintenance activé : seuls le président CEAM et l'administrateur ont "
            "encore accès au site.",
            "success",
        )
    else:
        maintenance_model.deactivate(actor_name)
        AuditLog.record(
            action=AuditLog.ACTION_MAINTENANCE_TOGGLE,
            actor_name=actor_name,
            details=f"{actor_name} a désactivé le mode maintenance.",
        )
        flash("Mode maintenance désactivé : le site est de nouveau accessible à tous.", "success")
    return redirect(url_for("admin.systeme"))


@bp.route("/reset-database/envoyer-code", methods=["POST"])
@login_required
@requires_role(User.ROLE_PRESIDENT_CEAM)
def reset_database_send_code():
    """Première étape après la phrase de confirmation : génère un code à
    5 caractères, l'envoie par MP Discord à la personne qui vient de
    demander la réinitialisation, et le garde en session (jamais côté
    client) le temps qu'elle le retape — un 3e garde-fou, hors du
    navigateur, avant une action irréversible."""
    confirmation_phrase = request.form.get("confirmation_phrase", "").strip()
    if confirmation_phrase != RESET_CONFIRMATION_PHRASE:
        flash(
            "Phrase de confirmation incorrecte : la base de données n'a pas été modifiée.",
            "danger",
        )
        return redirect(url_for("admin.logs"))

    from app.notifications import send_discord_dm  # import différé : évite un cycle d'import

    code = "".join(secrets.choice(RESET_CODE_ALPHABET) for _ in range(5))
    session["reset_code"] = code
    session["reset_code_expires_at"] = (datetime.utcnow() + timedelta(minutes=10)).isoformat()

    sent = send_discord_dm(
        current_user.discord_id,
        content=(
            f"🔐 Code de confirmation pour la réinitialisation de la base de données : **{code}**\n"
            "Valable 10 minutes. Si tu n'es pas à l'origine de cette demande, ignore ce message "
            "et ne partage ce code avec personne."
        ),
    )
    if not sent:
        session.pop("reset_code", None)
        session.pop("reset_code_expires_at", None)
        flash(
            "Impossible d'envoyer le code de confirmation par MP Discord (vérifie que tes MP "
            "sont ouverts). La base de données n'a pas été modifiée.",
            "danger",
        )
        return redirect(url_for("admin.logs"))

    return redirect(url_for("admin.logs", show_reset_code_modal=1))


@bp.route("/reset-database/confirmer", methods=["POST"])
@login_required
@requires_role(User.ROLE_PRESIDENT_CEAM)
def reset_database_confirm():
    """Dernière étape : vérifie le code reçu par MP Discord (généré et
    gardé en session par reset_database_send_code) avant d'effectuer la
    réinitialisation elle-même."""
    submitted_code = request.form.get("reset_code", "").strip().upper()
    expected_code = session.get("reset_code")
    expires_at = session.get("reset_code_expires_at")

    session.pop("reset_code", None)
    session.pop("reset_code_expires_at", None)

    if not expected_code or not expires_at or datetime.utcnow().isoformat() > expires_at:
        flash(
            "Code de confirmation expiré ou manquant : recommence depuis le début. "
            "La base de données n'a pas été modifiée.",
            "danger",
        )
        return redirect(url_for("admin.logs"))

    if submitted_code != expected_code:
        flash(
            "Code de confirmation incorrect : la base de données n'a pas été modifiée.",
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