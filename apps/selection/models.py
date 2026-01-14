from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class SelectionStatusChoices:
    """Selection phase status choices"""
    ON_GOING = 'ON_GOING'
    FINALIZED = 'FINALIZED'
    
    CHOICES = [
        (ON_GOING, 'On Going'),
        (FINALIZED, 'Finalized'),
    ]


class SubPhaseStatusChoices:
    """Sub-phase status choices for screening and fulltext"""
    NOT_STARTED = 'NOT_STARTED'
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETED = 'COMPLETED'
    
    CHOICES = [
        (NOT_STARTED, 'Not Started'),
        (IN_PROGRESS, 'In Progress'),
        (COMPLETED, 'Completed'),
    ]


class SelectionStageChoices:
    """Selection stage choices"""
    # Screening sub-phases
    SCREENING_OVERVIEW = 'SCREENING_OVERVIEW'
    SCREENING = 'SCREENING'
    SCREENING_DISCUSSION = 'SCREENING_DISCUSSION'
    # Fulltext sub-phases
    FULLTEXT_OVERVIEW = 'FULLTEXT_OVERVIEW'
    FULLTEXT = 'FULLTEXT'
    FULLTEXT_DISCUSSION = 'FULLTEXT_DISCUSSION'
    
    CHOICES = [
        (SCREENING_OVERVIEW, 'Screening Overview'),
        (SCREENING, 'Screening'),
        (SCREENING_DISCUSSION, 'Screening Discussion'),
        (FULLTEXT_OVERVIEW, 'Full-text Overview'),
        (FULLTEXT, 'Full-text Review'),
        (FULLTEXT_DISCUSSION, 'Full-text Discussion'),
    ]
    
    # For backward compatibility with PaperReview stage field
    STAGE_SCREENING = 'SCREENING'
    STAGE_FULLTEXT = 'FULL_TEXT'


class AssignmentStageChoices:
    """Stage for paper assignments"""
    SCREENING = 'SCREENING'
    FULLTEXT = 'FULLTEXT'
    
    CHOICES = [
        (SCREENING, 'Screening'),
        (FULLTEXT, 'Full-text'),
    ]


class ResolutionMethodChoices:
    """Method used to resolve a conflict"""
    OWNER_VOTE = 'OWNER_VOTE'
    THIRD_REVIEWER = 'THIRD_REVIEWER'
    
    CHOICES = [
        (OWNER_VOTE, 'Owner Vote'),
        (THIRD_REVIEWER, 'Third Reviewer'),
    ]


class SelectionPhase(models.Model):
    """
    Selection phase model.
    
    Manages the systematic review selection process with two main phases:
    - Screening: Abstract-based paper selection (Overview → Screening → Discussion)
    - Full-text: PDF-based paper review (Overview → Review → Discussion)
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
        max_length=30,
        choices=SelectionStageChoices.CHOICES,
        default=SelectionStageChoices.SCREENING_OVERVIEW
    )
    
    # Screening metadata sub-phase (existing DB columns)
    screening_metadata_status = models.CharField(
        max_length=20,
        choices=SubPhaseStatusChoices.CHOICES,
        default=SubPhaseStatusChoices.NOT_STARTED
    )
    screening_metadata_start_date = models.DateTimeField(null=True, blank=True)
    screening_metadata_end_date = models.DateTimeField(null=True, blank=True)
    
    # Fulltext overview sub-phase (existing DB columns)
    fulltext_overview_status = models.CharField(
        max_length=20,
        choices=SubPhaseStatusChoices.CHOICES,
        default=SubPhaseStatusChoices.NOT_STARTED
    )
    fulltext_overview_start_date = models.DateTimeField(null=True, blank=True)
    fulltext_overview_end_date = models.DateTimeField(null=True, blank=True)
    
    # Fulltext screening sub-phase (existing DB columns)  
    fulltext_screening_status = models.CharField(
        max_length=20,
        choices=SubPhaseStatusChoices.CHOICES,
        default=SubPhaseStatusChoices.NOT_STARTED
    )
    fulltext_screening_start_date = models.DateTimeField(null=True, blank=True)
    fulltext_screening_end_date = models.DateTimeField(null=True, blank=True)
    
    # Discussion metadata sub-phase (existing DB columns)
    discussion_metadata_status = models.CharField(
        max_length=20,
        choices=SubPhaseStatusChoices.CHOICES,
        default=SubPhaseStatusChoices.NOT_STARTED
    )
    discussion_metadata_start_date = models.DateTimeField(null=True, blank=True)
    discussion_metadata_end_date = models.DateTimeField(null=True, blank=True)
    
    # Discussion fulltext sub-phase (existing DB columns)
    discussion_fulltext_status = models.CharField(
        max_length=20,
        choices=SubPhaseStatusChoices.CHOICES,
        default=SubPhaseStatusChoices.NOT_STARTED
    )
    discussion_fulltext_start_date = models.DateTimeField(null=True, blank=True)
    discussion_fulltext_end_date = models.DateTimeField(null=True, blank=True)
    
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
    
    # Properties for backward compatibility with new service layer
    @property
    def screening_status(self):
        """Alias for screening_metadata_status"""
        return self.screening_metadata_status
    
    @property
    def fulltext_status(self):
        """Alias for fulltext_screening_status"""
        return self.fulltext_screening_status
    
    @property
    def screening_distributed(self):
        """Check if screening has been distributed (started)"""
        return self.screening_metadata_status != SubPhaseStatusChoices.NOT_STARTED
    
    @property
    def fulltext_distributed(self):
        """Check if fulltext has been distributed (started)"""
        return self.fulltext_screening_status != SubPhaseStatusChoices.NOT_STARTED
    
    @property
    def screening_discussions_resolved(self):
        """Check if screening discussions are completed"""
        return self.discussion_metadata_status == SubPhaseStatusChoices.COMPLETED
    
    @property
    def fulltext_discussions_resolved(self):
        """Check if fulltext discussions are completed"""
        return self.discussion_fulltext_status == SubPhaseStatusChoices.COMPLETED
    
    def can_access_fulltext(self):
        """Check if fulltext phase can be accessed (screening completed with discussions resolved)"""
        return (
            self.screening_metadata_status == SubPhaseStatusChoices.COMPLETED and
            self.discussion_metadata_status == SubPhaseStatusChoices.COMPLETED
        )
    
    def get_screening_status_display(self):
        """Get display value for screening status"""
        return dict(SubPhaseStatusChoices.CHOICES).get(self.screening_metadata_status, self.screening_metadata_status)
    
    def get_fulltext_status_display(self):
        """Get display value for fulltext status"""
        return dict(SubPhaseStatusChoices.CHOICES).get(self.fulltext_screening_status, self.fulltext_screening_status)
    
    def get_screening_conflicts_count(self):
        """Get count of unresolved screening conflicts"""
        from apps.selection.services import DiscrepancyResolutionService
        service = DiscrepancyResolutionService(self)
        return len(service.get_conflicts(stage='SCREENING'))
    
    def get_fulltext_conflicts_count(self):
        """Get count of unresolved fulltext conflicts"""
        from apps.selection.services import DiscrepancyResolutionService
        service = DiscrepancyResolutionService(self)
        return len(service.get_conflicts(stage='FULL_TEXT'))


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
