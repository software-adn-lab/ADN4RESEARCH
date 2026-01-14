"""
Bounded Context: Taxonomy
Forms relacionados con Tags (Deductivos e Inductivos)

Referencia Django Forms:
https://docs.djangoproject.com/en/stable/topics/forms/
https://docs.djangoproject.com/en/stable/ref/forms/api/
"""
from django import forms
from django.core.exceptions import ValidationError

from .models import Tag, TagTypeChoices, VisibilityChoices, ApprovalStatusChoices
from apps.design.research_question.models.research_question import ResearchQuestion
from apps.extraction.shared.design_protocol import DesignProtocolAdapter


class DeductiveTagForm(forms.ModelForm):
    """
    Form para crear tags deductivos.
    
    Tags deductivos son definidos a priori por el líder del proyecto
    y están vinculados a preguntas de investigación.
    
    El campo rq_related se configura dinámicamente según el proyecto.
    """
    
    class Meta:
        model = Tag
        fields = ['name', 'rq_related']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Ej. Costo Financiero'
            }),
            'rq_related': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
        }

    def __init__(self, *args, **kwargs):
        """
        Inicializa el form y configura el queryset de rq_related
        según el proyecto proporcionado.
        
        Args:
            project: Instancia de Project para filtrar ResearchQuestions
        """
        project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)
        
        if project:
            self.fields['name'].required = True
            adapter = DesignProtocolAdapter()
            approved_questions = adapter.get_approved_questions(project.id)
            # Configurar queryset solo con RQs aprobadas del protocolo
            
            self.fields['rq_related'] = forms.ChoiceField(
                required=False,
                choices=[("", "-- Sin vincular a RQ --")] + [
                    (q["id"], q["question"]) for q in approved_questions
                ],
            )
            self.fields['rq_related'].required = False
            self.fields['rq_related'].empty_label = "-- Sin vincular a RQ --"


class InductiveTagForm(forms.ModelForm):
    """
    Form para crear tags inductivos durante la extracción.
    
    Tags inductivos emergen durante el proceso de extracción cuando
    un researcher identifica un patrón o tema no previsto.
    
    Características:
    - Se crean con estado PENDING
    - Visibilidad PRIVATE (solo el creador puede usarlo)
    - Requieren aprobación del líder para volverse públicos
    
    Referencia:
    https://docs.djangoproject.com/en/stable/topics/forms/modelforms/
    """
    
    class Meta:
        model = Tag
        fields = ['name', 'color']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Nombre del tag emergente',
                'required': True,
            }),
            'color': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'type': 'color',
                'value': '#6366F1',  # Color por defecto (Indigo)
            }),
        }
        labels = {
            'name': 'Nombre del Tag',
            'color': 'Color identificador',
        }
        help_texts = {
            'name': 'Describe el tema o patrón que identificaste.',
            'color': 'Selecciona un color para identificar visualmente este tag.',
        }

    def __init__(self, *args, **kwargs):
        """
        Inicializa el form.
        
        Args:
            phase: ExtractionPhase donde se crea el tag (requerido)
            user: Usuario que crea el tag (requerido para validación)
        """
        self.phase = kwargs.pop('phase', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Nombre es requerido para tags inductivos
        self.fields['name'].required = True
        
        # Color es opcional
        self.fields['color'].required = False

    def clean_name(self):
        """
        Valida que el nombre del tag sea único en la fase.
        
        Referencia:
        https://docs.djangoproject.com/en/stable/ref/forms/validation/#cleaning-a-specific-field-attribute
        """
        name = self.cleaned_data.get('name')
        
        if not name:
            raise ValidationError('El nombre del tag es requerido.')
        
        # Normalizar nombre (strip y capitalizar)
        name = name.strip()
        
        if len(name) < 2:
            raise ValidationError(
                'El nombre del tag debe tener al menos 2 caracteres.'
            )
        
        if len(name) > 100:
            raise ValidationError(
                'El nombre del tag no puede exceder 100 caracteres.'
            )
        
        # Verificar unicidad en la fase
        if self.phase:
            exists = Tag.objects.filter(
                extraction_phase=self.phase,
                name__iexact=name
            ).exists()
            
            if exists:
                raise ValidationError(
                    f'Ya existe un tag con el nombre "{name}" en esta fase.'
                )
        
        return name

    def clean_color(self):
        """
        Valida y normaliza el color hexadecimal.
        Si no se proporciona, genera uno aleatorio.
        """
        color = self.cleaned_data.get('color')
        
        if not color:
            # Generar color por defecto
            import random
            color = '#{:06x}'.format(random.randint(0, 0xFFFFFF))
        
        # Normalizar a mayúsculas
        return color.upper()

    def clean(self):
        """
        Validaciones a nivel de formulario.
        
        Referencia:
        https://docs.djangoproject.com/en/stable/ref/forms/validation/#cleaning-and-validating-fields-that-depend-on-each-other
        """
        cleaned_data = super().clean()
        
        if not self.phase:
            raise ValidationError(
                'No se puede crear un tag sin una fase de extracción asociada.'
            )
        
        if not self.user:
            raise ValidationError(
                'No se puede crear un tag sin un usuario asociado.'
            )
        
        return cleaned_data


class TagApprovalForm(forms.Form):
    """
    Form para aprobar o rechazar tags inductivos.
    
    Este form no es un ModelForm porque la acción de aprobación
    tiene lógica de negocio específica en el modelo/servicio.
    
    Referencia:
    https://docs.djangoproject.com/en/stable/topics/forms/
    """
    
    ACTION_APPROVE = 'approve'
    ACTION_REJECT = 'reject'
    
    ACTION_CHOICES = [
        (ACTION_APPROVE, 'Aprobar'),
        (ACTION_REJECT, 'Rechazar'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.RadioSelect(attrs={
            'class': 'radio radio-primary',
        }),
        label='Acción',
    )
    
    rejection_reason = forms.CharField(
        required=False,
        max_length=500,
        widget=forms.Textarea(attrs={
            'class': 'textarea textarea-bordered w-full',
            'rows': 3,
            'placeholder': 'Motivo del rechazo (opcional)',
        }),
        label='Motivo del rechazo',
        help_text='Si rechazas el tag, puedes indicar el motivo.',
    )

    def clean(self):
        """
        Validar que si se rechaza, el motivo sea proporcionado (opcional pero recomendado).
        """
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        reason = cleaned_data.get('rejection_reason')
        
        # Opcional: Requerir motivo para rechazo
        # if action == self.ACTION_REJECT and not reason:
        #     raise ValidationError(
        #         'Por favor, indica el motivo del rechazo.'
        #     )
        
        return cleaned_data


class TagFilterForm(forms.Form):
    """
    Form para filtrar tags en la vista de listado.
    
    Útil para que líderes de proyecto filtren tags pendientes
    de aprobación o por tipo.
    
    Referencia:
    https://docs.djangoproject.com/en/stable/topics/forms/
    """
    
    TYPE_CHOICES = [('', 'Todos los tipos')] + list(TagTypeChoices.CHOICES)
    STATUS_CHOICES = [('', 'Todos los estados')] + list(ApprovalStatusChoices.CHOICES)
    
    type = forms.ChoiceField(
        choices=TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'select select-bordered select-sm',
        }),
        label='Tipo',
    )
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'select select-bordered select-sm',
        }),
        label='Estado',
    )
    
    search = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered input-sm',
            'placeholder': 'Buscar por nombre...',
        }),
        label='Buscar',
    )
