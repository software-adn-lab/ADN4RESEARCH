from django.db import models

# Create your models here.

class Notification(models.Model):
    TYPE_CHOICES = [
        ('RESEARCH_QUESTION_SUBMITTED_FOR_REVIEW', 'Research Question Submitted for Review'),
        ('SUGGESTION_QUESTION_REJECT', 'Suggestion Question Reject'),
    ]
    
    type = models.CharField(
        max_length=50,
        choices=TYPE_CHOICES
    )
    project = models.ForeignKey(
        'project.Project',
        on_delete=models.CASCADE,
        related_name='notifications',
        default=None,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    sender = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        related_name='sent_notifications',
        null=True
    )
    @property
    def message(self):
        if self.type == 'RESEARCH_QUESTION_SUBMITTED_FOR_REVIEW':
            return "A new research question has been submitted for review."
        elif self.type == 'SUGGESTION_QUESTION_REJECT':
            return "A suggestion question has been rejected."
        else:
            return ""


    def __str__(self):
        return f"Notification-{self.id} ({self.type}) for Project-{self.project.id}"
