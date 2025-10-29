from django.contrib import admin

from apps.project.models import Membership, Project, Stage

# Register your models here.
admin.site.register(Project)
admin.site.register(Membership)
admin.site.register(Stage)