"""
Envoi de notifications par message privé (MP) Discord, via le bot de
l'application (nécessite DISCORD_BOT_TOKEN, voir app/config.py).

Toute notification échoue silencieusement (log uniquement) plutôt que de
faire planter l'action métier associée (dépôt de rapport, envoi de
réponse...) : un MP raté ne doit jamais empêcher une opération de la CEAM.
Causes fréquentes d'échec : la personne a désactivé les MP venant des
membres du serveur, ou le bot n'a pas encore été invité sur le serveur HCT.
"""

import requests
from flask import current_app


def send_discord_dm(discord_id, content):
    """Envoie un MP Discord. Retourne True si envoyé, False sinon."""
    bot_token = current_app.config.get("DISCORD_BOT_TOKEN")
    if not bot_token:
        current_app.logger.warning(
            "DISCORD_BOT_TOKEN non configuré : notification DM ignorée."
        )
        return False

    headers = {
        "Authorization": f"Bot {bot_token}",
        "Content-Type": "application/json",
    }
    base_url = current_app.config["DISCORD_API_BASE_URL"]

    try:
        channel_resp = requests.post(
            f"{base_url}/users/@me/channels",
            headers=headers,
            json={"recipient_id": str(discord_id)},
            timeout=10,
        )
        channel_resp.raise_for_status()
        channel_id = channel_resp.json()["id"]

        message_resp = requests.post(
            f"{base_url}/channels/{channel_id}/messages",
            headers=headers,
            json={"content": content},
            timeout=10,
        )
        message_resp.raise_for_status()
        return True
    except requests.RequestException as exc:
        current_app.logger.warning(
            "Échec de l'envoi du MP Discord à %s : %s", discord_id, exc
        )
        return False