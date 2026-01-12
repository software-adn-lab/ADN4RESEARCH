from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class SelectionStatusChoices:
    """Selection phase status choices"""
    ON_GOING = 'ON_GOING'
    FINALIZED = 'FINALIZED'
    
    CHOICES = [
        (ON_GOING, 'On Going'),
        (FINALIZED, 'Finalized'),
    ]


class SelectionStageChoices:
    """Selection stage choices"""
    OVERVIEW = 'OVERVIEW'
    SCREENING = 'SCREENING'
    FULL_TEXT = 'FULL_TEXT'
    DISCUSSION = 'DISCUSSION'
    
    CHOICES = [
        (OVERVIEW, 'Overview'),
        (SCREENING, 'Screening'),
        (FULL_TEXT, 'Full-text Screening'),
        (DISCUSSION, 'Discussion'),
    ]


class SelectionPhase(models.Model):
    """
    Selection phase model.
    
    Manages the systematic review selection process with stages:
    - Overview: Distribution and progress tracking
    - Screening: Abstract-based paper selection
    - Full-text: Full paper review
    - Discussion: Conflict resolution
    """
    
    project = models.OneToOneField(
        'project.Project',
        on_delete=models.CASCADE,
        related_name='selection_phase',
        primary_key=True
    )
    
    status = models.CharField(
        max_length=20,
        choices=SelectionStatusChoices.CHOICES,
        default=SelectionStatusChoices.ON_GOING
    )
    
    current_stage = models.CharField(
        max_length=20,
        choices=SelectionStageChoices.CHOICES,
        default=SelectionStageChoices.OVERVIEW
    )
    
    is_active = models.BooleanField(default=True)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Selection Phase'
        verbose_name_plural = 'Selection Phases'
    
    def __str__(self):
        return f"Selection Phase - {self.project.title} ({self.status})"


class PaperAssignment(models.Model):
    """
    Paper assignment to researchers.
    
    Tracks which papers are assigned to which researchers for review.
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
    
    assigned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('selection_phase', 'paper_id', 'researcher')
        verbose_name = 'Paper Assignment'
        verbose_name_plural = 'Paper Assignments'
    
    def __str__(self):
        return f"{self.researcher.username} - {self.paper_id[:8]}"


class SelectionDecisionChoices:
    """Paper selection decision choices"""
    INCLUDED = 'INCLUDED'
    EXCLUDED = 'EXCLUDED'
    PENDING = 'PENDING'
    
    CHOICES = [
        (INCLUDED, 'Included'),
        (EXCLUDED, 'Excluded'),
        (PENDING, 'Pending'),
    ]


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


class ConflictResolution(models.Model):
    """
    Conflict resolution for papers with disagreement.
    
    When researchers disagree on a paper, this tracks the resolution.
    """
    
    selection_phase = models.ForeignKey(
        SelectionPhase,
        on_delete=models.CASCADE,
        related_name='conflicts'
    )
    
    paper_id = models.CharField(max_length=255)
    
    final_decision = models.CharField(
        max_length=20,
        choices=SelectionDecisionChoices.CHOICES
    )
    
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='resolved_conflicts'
    )
    
    resolution_notes = models.TextField()
    resolved_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('selection_phase', 'paper_id')
        verbose_name = 'Conflict Resolution'
        verbose_name_plural = 'Conflict Resolutions'
    
    def __str__(self):
        return f"Conflict: {self.paper_id[:8]} - {self.final_decision}"
