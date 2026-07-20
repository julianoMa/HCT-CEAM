import hashlib
import os

from dotenv import load_dotenv
from flask import Flask, url_for

from app.config import Config
from app.extensions import csrf, init_firestore, login_manager
from app.rich_text import render_chat_markdown, render_rich_text
from app.startup_check import run_startup_checks

load_dotenv()


def _compute_static_fingerprint(static_folder, filename):
    """Petite empreinte (8 caractères) du contenu actuel d'un fichier
    statique. Retourne None si le fichier est introuvable, pour ne jamais
    faire planter le rendu d'une page à cause de ça."""
    filepath = os.path.join(static_folder, filename)
    try:
        with open(filepath, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()[:8]
    except OSError:
        return None


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Cache navigateur LONG pour les fichiers statiques (CSS, JS, images) :
    # sûr uniquement parce que versioned_static() (ci-dessous) change l'URL
    # dès que le contenu du fichier change. Le navigateur ne voit donc
    # jamais une URL "périmée" — une mise à jour de style.css/app.js produit
    # une toute nouvelle URL, retéléchargée immédiatement, pendant que
    # l'ancienne reste en cache (inutilisée) jusqu'à expiration naturelle.
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 31536000  # 1 an

    # Cache des empreintes attaché à CETTE instance d'app (pas un cache de
    # module type @lru_cache) : il se reconstruit à chaque redémarrage de
    # process (donc à chaque déploiement), sans jamais rester bloqué sur
    # une empreinte périmée si un worker restait actif entre deux
    # déploiements — tout en évitant de relire le fichier à chaque requête
    # au sein d'un même process déjà démarré.
    static_fingerprints = {}

    @app.context_processor
    def inject_versioned_static():
        def versioned_static(filename):
            """À utiliser à la place de url_for('static', filename=...)
            pour CSS/JS/images qui changent entre déploiements : ajoute
            ?v=<empreinte> à l'URL, qui change automatiquement dès que le
            fichier change, forçant le navigateur à le retélécharger même
            s'il l'avait mis en cache pendant un an."""
            if filename not in static_fingerprints:
                static_fingerprints[filename] = _compute_static_fingerprint(app.static_folder, filename)
            url = url_for("static", filename=filename)
            fingerprint = static_fingerprints[filename]
            if fingerprint:
                url = f"{url}?v={fingerprint}"
            return url
        return dict(versioned_static=versioned_static)

    init_firestore(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    run_startup_checks(app)

    app.jinja_env.filters["rich_text"] = render_rich_text
    app.jinja_env.filters["chat_markdown"] = render_chat_markdown

    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.get_for_session(user_id)

    from app.auth.routes import bp as auth_bp
    from app.ceam.routes import bp as ceam_bp
    from app.admin.routes import bp as admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(ceam_bp)
    app.register_blueprint(admin_bp)

    from flask import redirect, url_for

    @app.route("/")
    def index():
        return redirect(url_for("ceam.accueil"))

    from flask_login import current_user

    @app.context_processor
    def inject_unread_notifications():
        if current_user.is_authenticated:
            from app.models.notification import Notification
            return {"unread_notifications_count": Notification.count_unread(current_user.id)}
        return {"unread_notifications_count": 0}

    from flask import render_template

    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(error):
        return render_template("errors/500.html"), 500

    return app