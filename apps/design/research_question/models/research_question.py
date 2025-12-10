from django.db import models
from django.conf import settings


class ResearchQuestionQuerySet(models.QuerySet):

    def by_project(self, project_id):
        return self.filter(design_phase_id=project_id)

    def by_status(self, status):
        return self.filter(status=status)

    def by_researcher(self, user):
        return self.filter(researcher=user)

    def in_discussion_phase(self):
        return self.filter(status__in=self.model.DISCUSSION_PHASE_STATUSES)


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
    objects = ResearchQuestionQuerySet.as_manager()
    design_phase = models.ForeignKey(
        'design.DesignPhase',
        on_delete=models.CASCADE,
        related_name='research_questions',
    )

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
    last_modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='modified_questions',
        help_text="User who last modified the research question"
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='reviewed_questions',
        help_text="Owner who reviewed the research question"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    modified_at = models.DateTimeField(auto_now=True)
    framework_fields = models.JSONField(default=dict)

    @property
    def project(self):
        return self.design_phase.project

    @property
    def research_framework(self):
        # Accedemos al framework a través de la cadena de relaciones
        return self.design_phase.project.research_framework

    @property
    def has_question_text(self):
        return bool(self.question and self.question.strip())

    @property
    def has_motivation(self):
        return bool(self.motivation and self.motivation.strip())

    @property
    def is_framework_complete(self):
        if not self.research_framework:
            return False
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

    def to_json(self):
        import json
        return json.dumps({
            'id': self.id,
            'question': self.question,
            'motivation': self.motivation,
            'framework_fields': self.framework_fields,
            'status': self.status,
        })

    def __str__(self):
        return f"RQ-{self.id} ({self.status})"