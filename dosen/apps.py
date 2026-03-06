from django.apps import AppConfig

class DosenConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dosen"
    verbose_name = "Dosen Digital"

    def ready(self):
        from . import signals  # noqa: F401
