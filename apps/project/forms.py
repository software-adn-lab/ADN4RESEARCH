import json
from datetime import date
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
        widget=forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent', 'placeholder': 'PICO'})
    )
    framework_keys = forms.CharField(
        label="Framework Fields",
        help_text="Enter the fields separated by commas (e.g., Population, Intervention, Comparison, Outcome)",
        required=True,
        widget=forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent', 'rows': 2, 'placeholder': 'Population, Intervention, Comparison, Outcome'})
    )
    
    # Hidden field to store members with workload as JSON
    members_workload = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'id_members_workload'})
    )

    class Meta:
        model = Project
        fields = ['title', 'summary', 'motivation', 'general_objective', 'start_date', 'end_date']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent', 'placeholder': 'Project Title'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent', 'id': 'start-date-input', 'min': date.today().isoformat()}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent', 'id': 'end-date-input', 'min': date.today().isoformat()}),
            'summary': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent', 'rows': 3, 'placeholder': 'Brief summary...'}),
            'motivation': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent', 'rows': 3, 'placeholder': 'Why this research?'}),
            'general_objective': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent', 'rows': 3, 'placeholder': 'Main objective...'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date:
            if end_date < start_date:
                raise forms.ValidationError({
                    'end_date': 'End date must be greater than or equal to start date.'
                })

        return cleaned_data

    def clean_framework_keys(self):
        data = self.cleaned_data['framework_keys']
        # Convert comma separated string to list of trimmed strings
        keys = [k.strip() for k in data.split(',') if k.strip()]
        if not keys:
            raise forms.ValidationError("You must provide at least one field for the framework.")
        return keys
    
    def clean_members_workload(self):
        """Parse and validate members with workload data"""
        data = self.cleaned_data.get('members_workload', '')
        if not data or data.strip() == '':
            return []
        
        try:
            members_data = json.loads(data)
            validated = []
            for item in members_data:
                user_id = int(item.get('user_id'))
                workload = int(item.get('workload', 0))
                if workload < 0:
                    raise forms.ValidationError("Workload cannot be negative")
                validated.append({'user_id': user_id, 'workload': workload})
            return validated
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            raise forms.ValidationError(f"Invalid members workload data: {str(e)}")

class SpecificObjectiveForm(forms.ModelForm):
    class Meta:
        model = SpecificObjective
        fields = ['description']
        widgets = {
            'description': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent', 'rows': 2, 'placeholder': 'Describe a specific objective...'}),
        }

class ExpectedResultForm(forms.ModelForm):
    class Meta:
        model = ExpectedResult
        fields = ['description']
        widgets = {
            'description': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent', 'rows': 2, 'placeholder': 'Describe an expected result...'}),
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
