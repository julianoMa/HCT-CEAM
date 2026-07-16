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
    """Récupère le profil Discord de l'utilisateur connecté."""
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(
        f"{current_app.config['DISCORD_API_BASE_URL']}/users/@me",
        headers=headers,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def is_member_of_guild(access_token, guild_id):
    """Vérifie que l'utilisateur est toujours membre du serveur Discord HCT."""
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(
        f"{current_app.config['DISCORD_API_BASE_URL']}/users/@me/guilds",
        headers=headers,
        timeout=10,
    )
    response.raise_for_status()
    guild_ids = {g["id"] for g in response.json()}
    return str(guild_id) in guild_ids
