from django.apps import AppConfig

class ExtractionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.extraction'
    verbose_name = "Extraction Context"

    def ready(self):
        # Aquí podrías inicializar listeners de señales si usaras eventos de dominio
        # import extraction_refactor.infrastructure.signals
        pass