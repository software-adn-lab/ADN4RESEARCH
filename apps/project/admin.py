from django.contrib import admin

from apps.project.models import Membership, Project, ResearchFramework, ProjectPhase

# Register your models here.
admin.site.register(Project)
admin.site.register(Membership)
admin.site.register(ResearchFramework)
admin.site.register(ProjectPhase)