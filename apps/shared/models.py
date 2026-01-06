"""
Shared models for all phases.

This module contains abstract base models that are inherited by different phase modules
(Design, Selection, Extraction) to ensure consistent structure.
"""

from django.db import models


class BasePhase(models.Model):
    """
    Abstract base class for all phase models.

    Provides common fields for phase lifecycle management:
    - is_active: Whether the phase is currently active
    - start_date: Timestamp when phase was activated
    - end_date: Timestamp when phase was completed (null if ongoing)

    Inherited by:
    - DesignPhase (apps.design.design_phase_logic.models)
    - SelectionPhase (future)
    - ExtractionPhase (future)
    """

    is_active = models.BooleanField(
        default=False,
        help_text="Whether this phase is currently active"
    )

    start_date = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when phase was created/started"
    )

    end_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when phase was completed (null if ongoing)"
    )

    class Meta:
        abstract = True

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.__class__.__name__} ({status})"
