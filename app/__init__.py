from dotenv import load_dotenv
from flask import Flask, jsonify
from app.extensions import mail
from app.database import init_db
from app.routes import register_routes


def create_app():
    load_dotenv()

    app = Flask(__name__)
    login_manager = LoginManager()
    login_manager.init_app(app)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret")
    init_db(app)

    app.config.update(
        MAIL_SERVER=os.environ.get("MAIL_SERVER", "smtp.gmail.com"),
        MAIL_PORT=int(os.environ.get("MAIL_PORT", 587)),
        MAIL_USE_TLS=True,
        MAIL_USERNAME=os.environ.get("MAIL_USERNAME"),
        MAIL_PASSWORD=os.environ.get("MAIL_PASSWORD"),
    )

    mail.init_app(app)

    from app import models  # noqa: F401 - registers models with Peewee

    register_routes(app)

    @app.route("/health")
    def health():
        return jsonify(status="ok")

    return app
