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

    def __str__(self):
        return f"Strategy '{self.name}' for RQ-{self.research_question.id}"