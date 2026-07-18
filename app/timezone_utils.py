"""
Utilitaires de fuseau horaire.

Toutes les dates sont stockées en UTC (via datetime.utcnow()), ce qui est
la bonne pratique côté base de données — mais elles doivent être affichées
dans le fuseau horaire de la communauté (Europe/Paris) pour avoir un sens
réel pour les utilisateurs. Ce module centralise cette conversion, faite
uniquement à l'affichage, jamais au stockage.
"""

from datetime import datetime, timezone

from zoneinfo import ZoneInfo

APP_TIMEZONE = ZoneInfo("Europe/Paris")


def format_utc(iso_string, fmt="%d/%m/%Y à %H:%M"):
    """Parse une date ISO stockée en UTC (naïve, ex: '2026-01-15T14:30')
    et la formate dans le fuseau horaire de l'application. Gère
    automatiquement l'heure d'été/hiver. Retourne la chaîne d'origine si
    le parsing échoue, plutôt que de faire planter l'affichage sur une
    donnée déjà mal formée."""
    if not iso_string:
        return iso_string
    try:
        dt = datetime.fromisoformat(iso_string)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        local_dt = dt.astimezone(APP_TIMEZONE)
        return local_dt.strftime(fmt)
    except (ValueError, TypeError):
        return iso_string