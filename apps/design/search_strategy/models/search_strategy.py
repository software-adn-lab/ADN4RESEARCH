from django.db import models

class SearchStrategy(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        ACTIVE = 'ACTIVE', 'Active'
        ARCHIVED = 'ARCHIVED', 'Archived'
        
    research_question = models.ForeignKey(
        'design.ResearchQuestion',
        on_delete=models.CASCADE,
        related_name='search_strategies'
    )
    name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20, 
        choices=Status.choices,  
        default=Status.DRAFT     
    )
    # Aquí se guarda la CADENA FINAL GENERADA!!!!!! pilas
    final_search_string = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # approved_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL) # Opcional: Quién aprobó la estrategia

    def __str__(self):
        return f"Strategy '{self.name}' for RQ-{self.research_question.id}"

class SearchStrategyVersion(models.Model):
    """ Este es el memento"""
    strategy = models.ForeignKey(
        'design.SearchStrategy',
        on_delete=models.CASCADE,
        related_name='versions'
    )
    version_number = models.PositiveIntegerField()
    final_search_string = models.TextField()
    
    metadata_snapshot = models.JSONField(default=dict) 
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True) # Opcional: Saber quién hizo el cambio

    class Meta:
        ordering = ['-version_number']
        unique_together = ('strategy', 'version_number')

    def __str__(self):
        return f"v{self.version_number} of Strategy {self.strategy_id}"