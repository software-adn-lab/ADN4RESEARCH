from django.db import models
from django.contrib.auth import get_user_model

from apps.selection.models.choices import (
    AssignmentStageChoices,
    SelectionDecisionChoices,
    SelectionStageChoices,
)
from apps.selection.features.distribution.models import SelectionPhase

User = get_user_model()


class PaperAssignment(models.Model):
    """
    Paper assignment to researchers.

    Tracks which papers are assigned to which researchers for review.
    Assignments are separate for screening and fulltext phases.
    """

    selection_phase = models.ForeignKey(
        SelectionPhase,
        on_delete=models.CASCADE,
        related_name='assignments'
    )

    paper_id = models.CharField(
        max_length=255,
        help_text="Study UUID from acquisition module"
    )

    researcher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='paper_assignments'
    )

    # Stage of this assignment (screening vs fulltext)
    stage = models.CharField(
        max_length=20,
        choices=AssignmentStageChoices.CHOICES,
        default=AssignmentStageChoices.SCREENING
    )

    # For third reviewer assignments in discrepancy resolution
    is_third_reviewer = models.BooleanField(
        default=False,
        help_text="True if this assignment is for discrepancy resolution"
    )

    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('selection_phase', 'paper_id', 'researcher', 'stage')
        verbose_name = 'Paper Assignment'
        verbose_name_plural = 'Paper Assignments'

    def __str__(self):
        stage_label = "3rd" if self.is_third_reviewer else self.stage
        return f"{self.researcher.username} - {self.paper_id[:8]} ({stage_label})"


class PaperReview(models.Model):
    """
    Individual researcher's review decision on a paper.

    Each assigned paper can have multiple reviews from different researchers.
    """

    assignment = models.ForeignKey(
        PaperAssignment,
        on_delete=models.CASCADE,
        related_name='reviews'
    )

    decision = models.CharField(
        max_length=20,
        choices=SelectionDecisionChoices.CHOICES,
        default=SelectionDecisionChoices.PENDING
    )

    stage = models.CharField(
        max_length=20,
        choices=SelectionStageChoices.CHOICES,
        help_text="Stage where this decision was made"
    )

    criterion_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="ID of inclusion/exclusion criterion from design phase"
    )

    criterion_label = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Human-readable label of the criterion"
    )

    notes = models.TextField(
        blank=True,
        help_text="Researcher's notes about the decision"
    )

    reviewed_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Paper Review'
        verbose_name_plural = 'Paper Reviews'

    def __str__(self):
        return f"{self.assignment.researcher.username} - {self.decision}"
