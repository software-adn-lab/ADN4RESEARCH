"""
Bounded Context: Taxonomy
Forms relacionados con Tags
"""
from django import forms
from .models import Tag


class DeductiveTagForm(forms.ModelForm):
    """
    Form para crear tags deductivos.
    
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
            # Configurar queryset de preguntas de investigación del proyecto
            self.fields['rq_related'].queryset = (
                project.design_phase.research_questions.all()
            )
            self.fields['rq_related'].required = False
            self.fields['rq_related'].empty_label = "-- Sin vincular a RQ --"