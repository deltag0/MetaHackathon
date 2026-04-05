import peewee as pw

def migrate(migrator, database, fake=False, **kwargs):
    from app.models.user import User
    from app.models.url import URL
    from app.models.event import Event
    
    migrator.create_model(User)
    migrator.create_model(URL)
    migrator.create_model(Event)

def rollback(migrator, database, fake=False, **kwargs):
    from app.models.user import User
    from app.models.url import URL
    from app.models.event import Event
    
    migrator.remove_model(Event)
    migrator.remove_model(URL)
    migrator.remove_model(User)
