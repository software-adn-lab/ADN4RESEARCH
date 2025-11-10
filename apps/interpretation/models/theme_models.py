from django.db import models
from django.conf import settings


class Theme(models.Model):
    """
    Representa un tema principal de investigación en la SLR.
    """

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    research_question = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='themes'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Theme: {self.name}"
