from peewee import AutoField, TextField

from app.database import BaseModel


class Url(BaseModel):
    id = AutoField()
    user_id = IntegerField()
    original_url = TextField()
    short_code = TextField()
    title = TextField()
    is_active = BooleanField()
    created_at = DateTimeField()
    updated_at = DateTimeField()

    class Meta:
        table_name = "urls"

class User(BaseModel):
    id = AutoField()
    username = TextField()
    email = TextField()
    created_at = DateTimeField()

    class Meta:
        table_name = "users"
    
    
