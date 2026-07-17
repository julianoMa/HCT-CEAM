"""
Vérifications de configuration exécutées à chaque démarrage de l'application
(en local via `flask run`, ou à chaque cold start sur Vercel), pour repérer
immédiatement une mauvaise configuration plutôt que de la découvrir plus
tard (ex: un membre qui n'arrive pas à se connecter).

Aucun problème détecté ici ne fait planter le démarrage de l'application :
tout est journalisé (WARNING/ERROR) mais l'app démarre quand même — mieux
vaut démarrer avec un avertissement clair dans les logs que refuser de
démarrer et bloquer tout le monde.
"""

from app.extensions import get_db

REQUIRED_ENV_VARS = [
    "SECRET_KEY",
    "DISCORD_CLIENT_ID",
    "DISCORD_CLIENT_SECRET",
    "DISCORD_REDIRECT_URI",
]


def run_startup_checks(app):
    """Exécute toutes les vérifications et journalise les problèmes trouvés."""
    _check_env_vars(app)
    _check_guild_id(app)
    _check_firebase_credentials(app)
    _check_firestore_connection(app)


def _check_env_vars(app):
    for key in REQUIRED_ENV_VARS:
        if not app.config.get(key):
            app.logger.error(
                "[Config] %s n'est pas défini : l'authentification Discord "
                "ne fonctionnera pas tant que cette variable n'est pas configurée.",
                key,
            )

    if app.config.get("SECRET_KEY") == "dev-secret-key":
        app.logger.warning(
            "[Config] SECRET_KEY utilise la valeur par défaut de développement. "
            "Ne jamais utiliser cette valeur en production : les sessions et "
            "jetons CSRF seraient prévisibles et falsifiables."
        )


def _check_guild_id(app):
    if not app.config.get("DISCORD_GUILD_ID"):
        app.logger.warning(
            "[Config] DISCORD_GUILD_ID n'est pas défini : la vérification "
            "d'appartenance au serveur HCT est désactivée à la connexion "
            "(n'importe quel compte Discord peut se connecter)."
        )


def _check_firebase_credentials(app):
    if not app.config.get("FIREBASE_CREDENTIALS_JSON") and not app.config.get("FIREBASE_CREDENTIALS_PATH"):
        app.logger.error(
            "[Config] Ni FIREBASE_CREDENTIALS_JSON ni FIREBASE_CREDENTIALS_PATH "
            "ne sont configurés : l'accès à Firestore va échouer."
        )


def _check_firestore_connection(app):
    """Vérifie que Firestore répond réellement, pas seulement que les
    identifiants ont pu être chargés. Ajoute un léger coût de latence à
    chaque démarrage (notable sur un cold start serverless) ; si besoin,
    ce check peut être désactivé en mettant STARTUP_HEALTHCHECK=0."""
    if str(app.config.get("STARTUP_HEALTHCHECK", "1")) == "0":
        return
    try:
        db = get_db()
        list(db.collection("counters").limit(1).stream())
        app.logger.info("[Config] Connexion Firestore OK.")
    except Exception as exc:  # noqa: BLE001 - on veut logger n'importe quel type d'erreur ici
        app.logger.error("[Config] Connexion Firestore impossible : %s", exc)