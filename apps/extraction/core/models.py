from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class ExtractionStatus(models.TextChoices):
    PENDING = 'Pending', 'Pendiente'
    IN_PROGRESS = 'InProgress', 'En Progreso'
    DONE = 'Done', 'Completado'


class PaperExtraction(models.Model):
    """
    Aggregate Root.
    Representa el proceso de extracción sobre un estudio (Paper).
    """
    study_id = models.IntegerField(unique=True, db_index=True)
    project_id = models.IntegerField(db_index=True)

    status = models.CharField(
        max_length=50,
        choices=ExtractionStatus.choices,
        default=ExtractionStatus.PENDING
    )

    assigned_to_id = models.IntegerField(null=True, blank=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['project_id', 'status']),
            models.Index(fields=['assigned_to_id', 'status']),
        ]

    @property
    def is_completed(self):
        return self.status == ExtractionStatus.DONE


class Quote(models.Model):
    """
    Entidad dependiente del Aggregate Root (PaperExtraction).
    """
    paper_extraction = models.ForeignKey(
        PaperExtraction,
        on_delete=models.CASCADE,
        related_name='quotes'
    )
    text_portion = models.TextField()
    location = models.CharField(max_length=100, blank=True)

    tags = models.ManyToManyField(
        'extraction.Tag',
        related_name='quotes',
        blank=True
    )

    researcher_id = models.IntegerField()
    validated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class Comment(models.Model):
    """
    Entidad de soporte para feedback.
    """
    user_id = models.IntegerField()
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
