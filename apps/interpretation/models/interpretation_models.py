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


class SubTheme(models.Model):
    """
    Representa un subtema dentro de un tema principal.
    """
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pendiente'
        IN_PROGRESS = 'IN_PROGRESS', 'En Progreso'
        INTERPRETATION_COMPLETED = 'INTERPRETATION_COMPLETED', 'Interpretación Finalizada'

    theme = models.ForeignKey(Theme, on_delete=models.CASCADE, related_name='subthemes')
    name = models.CharField(max_length=255)
    central_codes = models.JSONField(default=list, blank=True)  # Lista de códigos centrales
    key_citations = models.JSONField(default=list, blank=True)  # Citas clave de estudios
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"SubTheme: {self.name} ({self.theme.name})"


class InterpretationContext(models.Model):
    """
    Representa el contexto activo de una sesión de interpretación.
    """
    subtheme = models.OneToOneField(SubTheme, on_delete=models.CASCADE, related_name='context')
    research_question = models.TextField()
    theme_name = models.CharField(max_length=255)
    extractions_context = models.JSONField(default=dict, blank=True)  # Datos de extracción relevantes
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Context for {self.subtheme.name}"


class ConversationTrace(models.Model):
    """
    Registra la traza completa de la conversación entre el investigador y el Copilot.
    Para fines de reflexividad y trazabilidad metodológica.
    """
    class MessageRole(models.TextChoices):
        RESEARCHER = 'RESEARCHER', 'Investigador'
        COPILOT = 'COPILOT', 'Copilot'
        SYSTEM = 'SYSTEM', 'Sistema'

    context = models.ForeignKey(
        InterpretationContext,
        on_delete=models.CASCADE,
        related_name='conversation_traces'
    )
    role = models.CharField(max_length=20, choices=MessageRole.choices)
    message = models.TextField()
    title = models.CharField(max_length=255, blank=True)
    body = models.TextField(blank=True)
    tags = models.CharField(max_length=255, blank=True)  # Separados por comas
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.role} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class InterpretativeProposition(models.Model):
    """
    Representa una proposición interpretativa (hallazgo) generada durante la síntesis.
    """
    class PropositionStatus(models.TextChoices):
        DRAFT = 'DRAFT', 'Borrador'
        REFINED = 'REFINED', 'Refinada'
        FINAL = 'FINAL', 'Final'

    subtheme = models.ForeignKey(SubTheme, on_delete=models.CASCADE, related_name='propositions')
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
        ConversationTrace,
        on_delete=models.SET_NULL,
        related_name='propositions',
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Proposition ({self.status}) - {self.subtheme.name}"
