from django.db import models
from django.conf import settings


class InterpretativeProposition(models.Model):
    """
    Representa una proposición interpretativa (hallazgo) generada durante la síntesis.
    """
    class PropositionStatus(models.TextChoices):
        DRAFT = 'DRAFT', 'Borrador'
        REFINED = 'REFINED', 'Refinada'
        FINAL = 'FINAL', 'Final'

    subtheme = models.ForeignKey(
        'interpretation.SubTheme',
        on_delete=models.CASCADE,
        related_name='propositions'
    )
    proposition_text = models.TextField()
    supporting_narrative = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=PropositionStatus.choices,
        default=PropositionStatus.DRAFT
    )
    researcher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='propositions',
        null=True
    )
    conversation_trace = models.ForeignKey(
        'interpretation.ConversationTrace',
        on_delete=models.SET_NULL,
        related_name='propositions',
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Proposition ({self.status}) - {self.subtheme.name}"
