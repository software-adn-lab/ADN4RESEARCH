# apps/extraction/models.py

# Importamos los modelos desde la capa de infraestructura
# para que Django los detecte y pueda crear las migraciones.
from .infrastructure.models import (
    ExtractionModel,
    TagModel,
    QuoteModel
)

# Nota: No definas nada más aquí, solo impórtalos.