from django import forms
import json

class ResearchQuestionAutosaveForm(forms.Form):
    # Campos requeridos o opcionales según tu modelo
    question = forms.CharField(required=False, max_length=500) 
    motivation = forms.CharField(required=False, widget=forms.Textarea)
    # Recibimos el JSON string del frontend y lo convertimos a Dict
    framework_fields = forms.JSONField(required=False, initial=dict)
    
    # IDs necesarios para el ruteo, pero no se guardan en el modelo Question directamente
    project_id = forms.IntegerField(required=True)
    question_id = forms.IntegerField(required=False) # Puede ser nulo si es nuevo

    def clean_framework_fields(self):
        data = self.cleaned_data.get('framework_fields')
        # Si viene como string vacío o None, devolvemos dict vacío
        if not data:
            return {}
        return data