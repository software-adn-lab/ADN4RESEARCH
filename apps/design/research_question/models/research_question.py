from django.db import models
from django.conf import settings

class ResearchQuestion(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        READY_TO_SEND = 'READY_TO_SEND', 'Ready to Send'
        SUGGESTED = 'SUGGESTED', 'Suggested'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
    
    DISCUSSION_PHASE_STATUSES = [
        Status.SUGGESTED,
        Status.APPROVED,
        Status.REJECTED,
    ]
    project = models.ForeignKey('project.Project', on_delete=models.CASCADE, related_name='research_questions', default=None, null=True, blank=True)
    research_framework = models.ForeignKey('project.ResearchFramework', on_delete=models.CASCADE, related_name='research_questions')
    # Si estoy mandando solo el id. Asi si se define una relacion uno a muchos (El modelo de "muchos" se coloca como campo en el modelo "uno")
    researcher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='research_questions',
        null=True
    )
    question = models.TextField(blank=True)
    motivation = models.TextField(blank=True)
    
    justification = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, 
        choices=Status.choices,  
        default=Status.DRAFT     
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    framework_fields = models.JSONField(default=dict)
    @property
    def has_question_text(self):
        return bool(self.question and self.question.strip())

    @property
    def has_motivation(self):
        return bool(self.motivation and self.motivation.strip())

    @property
    def is_framework_complete(self):
        required_field_names = self.research_framework.fields_data.keys()
        if not required_field_names:
            return True 
        for field_name in required_field_names:
            if not self.framework_fields.get(field_name, '').strip():
                return False 
        return True

    def calculate_status(self):
        if self.is_framework_complete and self.has_question_text and self.has_motivation:
            return self.Status.READY_TO_SEND
        return self.Status.DRAFT

    def save(self, *args, **kwargs):
        if self.status not in self.DISCUSSION_PHASE_STATUSES: 
            self.status = self.calculate_status()
        super().save(*args, **kwargs)
        
    def get_status_display(self):
        return self.Status(self.status).label

    def __str__(self):
        return f"RQ-{self.id} ({self.status}) - {self.research_framework.name}"
