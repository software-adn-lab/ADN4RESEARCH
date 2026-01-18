from apps.interpretation.conclusion_assistant.models.theme_models import Theme
from apps.interpretation.conclusion_assistant.models.subtheme_models import SubTheme
from apps.interpretation.conclusion_assistant.models.proposition_models import InterpretativeProposition
from apps.project.structure.models.project_models import Project
from django.utils import timezone

class MarkdownExporter:
    def generate_report(self, project_id):
        project = Project.objects.get(id=project_id)
        themes = Theme.objects.filter(project=project)
        
        # Header
        markdown = f"# Reporte de Interpretación\n"
        markdown += f"**Proyecto:** {project.title}\n"
        markdown += f"**Fecha:** {timezone.now().strftime('%Y-%m-%d')}\n\n"
        
        markdown += "## Resumen del Proyecto\n"
        markdown += f"{project.summary}\n\n"
        markdown += "---\n\n"
        
        markdown += "## Síntesis Interpretativa\n\n"
        
        if not themes.exists():
            markdown += "*No se han generado temas para este proyecto.*\n"
            return markdown
            
        for theme in themes:
            markdown += f"### Tema: {theme.name}\n"
            if theme.description:
                markdown += f"*{theme.description}*\n\n"
            
            subthemes = SubTheme.objects.filter(theme=theme)
            
            if not subthemes.exists():
                markdown += "> *Sin subtemas definidos.*\n\n"
                continue
                
            for sub in subthemes:
                markdown += f"#### Subtema: {sub.name}\n"
                
                # Fetch finalized propositions
                finals = InterpretativeProposition.objects.filter(
                    subtheme=sub, 
                    status='FINAL'  # Using the string value directly or InterpretativeProposition.PropositionStatus.FINAL
                )
                
                if finals.exists():
                    markdown += "**Hallazgos Finales:**\n\n"
                    for prop in finals:
                        markdown += f"- **{prop.proposition_text}**\n"
                        if prop.supporting_narrative:
                            markdown += f"  > {prop.supporting_narrative}\n"
                    markdown += "\n"
                else:
                    markdown += "*No hay proposiciones finalizadas para este subtema.*\n\n"
            
            markdown += "---\n"
                    
        return markdown
