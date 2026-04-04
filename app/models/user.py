from peewee import CharField, DateTimeField
from datetime import datetime
from app.database import BaseModel


class User(BaseModel):
    class Meta:
        table_name = "users"

    email = CharField(max_length=255, unique=True)
    username = CharField(max_length=255, null=True)
    password_hash = CharField(max_length=255, default="")
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
