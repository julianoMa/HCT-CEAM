import requests
from flask import current_app


def exchange_code_for_token(code):
    """Échange le code temporaire OAuth2 contre un access_token Discord."""
    data = {
        "client_id": current_app.config["DISCORD_CLIENT_ID"],
        "client_secret": current_app.config["DISCORD_CLIENT_SECRET"],
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": current_app.config["DISCORD_REDIRECT_URI"],
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post(
        current_app.config["DISCORD_TOKEN_URL"], data=data, headers=headers, timeout=10
    )
    response.raise_for_status()
    return response.json()["access_token"]


def fetch_discord_user(access_token):
    """Récupère le profil Discord (compte) de l'utilisateur connecté."""
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(
        f"{current_app.config['DISCORD_API_BASE_URL']}/users/@me",
        headers=headers,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def fetch_guild_member(access_token, guild_id):
    """Récupère le profil de membre sur le serveur HCT (contient le pseudo
    serveur `nick`, distinct du pseudo global du compte Discord).

    Lève requests.HTTPError avec un status_code 404 si la personne n'est
    pas membre du serveur.
    Nécessite le scope OAuth2 `guilds.members.read`.
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(
        f"{current_app.config['DISCORD_API_BASE_URL']}/users/@me/guilds/{guild_id}/member",
        headers=headers,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()