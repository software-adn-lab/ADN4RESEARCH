from django.contrib import admin

from apps.design.models.research_question_models import ResearchQuestion, ResearchFramework

# Register your models here.
admin.site.register(ResearchQuestion)
admin.site.register(ResearchFramework)