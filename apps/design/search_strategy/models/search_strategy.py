from django.db import models
from django.conf import settings

class SearchStrategyQuerySet(models.QuerySet):
    def by_project(self, project_id):
        return self.filter(research_question__design_phase_id=project_id)

    def approved(self):
        return self.filter(status=self.model.Status.APPROVED)
    
class SearchStrategy(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft' 
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        
    research_question = models.ForeignKey(
        'design.ResearchQuestion',
        on_delete=models.CASCADE,
        related_name='search_strategies',
        blank=True,
        null=True
    )
    status = models.CharField(max_length=20, choices=Status.choices,  default=Status.DRAFT)
    final_search_string = models.TextField(blank=True)
    json_definition = models.JSONField(default=dict)
    total_studies_found = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True,related_name='created_strategies',help_text="User who created the strategy")
    created_at = models.DateTimeField(auto_now_add=True)
    objects = SearchStrategyQuerySet.as_manager()
    last_modified_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='modified_strategies',
        help_text="User who last modified the strategy"
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='reviewed_strategies',
        help_text="Who reviewed the search strategy"
    )

    def __str__(self):
        return f"Strategy for RQ-{self.research_question.id}"

class SearchStrategyVersion(models.Model):
    strategy = models.ForeignKey(
        SearchStrategy,
        on_delete=models.CASCADE,
        related_name='versions'
    )
    version_number = models.PositiveIntegerField()
    final_search_string = models.TextField()
    json_definition = models.JSONField(default=dict)
    total_found = models.PositiveIntegerField(default=0, help_text="Number of studies found with this strategy")
    status = models.CharField(max_length=20, choices=SearchStrategy.Status.choices, default=SearchStrategy.Status.DRAFT)
    justification = models.TextField(blank=True, null=True, help_text="Justification for approval/rejection")
    metadata_snapshot = models.JSONField(default=dict) 
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True) 

    class Meta:
        ordering = ['-version_number']
        unique_together = ('strategy', 'version_number')

    def __str__(self):
        return f"v{self.version_number} of Strategy {self.strategy_id}"