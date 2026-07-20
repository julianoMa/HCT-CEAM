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

_MOIS_FR = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]


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


def local_date(iso_string):
    """Retourne la date (jour civil, fuseau Europe/Paris) correspondant à
    cet horodatage UTC — utile pour comparer si deux évènements ont eu
    lieu le même jour côté utilisateur, DST géré automatiquement."""
    dt = datetime.fromisoformat(iso_string)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(APP_TIMEZONE).date()


def chat_date_label(iso_string):
    """Libellé relatif d'une date pour les séparateurs du chat :
    "Aujourd'hui", "Hier", ou "12 janvier" (avec l'année en plus si ce
    n'est pas l'année en cours)."""
    day = local_date(iso_string)
    today = datetime.now(APP_TIMEZONE).date()
    delta_days = (today - day).days

    if delta_days == 0:
        return "Aujourd'hui"
    if delta_days == 1:
        return "Hier"

    label = f"{day.day} {_MOIS_FR[day.month - 1]}"
    if day.year != today.year:
        label += f" {day.year}"
    return label