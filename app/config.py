import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")

    # Durée de connexion : combien de temps une personne reste connectée
    # sans avoir à se reconnecter via Discord (par défaut 30 jours).
    REMEMBER_COOKIE_DURATION = timedelta(days=int(os.environ.get("REMEMBER_COOKIE_DAYS", 30)))
    PERMANENT_SESSION_LIFETIME = timedelta(days=int(os.environ.get("REMEMBER_COOKIE_DAYS", 30)))
    REMEMBER_COOKIE_HTTPONLY = True

    # Chemin vers le fichier de clé de compte de service Firebase (JSON),
    # utilisé en local uniquement.
    FIREBASE_CREDENTIALS_PATH = os.environ.get("FIREBASE_CREDENTIALS_PATH", "firebase-credentials.json")

    # En production (Vercel), colle le contenu JSON complet de la clé de
    # compte de service dans cette variable d'environnement à la place.
    FIREBASE_CREDENTIALS_JSON = os.environ.get("FIREBASE_CREDENTIALS_JSON")

    DISCORD_CLIENT_ID = os.environ.get("DISCORD_CLIENT_ID")
    DISCORD_CLIENT_SECRET = os.environ.get("DISCORD_CLIENT_SECRET")
    DISCORD_REDIRECT_URI = os.environ.get("DISCORD_REDIRECT_URI")
    DISCORD_GUILD_ID = os.environ.get("DISCORD_GUILD_ID")

    DISCORD_AUTHORIZE_URL = "https://discord.com/api/oauth2/authorize"
    DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"
    DISCORD_API_BASE_URL = "https://discord.com/api"