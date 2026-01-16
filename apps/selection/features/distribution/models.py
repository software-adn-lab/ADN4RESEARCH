from django.db import models

from apps.selection.models.choices import (
    SelectionStatusChoices,
    SubPhaseStatusChoices,
    SelectionStageChoices,
)


class SelectionPhase(models.Model):
    """
    Selection phase model.

    Manages the systematic review selection process with two main phases:
    - Screening: Abstract-based paper selection (Overview -> Screening -> Discussion)
    - Full-text: PDF-based paper review (Overview -> Review -> Discussion)
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
        from apps.selection.features.discussion.services import DiscrepancyResolutionService
        service = DiscrepancyResolutionService(self)
        return len(service.get_conflicts(stage='SCREENING'))

    def get_fulltext_conflicts_count(self):
        """Get count of unresolved fulltext conflicts"""
        from apps.selection.features.discussion.services import DiscrepancyResolutionService
        service = DiscrepancyResolutionService(self)
        return len(service.get_conflicts(stage='FULL_TEXT'))
