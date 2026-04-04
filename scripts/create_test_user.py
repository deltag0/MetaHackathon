"""
Creates a test user for local development.
Run with: uv run scripts/create_test_user.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from flask import Flask
from werkzeug.security import generate_password_hash

from app.database import db, init_db
from app.models.user import User


def create_app():
    load_dotenv()
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret")
    init_db(app)
    return app


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        db.create_tables([User], safe=True)

        email = "test@example.com"
        password = "password123"

        existing = User.get_or_none(User.email == email)
        if existing:
            print(f"Test user already exists: {email}")
        else:
            User.create(
                email=email,
                password_hash=generate_password_hash(password),
            )
            print("Test user created:")

        print(f"  Email:    {email}")
        print(f"  Password: {password}")
