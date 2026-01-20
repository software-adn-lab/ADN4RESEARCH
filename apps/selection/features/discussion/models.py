from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.selection.models.choices import (
    AssignmentStageChoices,
    ResolutionMethodChoices,
    SelectionDecisionChoices,
)
from apps.selection.features.distribution.models import SelectionPhase

User = get_user_model()


class ConflictResolution(models.Model):
    """
    Conflict resolution for papers with disagreement.

    When researchers disagree on a paper, this tracks the resolution.
    Can be resolved by owner vote or by third reviewer.
    """

    selection_phase = models.ForeignKey(
        SelectionPhase,
        on_delete=models.CASCADE,
        related_name='conflicts'
    )

    paper_id = models.CharField(max_length=255)

    # Stage where conflict occurred
    stage = models.CharField(
        max_length=20,
        choices=AssignmentStageChoices.CHOICES,
        default=AssignmentStageChoices.SCREENING
    )

    # Resolution method and status
    resolution_method = models.CharField(
        max_length=20,
        choices=ResolutionMethodChoices.CHOICES,
        null=True,
        blank=True,
        help_text="How this conflict was/will be resolved"
    )

    is_resolved = models.BooleanField(default=False)

    # Third reviewer (if assigned)
    third_reviewer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='third_reviewer_conflicts',
        help_text="Third reviewer assigned to resolve this conflict"
    )

    # Final decision
    final_decision = models.CharField(
        max_length=20,
        choices=SelectionDecisionChoices.CHOICES,
        null=True,
        blank=True
    )

    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_conflicts'
    )

    resolution_notes = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('selection_phase', 'paper_id', 'stage')
        verbose_name = 'Conflict Resolution'
        verbose_name_plural = 'Conflict Resolutions'

    def __str__(self):
        status = "Resolved" if self.is_resolved else "Pending"
        return f"Conflict: {self.paper_id[:8]} ({self.stage}) - {status}"
