from django.contrib import admin

from apps.project.models import Membership, Project, ResearchFramework

# Register your models here.
admin.site.register(Project)
admin.site.register(Membership)
admin.site.register(ResearchFramework)