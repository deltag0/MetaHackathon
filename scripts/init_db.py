"""
Creates all tables and seeds data from CSV files.
Run with: uv run scripts/init_db.py
"""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from app.database import db, init_db
from app.models.user import User
from app.models.url import URL
from app.models.event import Event
from flask import Flask


def create_app():
    app = Flask(__name__)
    init_db(app)
    return app


def create_tables():
    print("Creating tables...")
    db.create_tables([User, URL, Event], safe=True)
    print("  users, urls, events tables ready.")


def seed_users(filepath="users.csv"):
    print(f"Seeding users from {filepath}...")
    with open(filepath, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    with db.atomic():
        for batch_start in range(0, len(rows), 100):
            batch = rows[batch_start:batch_start + 100]
            User.insert_many(batch).on_conflict_ignore().execute()

    print(f"  {len(rows)} users seeded.")


def seed_urls(filepath="urls.csv"):
    print(f"Seeding URLs from {filepath}...")
    with open(filepath, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Normalize is_active to boolean
    for row in rows:
        row["is_active"] = row["is_active"].strip().lower() == "true"
        row["user_id"] = row.pop("user_id")

    with db.atomic():
        for batch_start in range(0, len(rows), 100):
            batch = rows[batch_start:batch_start + 100]
            URL.insert_many(batch).on_conflict_ignore().execute()

    print(f"  {len(rows)} URLs seeded.")


def seed_events(filepath="events.csv"):
    print(f"Seeding events from {filepath}...")
    with open(filepath, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        row["url_id"] = row.pop("url_id")
        row["user_id"] = row.pop("user_id")
        # Parse JSON details string into dict
        try:
            row["details"] = json.loads(row["details"])
        except (json.JSONDecodeError, KeyError):
            row["details"] = {}

    with db.atomic():
        for batch_start in range(0, len(rows), 100):
            batch = rows[batch_start:batch_start + 100]
            Event.insert_many(batch).on_conflict_ignore().execute()

    print(f"  {len(rows)} events seeded.")


def reset_sequences():
    print("Resetting PostgreSQL sequences...")
    db.execute_sql("SELECT setval('users_id_seq',  (SELECT MAX(id) FROM users));")
    db.execute_sql("SELECT setval('urls_id_seq',   (SELECT MAX(id) FROM urls));")
    db.execute_sql("SELECT setval('events_id_seq', (SELECT MAX(id) FROM events));")
    print("  Sequences reset.")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        create_tables()
        seed_users()
        seed_urls()
        seed_events()
        reset_sequences()
        print("\nDone. Database is ready.")
