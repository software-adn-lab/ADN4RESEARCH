from django import forms
import re

class ResearchQuestionAutosaveForm(forms.Form):
    question = forms.CharField(required=False, max_length=500) 
    motivation = forms.CharField(required=False, widget=forms.Textarea)
    framework_fields = forms.JSONField(required=False) 
    
    project_id = forms.IntegerField(required=True)
    question_id = forms.IntegerField(required=False)

    def clean(self):
        cleaned_data = super().clean()
        framework_data = {}
        pattern = re.compile(r'^framework_fields\[(.*?)\]$')
        
        for key, value in self.data.items():
            match = pattern.match(key)
            if match:
                field_name = match.group(1)
                framework_data[field_name] = value 

        cleaned_data['framework_fields'] = framework_data
        
        return cleaned_data