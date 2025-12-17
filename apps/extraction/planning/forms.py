from django import forms
from .models import ExtractionPhase
from ..taxonomy.models import Tag, TagTypeChoices

class ExtractionPhaseConfigForm(forms.ModelForm):
    class Meta:
        model = ExtractionPhase
        fields = ['start_date', 'due_date']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'input input-bordered w-full'}),
            'due_date': forms.DateInput(attrs={'type': 'date', 'class': 'input input-bordered w-full'}),
        }

class DeductiveTagForm(forms.ModelForm):
    rq_related_id = forms.IntegerField(required=False, widget=forms.Select(attrs={'class': 'select select-bordered w-full'}))

    class Meta:
        model = Tag
        fields = ['name', 'rq_related']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'input input-bordered w-full', 'placeholder': 'Ej. Costo Financiero'}),
        }

    def __init__(self, *args, **kwargs):
        project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)
        if project:
            self.fields['rq_related'].queryset = project.design_phase.research_questions.all()
            self.fields['rq_related'].widget.attrs.update({'class': 'select select-bordered w-full'})