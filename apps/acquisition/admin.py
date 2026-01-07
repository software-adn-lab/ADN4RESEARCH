"""Admin registrations for acquisition app (scaffold).
"""

from django.contrib import admin

# Register models here when ready.
from django.contrib import admin
from apps.acquisition.models import StudyModel

# Register your models here.
admin.site.register(StudyModel)