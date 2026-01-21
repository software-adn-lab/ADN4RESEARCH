"""
Forms - Core Bounded Context
Referencia: https://docs.djangoproject.com/en/stable/topics/forms/
"""
from django import forms
from django.core.exceptions import ValidationError
from .models import Quote, PaperExtraction
from apps.extraction.taxonomy.models import Tag


class QuoteForm(forms.ModelForm):
    """
    Formulario para crear/editar Quotes.
    Usa ModelForm para validaciones automáticas del modelo.
    """
    
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.none(),  # Se configura dinámicamente
        widget=forms.CheckboxSelectMultiple,
        required=True,
        error_messages={
            'required': 'Debes seleccionar al menos una etiqueta.'
        }
    )
    
    class Meta:
        model = Quote
        fields = ['text_fragment', 'paper_extraction', 'tags']
        widgets = {
            'text_fragment': forms.Textarea(attrs={
                'rows': 4,
                'class': 'textarea textarea-bordered',
                'readonly': True
            }),
            'paper_extraction': forms.HiddenInput(),
        }
    
    def __init__(self, *args, **kwargs):
        """
        Configurar queryset de tags según la fase del paper.
        """
        paper = kwargs.pop('paper', None)
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if paper:
            if user:
                # Tags usables por el usuario (incluye inductivos pendientes propios)
                self.fields['tags'].queryset = paper.extraction_phase.tags.usable_by(user)
            else:
                # Fallback: solo tags aprobados
                self.fields['tags'].queryset = paper.extraction_phase.tags.filter(
                    status='APPROVED'
                )
    
    def clean_text_fragment(self):
        """
        Validar longitud mínima del texto.
        Referencia: https://docs.djangoproject.com/en/stable/ref/forms/validation/
        """
        text = self.cleaned_data.get('text_fragment', '').strip()
        
        return text
