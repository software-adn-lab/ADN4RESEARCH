from django.db import models

# Create your models here.

class Notification(models.Model):
    TYPE_CHOICES = [
        ('RESEARCH_QUESTION_SUBMITTED_FOR_REVIEW', 'Research Question Submitted for Review'),
        ('RESEARCH_QUESTION_REVIEWED', 'Research Question Reviewed'),
        ('SUGGESTION_QUESTION_REJECT', 'Suggestion Question Reject'),
        ('CRITERION_APPROVED', 'Eligibility Criterion Approved'),
        ('CRITERION_REJECTED', 'Eligibility Criterion Rejected'),
        ('STRATEGY_APPROVED', 'Search Strategy Approved'),
        ('STRATEGY_REJECTED', 'Search Strategy Rejected'),
        ('STAGE_CONSOLIDATED', 'Design Stage Finalized'),
        ('OWNER_MODIFIED_APPROVED_QUESTION', 'Owner Modified Approved Question in Closed Stage'),
        ('OWNER_MODIFIED_APPROVED_CRITERION', 'Owner Modified Approved Criterion in Closed Stage'),
        ('OWNER_MODIFIED_APPROVED_STRATEGY', 'Owner Modified Approved Strategy in Closed Stage'),
        ('REMINDER', 'Review Reminder'),
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
    recipient = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='received_notifications',
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
    title = models.CharField(max_length=200, blank=True, default='')
    custom_message = models.TextField(blank=True, default='')
    is_read = models.BooleanField(default=False)
    
    @property
    def message(self):
        if self.custom_message:
            return self.custom_message
        elif self.type == 'RESEARCH_QUESTION_SUBMITTED_FOR_REVIEW':
            return "A new research question has been submitted for review."
        elif self.type == 'RESEARCH_QUESTION_REVIEWED':
            return "Your research question has been reviewed."
        elif self.type == 'SUGGESTION_QUESTION_REJECT':
            return "A suggestion question has been rejected."
        elif self.type == 'CRITERION_APPROVED':
            return "Your eligibility criterion has been approved."
        elif self.type == 'CRITERION_REJECTED':
            return "Your eligibility criterion has been rejected."
        elif self.type == 'STRATEGY_APPROVED':
            return "Your search strategy has been approved."
        elif self.type == 'STRATEGY_REJECTED':
            return "Your search strategy has been rejected."
        elif self.type == 'STAGE_CONSOLIDATED':
            return "A design stage has been consolidated."
        elif self.type == 'OWNER_MODIFIED_APPROVED_QUESTION':
            return "The project owner has modified an approved research question in a closed stage."
        elif self.type == 'OWNER_MODIFIED_APPROVED_CRITERION':
            return "The project owner has modified an approved eligibility criterion in a closed stage."
        elif self.type == 'OWNER_MODIFIED_APPROVED_STRATEGY':
            return "The project owner has modified an approved search strategy in a closed stage."
        elif self.type == 'REMINDER':
            return "You have pending papers to review."
        else:
            return ""

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification-{self.id} ({self.type}) for Project-{self.project.id if self.project else 'N/A'}"
