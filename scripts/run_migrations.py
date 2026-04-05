import os
import time
import logging

from app.database import db
from playhouse.pool import PooledPostgresqlDatabase
from peewee_migrate import Router

database = PooledPostgresqlDatabase(
    os.environ.get("DATABASE_NAME", "hackathon_db"),
    host=os.environ.get("DATABASE_HOST", "localhost"),
    port=int(os.environ.get("DATABASE_PORT", 5432)),
    user=os.environ.get("DATABASE_USER", "postgres"),
    password=os.environ.get("DATABASE_PASSWORD", "postgres"),
)
db.initialize(database)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migrator")

def wait_for_db():
    retries = 30
    for i in range(retries):
        try:
            db.connect(reuse_if_open=True)
            db.close()
            logger.info("Database is ready!")
            return
        except Exception:
            logger.info(f"Waiting for database... ({i+1}/{retries})")
            time.sleep(2)
    raise Exception("Could not connect to database after 60 seconds")

if __name__ == "__main__":
    wait_for_db()
    
    router = Router(db, migrate_dir=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'migrations'))
    
    logger.info("Running migrations...")
    router.run()
    logger.info("Migrations completed successfully.")
