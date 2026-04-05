import os

from playhouse.pool import PooledPostgresqlDatabase
from peewee import DatabaseProxy, Model

db = DatabaseProxy()


class BaseModel(Model):
    class Meta:
        database = db


def init_db(app):
    kwargs = {
        "host": os.environ.get("DATABASE_HOST", "localhost"),
        "port": int(os.environ.get("DATABASE_PORT", 5432)),
        "user": os.environ.get("DATABASE_USER", "postgres"),
        "password": os.environ.get("DATABASE_PASSWORD", "postgres"),
        "max_connections": 2,
        "stale_timeout": 300,
    }
    sslmode = os.environ.get("DATABASE_SSLMODE", "disable")
    if sslmode != "disable":
        kwargs["sslmode"] = sslmode
    database = PooledPostgresqlDatabase(
        os.environ.get("DATABASE_NAME", "hackathon_db"),
        **kwargs,
    )
    db.initialize(database)

    @app.before_request
    def _db_connect():
        db.connect(reuse_if_open=True)

    @app.teardown_appcontext
    def _db_close(exc):
        if not db.is_closed():
            db.close()


def check_db_connection():
    db.execute_sql("SELECT 1")
