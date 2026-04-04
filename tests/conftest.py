import pytest

from app import create_app
from app.database import db
from app.models.event import Event
from app.models.url import URL
from app.models.user import User


@pytest.fixture(scope="session")
def app():
    application = create_app()
    with application.app_context():
        db.create_tables([User, URL, Event], safe=True)
        yield application
        db.drop_tables([Event, URL, User], safe=True)


@pytest.fixture(scope="session")
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def clean_db(app):
    yield
    with app.app_context():
        Event.delete().execute()
        URL.delete().execute()
        User.delete().execute()
