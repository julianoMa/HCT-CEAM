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


def build_avatar_url(discord_user):
    """Construit l'URL de la photo de profil Discord du compte, ou une
    icône par défaut Discord si la personne n'en a pas défini."""
    user_id = discord_user["id"]
    avatar_hash = discord_user.get("avatar")

    if avatar_hash:
        ext = "gif" if avatar_hash.startswith("a_") else "png"
        return f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.{ext}?size=64"

    # Pas d'avatar personnalisé : icône par défaut Discord.
    try:
        discriminator = int(discord_user.get("discriminator") or "0")
    except ValueError:
        discriminator = 0

    if discriminator == 0:
        # Nouveau système de pseudo Discord (sans discriminator) :
        # l'index par défaut se calcule à partir de l'ID du compte.
        index = (int(user_id) >> 22) % 6
    else:
        index = discriminator % 5

    return f"https://cdn.discordapp.com/embed/avatars/{index}.png"