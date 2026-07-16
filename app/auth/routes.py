import re
from urllib.parse import urlencode

import requests
from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import login_required, login_user, logout_user

from app.auth.discord import exchange_code_for_token, fetch_discord_user, is_member_of_guild
from app.models.user import User

bp = Blueprint("auth", __name__, url_prefix="/auth")

_DISCORD_SNOWFLAKE = re.compile(r"^\d{17,20}$")


def _access_denied(message):
    """Affiche une erreur sans renvoyer vers /auth/login (évite la boucle OAuth)."""
    return render_template("auth/access_denied.html", title="Accès refusé", message=message)


@bp.route("/login")
def login():
    params = {
        "client_id": current_app.config["DISCORD_CLIENT_ID"],
        "redirect_uri": current_app.config["DISCORD_REDIRECT_URI"],
        "response_type": "code",
        "scope": "identify guilds",
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
    if guild_id and _DISCORD_SNOWFLAKE.match(str(guild_id)):
        if not is_member_of_guild(access_token, guild_id):
            return _access_denied(
                "Tu dois être membre du serveur Discord HCT pour accéder à la CEAM."
            )
    elif guild_id and not _DISCORD_SNOWFLAKE.match(str(guild_id)):
        current_app.logger.warning(
            "DISCORD_GUILD_ID invalide (%r) : vérif serveur ignorée en dev.", guild_id
        )

    discord_id = int(discord_user["id"])
    user = User.get_by_discord_id(discord_id)

    if user is None:
        user = User.create(
            discord_id=discord_id,
            name=discord_user.get("global_name") or discord_user["username"],
            role=User.ROLE_DECLARANT,
        )

    login_user(user)
    flash(f"Connecté en tant que {user.name}.", "success")
    return redirect(url_for("ceam.mes_dossiers"))


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Déconnecté.", "success")
    return redirect(url_for("auth.login"))
