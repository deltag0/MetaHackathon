from peewee import BooleanField, CharField, DateTimeField, ForeignKeyField, TextField
from datetime import datetime
from app.database import BaseModel
from app.models.user import User


class URL(BaseModel):
    class Meta:
        table_name = "urls"

    user = ForeignKeyField(User, backref="urls", null=True)
    short_code = CharField(max_length=10, unique=True)
    original_url = TextField()
    title = CharField(max_length=255, null=True)
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
