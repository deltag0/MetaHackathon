import os
import time
import logging
from app.database import db

# ensure models are imported
from app.models.user import User
from app.models.url import URL
from app.models.event import Event

from peewee_migrate import Router

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
        except Exception as e:
            logger.info(f"Waiting for database... ({i+1}/{retries})")
            time.sleep(2)
    raise Exception("Could not connect to database after 60 seconds")

if __name__ == "__main__":
    wait_for_db()
    
    router = Router(db, migrate_dir=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'migrations'))
    
    logger.info("Running migrations...")
    router.run()
    logger.info("Migrations completed successfully.")
