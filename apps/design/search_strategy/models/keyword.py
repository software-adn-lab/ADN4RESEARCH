from django.db import models


class ProjectKeyword(models.Model):
    """
    Representa la DEFINICIÓN de un término clave y sus sinónimos a nivel de proyecto.
    Este es el "banco de términos" del proyecto.
    """
    project = models.ForeignKey(
        'project.Project', 
        on_delete=models.CASCADE, 
        related_name='project_keywords'
    )
    term = models.CharField(max_length=255) # Ej: "machine learning"
    synonyms = models.TextField(blank=True) # Ej: "deep learning, ML, artificial intelligence"

    class Meta:
        # Asegura que no puedas tener el mismo término dos veces en el mismo proyecto.
        unique_together = ('project', 'term')

    def __str__(self):
        return self.term

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
    project_keyword = models.ForeignKey(
        ProjectKeyword, 
        on_delete=models.CASCADE
    )

    def __str__(self):
        return self.project_keyword.term

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