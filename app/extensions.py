import json

import firebase_admin
from firebase_admin import credentials, firestore
from flask_login import LoginManager
from flask_wtf import CSRFProtect

login_manager = LoginManager()
csrf = CSRFProtect()

login_manager.login_view = "auth.login"
login_manager.login_message = "Merci de te connecter avec Discord pour accéder à cette page."

_firestore_client = None


def init_firestore(app):
    """Initialise l'app Firebase Admin et le client Firestore, une seule fois.

    En local : lit le fichier de clé de compte de service désigné par
    FIREBASE_CREDENTIALS_PATH.
    En production (Vercel, etc., sans disque persistant) : lit le JSON
    complet de la clé directement depuis la variable d'environnement
    FIREBASE_CREDENTIALS_JSON.
    """
    global _firestore_client

    if not firebase_admin._apps:
        cred_json = app.config.get("FIREBASE_CREDENTIALS_JSON")
        if cred_json:
            cred = credentials.Certificate(json.loads(cred_json))
        else:
            cred_path = app.config["FIREBASE_CREDENTIALS_PATH"]
            cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)

    _firestore_client = firestore.client()
    return _firestore_client


def get_db():
    """Retourne le client Firestore courant (à appeler après init_firestore)."""
    if _firestore_client is None:
        raise RuntimeError("Firestore n'est pas initialisé. Appelle init_firestore(app) au démarrage.")
    return _firestore_client