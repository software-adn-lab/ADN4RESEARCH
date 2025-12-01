from django.db import models
from django.conf import settings

class EligibilityCriterionQuerySet(models.QuerySet):
    def by_project(self, project_id):
        return self.filter(design_phase_id=project_id)

    def by_type(self, criteria_type):
        return self.filter(type=criteria_type)
    
class EligibilityCriterion(models.Model):
    class CriterionType(models.TextChoices):
        INCLUSION = 'INCLUSION', ('Inclusion')
        EXCLUSION = 'EXCLUSION', ('Exclusion')

    class CriterionStatus(models.TextChoices):
        DRAFT = 'DRAFT', ('Draft')
        APPROVED = 'APPROVED', ('Approved')
        REJECTED = 'REJECTED', ('Rejected')
        
    description = models.TextField()
    motivation = models.TextField(blank=True)
    design_phase = models.ForeignKey('design.DesignPhase',on_delete=models.CASCADE, related_name='criteria')
    researcher = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    last_modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='modified_criteria',
        help_text="User who last modified the criterion"
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='reviewed_criteria',
        help_text="User who reviewed the criterion"
    )
    type = models.CharField(
        max_length=10,
        choices=CriterionType.choices
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=CriterionStatus.choices,  default=CriterionStatus.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = EligibilityCriterionQuerySet.as_manager()

    def __str__(self):
        return f"{self.get_type_display()}: {self.description[:50]}"
    
    def get_type_display(self):
        return self.CriterionType(self.type).label
