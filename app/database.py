import os
from urllib.parse import urlparse

from playhouse.pool import PooledPostgresqlDatabase
from peewee import DatabaseProxy, Model

db = DatabaseProxy()


class BaseModel(Model):
    class Meta:
        database = db


def init_db(app):
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        parsed = urlparse(database_url)
        db_name = parsed.path.lstrip("/")
        kwargs = {
            "host": parsed.hostname,
            "port": parsed.port or 5432,
            "user": parsed.username,
            "password": parsed.password,
            "max_connections": 10,
            "stale_timeout": 300,
        }
        sslmode = os.environ.get("DATABASE_SSLMODE", "disable")
        if sslmode != "disable":
            kwargs["sslmode"] = sslmode
    else:
        db_name = os.environ.get("DATABASE_NAME", "hackathon_db")
        kwargs = {
            "host": os.environ.get("DATABASE_HOST", "localhost"),
            "port": int(os.environ.get("DATABASE_PORT", 5432)),
            "user": os.environ.get("DATABASE_USER", "postgres"),
            "password": os.environ.get("DATABASE_PASSWORD", "postgres"),
            "max_connections": 10,
            "stale_timeout": 300,
        }
        sslmode = os.environ.get("DATABASE_SSLMODE", "disable")
        if sslmode != "disable":
            kwargs["sslmode"] = sslmode
    database = PooledPostgresqlDatabase(
        db_name,
        **kwargs,
    )
    db.initialize(database)

    from app.models.user import User
    from app.models.url import URL
    from app.models.event import Event
    with database:
        database.create_tables([User, URL, Event], safe=True)

    @app.before_request
    def _db_connect():
        db.connect(reuse_if_open=True)

    @app.teardown_appcontext
    def _db_close(exc):
        if not db.is_closed():
            db.close()


def check_db_connection():
    db.execute_sql("SELECT 1")
