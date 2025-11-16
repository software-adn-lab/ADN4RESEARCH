from django.db import models

class Keyword(models.Model):
    """
    Represents a reusable keyword registered in the system.
    Example: 'desarrollo de software'
    """
    strategy = models.ForeignKey(
        'design.SearchStrategy',
        on_delete=models.CASCADE,
        related_name='keywords'
    )
    term = models.CharField(max_length=255) # Ej: "machine learning"
    # Guardamos los sinónimos como texto separado por comas (o un JSONField si prefieres)
    synonyms = models.TextField(blank=True) # Ej: "deep learning, ML, artificial intelligence"

    def __str__(self):
        return self.term

class ExclusionTerm(models.Model):
    """
    Representa UN término de exclusión perteneciente a UNA estrategia.
    """
    strategy = models.ForeignKey(
        'design.SearchStrategy', 
        on_delete=models.CASCADE, 
        related_name='exclusion_terms'
    )
    term = models.CharField(max_length=255) # Ej: "hardware testing"

    def __str__(self):
        return self.term