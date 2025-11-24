from django.db import models


class ConversationTrace(models.Model):
    """
    Registra la traza completa de la conversación entre el investigador y el Copilot.
    Para fines de reflexividad y trazabilidad metodológica.
    """

    class MessageRole(models.TextChoices):
        RESEARCHER = "RESEARCHER", "Investigador"
        COPILOT = "COPILOT", "Copilot"
        SYSTEM = "SYSTEM", "Sistema"

    context = models.ForeignKey(
        "interpretation.InterpretationContext",
        on_delete=models.CASCADE,
        related_name="conversation_traces",
    )
    role = models.CharField(max_length=20, choices=MessageRole.choices)
    message = models.TextField()
    title = models.CharField(max_length=255, blank=True)
    body = models.TextField(blank=True)
    tags = models.CharField(max_length=255, blank=True)  # Separados por comas
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.role} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    def get_tags_list(self):
        """Return tags as a list, splitting by comma."""
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(",") if tag.strip()]
