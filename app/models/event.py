from peewee import CharField, DateTimeField, ForeignKeyField
from datetime import datetime
from playhouse.postgres_ext import BinaryJSONField
from app.database import BaseModel
from app.models.user import User
from app.models.url import URL


class Event(BaseModel):
    class Meta:
        table_name = "events"

    url = ForeignKeyField(URL, backref="events")
    user = ForeignKeyField(User, backref="events", null=True)
    event_type = CharField(max_length=20)  # created | updated | deleted | clicked
    timestamp = DateTimeField(default=datetime.utcnow)
    details = BinaryJSONField(null=True)
