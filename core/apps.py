from django.apps import AppConfig
from django.dispatch import receiver
from django.db.backends.signals import connection_created

class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        # важно, чтобы модуль загрузился
        from . import translation  # noqa: F401

@receiver(connection_created)
def _sqlite_pragmas(sender, connection, **kwargs):
    if connection.vendor == "sqlite":
        cur = connection.cursor()
        cur.execute("PRAGMA journal_mode=WAL;")
        cur.execute("PRAGMA synchronous=NORMAL;")
        cur.execute("PRAGMA foreign_keys=ON;")
