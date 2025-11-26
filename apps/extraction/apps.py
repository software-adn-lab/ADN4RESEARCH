from django.apps import AppConfig


class ExtractionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.extraction'
    verbose_name = "Extraction Module"

    def ready(self):
        # Import models to register them
        from apps.extraction.core import models as core_models
        from apps.extraction.taxonomy import models as taxonomy_models
        from apps.extraction.planning import models as planning_models
