from dotenv import load_dotenv
from flask import Flask

from app.config import Config
from app.extensions import csrf, init_firestore, login_manager
from app.rich_text import render_rich_text
from app.startup_check import run_startup_checks

load_dotenv()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    init_firestore(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    run_startup_checks(app)

    app.jinja_env.filters["rich_text"] = render_rich_text

    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.get(user_id)

    from app.auth.routes import bp as auth_bp
    from app.ceam.routes import bp as ceam_bp
    from app.admin.routes import bp as admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(ceam_bp)
    app.register_blueprint(admin_bp)

    from flask import redirect, url_for

    @app.route("/")
    def index():
        return redirect(url_for("ceam.mes_dossiers"))

    return app