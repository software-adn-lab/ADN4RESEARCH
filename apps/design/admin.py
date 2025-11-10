from django.contrib import admin

from apps.design.research_question.models.research_question import ResearchQuestion, ResearchFramework

# Register your models here.
admin.site.register(ResearchQuestion)
admin.site.register(ResearchFramework)