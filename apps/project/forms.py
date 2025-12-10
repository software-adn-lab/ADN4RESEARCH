import json
from django import forms
from django.contrib.auth.models import User
from django.forms import inlineformset_factory

from apps.project.structure.models.project_models import Project, SpecificObjective, ExpectedResult, Membership

class ProjectForm(forms.ModelForm):
    # Framework fields
    framework_name = forms.CharField(
        max_length=50, 
        label="Framework Name",
        help_text="E.g., PICO, SPIDER",
        required=True,
        widget=forms.TextInput(attrs={'class': 'input input-bordered w-full', 'placeholder': 'PICO'})
    )
    framework_keys = forms.CharField(
        label="Framework Fields",
        help_text="Enter the fields separated by commas (e.g., Population, Intervention, Comparison, Outcome)",
        required=True,
        widget=forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 2, 'placeholder': 'Population, Intervention, Comparison, Outcome'})
    )
    
    # Members field (multi-select)
    members = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'select select-bordered w-full h-32'})
    )

    class Meta:
        model = Project
        fields = ['title', 'summary', 'motivation', 'general_objective', 'end_date']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'input input-bordered w-full', 'placeholder': 'Project Title'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'input input-bordered w-full'}),
            'summary': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 3, 'placeholder': 'Brief summary...'}),
            'motivation': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 3, 'placeholder': 'Why this research?'}),
            'general_objective': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 3, 'placeholder': 'Main objective...'}),
        }

    def clean_framework_keys(self):
        data = self.cleaned_data['framework_keys']
        # Convert comma separated string to list of trimmed strings
        keys = [k.strip() for k in data.split(',') if k.strip()]
        if not keys:
            raise forms.ValidationError("You must provide at least one field for the framework.")
        return keys

class SpecificObjectiveForm(forms.ModelForm):
    class Meta:
        model = SpecificObjective
        fields = ['description']
        widgets = {
            'description': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 2, 'placeholder': 'Describe a specific objective...'}),
        }

class ExpectedResultForm(forms.ModelForm):
    class Meta:
        model = ExpectedResult
        fields = ['description']
        widgets = {
            'description': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'rows': 2, 'placeholder': 'Describe an expected result...'}),
        }

# FormSets
SpecificObjectiveFormSet = inlineformset_factory(
    Project, 
    SpecificObjective, 
    form=SpecificObjectiveForm,
    extra=1,
    can_delete=True
)

ExpectedResultFormSet = inlineformset_factory(
    Project, 
    ExpectedResult, 
    form=ExpectedResultForm,
    extra=1,
    can_delete=True
)
