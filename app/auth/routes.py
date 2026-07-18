import re
from urllib.parse import urlencode

import requests
from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import login_required, login_user, logout_user

from app.auth.discord import build_avatar_url, exchange_code_for_token, fetch_discord_user, fetch_guild_member
from app.discord_roles import detect_affectation, detect_grade
from app.models.user import User

bp = Blueprint("auth", __name__, url_prefix="/auth")

_DISCORD_SNOWFLAKE = re.compile(r"^\d{17,20}$")


def _access_denied(message, invite_url=None):
    """Affiche une erreur sans renvoyer vers /auth/login (évite la boucle OAuth)."""
    return render_template(
        "auth/access_denied.html", title="Accès refusé", message=message, invite_url=invite_url
    )


@bp.route("/login")
def login():
    """Page d'accueil / connexion : affiche un bouton, ne redirige plus
    automatiquement vers Discord (voir login_discord)."""
    if request.args.get("code"):
        # Sécurité : si jamais quelqu'un atterrit ici avec un `code` OAuth
        # (mauvais lien, ancien favori...), on le renvoie vers le vrai callback.
        return redirect(url_for("auth.callback", **request.args))
    return render_template("auth/login.html", title="Connexion")


@bp.route("/login/discord")
def login_discord():
    """Redirection effective vers l'écran d'autorisation Discord, déclenchée
    par le clic sur le bouton de la page de connexion."""
    params = {
        "client_id": current_app.config["DISCORD_CLIENT_ID"],
        "redirect_uri": current_app.config["DISCORD_REDIRECT_URI"],
        "response_type": "code",
        # guilds.members.read : nécessaire pour récupérer le pseudo utilisé
        # sur le serveur HCT (distinct du pseudo global du compte Discord).
        "scope": "identify guilds guilds.members.read",
    }
    return redirect(f"{current_app.config['DISCORD_AUTHORIZE_URL']}?{urlencode(params)}")


@bp.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return _access_denied("Connexion Discord annulée ou invalide.")

    try:
        access_token = exchange_code_for_token(code)
        discord_user = fetch_discord_user(access_token)
    except requests.HTTPError:
        return _access_denied(
            "Discord a refusé la connexion. Vérifie que DISCORD_REDIRECT_URI correspond "
            "exactement à l'URL enregistrée dans le portail développeur Discord "
            "(y compris localhost vs 127.0.0.1)."
        )

    guild_id = current_app.config.get("DISCORD_GUILD_ID")
    guild_nickname = None
    guild_role_ids = []

    if not guild_id:
        current_app.logger.warning(
            "DISCORD_GUILD_ID n'est pas défini : la vérification d'appartenance "
            "au serveur HCT est DÉSACTIVÉE, n'importe quel compte Discord peut "
            "se connecter. Définis DISCORD_GUILD_ID pour l'activer."
        )
    elif not _DISCORD_SNOWFLAKE.match(str(guild_id)):
        current_app.logger.warning(
            "DISCORD_GUILD_ID invalide (%r) : ce n'est pas un identifiant Discord "
            "valide (17 à 20 chiffres) — vérif serveur ignorée.", guild_id
        )
    else:
        try:
            member = fetch_guild_member(access_token, guild_id)
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 404:
                return _access_denied(
                    "Tu dois être membre du serveur Discord HCT pour accéder à la CEAM.",
                    invite_url="https://discord.gg/uxfcjrUKWc",
                )
            return _access_denied(
                "Impossible de vérifier ton appartenance au serveur Discord HCT. Réessaie plus tard."
            )
        guild_nickname = member.get("nick")
        guild_role_ids = member.get("roles", [])

    discord_id = int(discord_user["id"])
    # Priorité au pseudo serveur HCT ; à défaut (pas de pseudo défini sur le
    # serveur, ou vérif serveur ignorée en dev), on retombe sur le pseudo du
    # compte Discord.
    name = guild_nickname or discord_user.get("global_name") or discord_user["username"]
    avatar_url = build_avatar_url(discord_user)
    affectation = detect_affectation(guild_role_ids)
    rank = detect_grade(guild_role_ids)

    user = User.get_by_discord_id(discord_id)

    if user is None:
        user = User.create(
            discord_id=discord_id, name=name, role=User.ROLE_DECLARANT, avatar_url=avatar_url,
            affectation=affectation, rank=rank,
        )
    elif (
        user.name != name or user.avatar_url != avatar_url
        or user.affectation != affectation or user.rank != rank
    ):
        # Garde le pseudo, la photo, l'affectation et le grade à jour à
        # chaque connexion (ces deux derniers sont déduits des rôles
        # Discord actuels, voir app/discord_roles.py).
        user.update_profile(name, avatar_url, affectation, rank)

    login_user(user, remember=True)
    session.permanent = True
    flash(f"Connecté en tant que {user.name}.", "success")
    return redirect(url_for("ceam.mes_dossiers"))


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Déconnecté.", "success")
    return redirect(url_for("auth.login"))