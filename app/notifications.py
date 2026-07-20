"""
Envoi de notifications par message privé (MP) Discord, via le bot de
l'application (nécessite DISCORD_BOT_TOKEN, voir app/config.py).

Toute notification échoue silencieusement (log uniquement) plutôt que de
faire planter l'action métier associée (dépôt de rapport, envoi de
réponse...) : un MP raté ne doit jamais empêcher une opération de la CEAM.
Causes fréquentes d'échec : la personne a désactivé les MP venant des
membres du serveur, ou le bot n'a pas encore été invité sur le serveur HCT.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import requests
from flask import current_app

# Doré, cohérent avec l'identité visuelle du site (variable CSS --accent).
ACCENT_COLOR = 0xF4B65D


def send_discord_dm_bulk(discord_ids, content=None, embed=None):
    """Envoie le même MP à PLUSIEURS personnes EN PARALLÈLE, pas les unes
    après les autres. Chaque MP Discord nécessite 2 appels réseau
    (création/récupération du canal, puis envoi du message) — les envoyer
    en série à toute la commission (dépôt de rapport, nouveau message...)
    pouvait bloquer la réponse plusieurs secondes, le temps de tous les
    finir un par un. Des threads suffisent ici : ce sont des appels
    réseau (I/O), donc le GIL se libère pendant l'attente — pas besoin de
    vrai parallélisme CPU. Reste dans le cycle requête/réponse (pas de
    tâche en arrière-plan qui pourrait être interrompue par la plateforme
    une fois la réponse envoyée)."""
    if not discord_ids:
        return
    # current_app est un proxy lié au contexte de LA requête en cours —
    # il faut le résoudre en objet concret avant de le réutiliser dans un
    # thread, qui n'a pas ce contexte par défaut.
    app = current_app._get_current_object()

    def _send_one(discord_id):
        with app.app_context():
            try:
                send_discord_dm(discord_id, content=content, embed=embed)
            except Exception:  # noqa: BLE001 - un MP raté ne doit jamais faire planter le reste
                app.logger.warning("Échec inattendu de l'envoi d'un MP Discord à %s", discord_id)

    with ThreadPoolExecutor(max_workers=min(8, len(discord_ids))) as executor:
        list(executor.map(_send_one, discord_ids))


def build_embed(title, description, fields=None, url=None):
    """Construit un embed Discord simple et cohérent (couleur, pied de
    page, horodatage), utilisé pour toutes les notifications CEAM."""
    embed = {
        "title": title,
        "description": description,
        "color": ACCENT_COLOR,
        "footer": {"text": "Commission d'Éthique des Affaires Médicales"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if url:
        embed["url"] = url
    if fields:
        embed["fields"] = fields
    return embed


def send_discord_dm(discord_id, content=None, embed=None):
    """Envoie un MP Discord — sous forme d'embed si `embed` est fourni
    (recommandé, voir build_embed), sinon en texte brut via `content`.
    Retourne True si envoyé, False sinon."""
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

    payload = {}
    if content:
        payload["content"] = content
    if embed:
        payload["embeds"] = [embed]

    try:
        channel_resp = requests.post(
            f"{base_url}/users/@me/channels",
            headers=headers,
            json={"recipient_id": str(discord_id)},
            timeout=5,
        )
        channel_resp.raise_for_status()
        channel_id = channel_resp.json()["id"]

        message_resp = requests.post(
            f"{base_url}/channels/{channel_id}/messages",
            headers=headers,
            json=payload,
            timeout=5,
        )
        message_resp.raise_for_status()
        return True
    except requests.RequestException as exc:
        current_app.logger.warning(
            "Échec de l'envoi du MP Discord à %s : %s", discord_id, exc
        )
        return False