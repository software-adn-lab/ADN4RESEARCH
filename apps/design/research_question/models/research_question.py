from django.db import models
from django.conf import settings

class ResearchFramework(models.Model):
    """
    Defines a research framework (either global like PICO/PEO/PCC or custom).
    """
    FRAMEWORK_CHOICES = [
        ('PICO', 'PICO'),
        ('PEO', 'PEO'),
        ('PCC', 'PCC'),
    ]

    name = models.CharField(max_length=50)
    is_global = models.BooleanField(default=False)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='custom_frameworks',
        null=True,
        blank=True
    )
    total_fields = models.PositiveIntegerField(default=0)
    fields = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ('name', 'assigned_by')  

    @property
    def fields_completed(self):
        return sum(1 for f in self.fields.values() if f and str(f).strip())

    @property
    def is_complete(self):
        return self.fields_completed == self.total_fields

    def __str__(self):
        prefix = "Global" if self.is_global else "Custom"
        return f"{prefix} Framework: {self.name}"


class ResearchQuestion(models.Model):
    """
    Represents a research question created under a specific framework and stage.
    """
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        READY_TO_SEND = 'READY_TO_SEND', 'Ready to Send'
        SUGGESTED = 'SUGGESTED', 'Suggested'
        SUGGEST_REJECT = 'SUGGEST_REJECT', 'Suggest Reject'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        
    research_framework = models.ForeignKey(ResearchFramework, on_delete=models.CASCADE, related_name='research_questions')
    suggested_question = models.TextField(blank=True)
    motivation = models.TextField(blank=True)
    project = models.ForeignKey('project.Project', on_delete=models.CASCADE, related_name='research_questions', default=None, null=True, blank=True)
    stage = models.ForeignKey('project.Stage', on_delete=models.CASCADE, related_name='research_questions', default=None, null=True, blank=True)
    researcher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        
        on_delete=models.SET_NULL,
        related_name='research_questions',
        null=True
    )
    suggester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='suggested_questions',
        null=True,
        blank=True
    )
    justification = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, 
        choices=Status.choices,  
        default=Status.DRAFT     
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    framework_fields = models.JSONField(default=dict, blank=True)
    
    @property
    def has_question_text(self):
        return bool(self.suggested_question and self.suggested_question.strip())

    @property
    def has_motivation(self):
        return bool(self.motivation and self.motivation.strip())

    @property
    def is_framework_complete(self):
        required_field_names = self.research_framework.fields.keys()
        print("what", required_field_names)
        
        if not required_field_names:
            return True # If the framework has no required fields, it's complete.

        for field_name in required_field_names:
            # Check if the field exists in our data and has a non-empty value.
            if not self.framework_fields.get(field_name, '').strip():
                return False # A required field is missing or empty.
        
        return True
    
    def can_submit_for_review(self) -> bool:
        return self.status == self.Status.READY_TO_SEND

    def calculate_status(self):
        if self.is_framework_complete and self.has_question_text and self.has_motivation:
            return self.Status.READY_TO_SEND
        return self.Status.DRAFT

    def save(self, *args, **kwargs):
        if self.status != self.Status.SUGGESTED: self.status = self.calculate_status()
        super().save(*args, **kwargs)
        
    def get_status_display(self):
        return self.Status(self.status).label

    def __str__(self):
        return f"RQ-{self.id} ({self.status}) - {self.research_framework.name}"
