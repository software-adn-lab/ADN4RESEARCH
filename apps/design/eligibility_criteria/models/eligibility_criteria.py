from django.db import models

class EligibilityCriterion(models.Model):
    class CriterionType(models.TextChoices):
        INCLUSION = 'INCLUSION', ('Inclusion')
        EXCLUSION = 'EXCLUSION', ('Exclusion')

    class CriterionStatus(models.TextChoices):
        DRAFT = 'DRAFT', ('Draft')
        APPROVED = 'APPROVED', ('Approved')
        REJECTED = 'REJECTED', ('Rejected')
        
    """Model representing inclusion criterion for research eligibility."""
    description = models.TextField()
    motivation = models.TextField(blank=True)
    project = models.ForeignKey('project.Project', on_delete=models.CASCADE, related_name='eligibility_criterion')
    suggester = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    type = models.CharField(
        max_length=10,
        choices=CriterionType.choices
    )
    status = models.CharField(max_length=10, choices=CriterionStatus.choices,  default=CriterionStatus.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_type_display()}: {self.description[:50]}"
    
    def get_type_display(self):
        return self.CriterionType(self.type).label
