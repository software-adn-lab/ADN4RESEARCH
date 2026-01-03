"""
Bounded Context: Planning
Forms relacionados con ExtractionPhase
"""
from django import forms
from .models import ExtractionPhase


class ExtractionPhaseConfigForm(forms.ModelForm):
    """Form para configurar fechas de una fase de extracción."""
    
    class Meta:
        model = ExtractionPhase
        fields = ['start_date', 'due_date']
        widgets = {
            'start_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'input input-bordered w-full'
            }),
            'due_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'input input-bordered w-full'
            }),
        }