from django.contrib import admin

from apps.selection.features.distribution.models import SelectionPhase
from apps.selection.features.screening.models import PaperAssignment, PaperReview
from apps.selection.features.discussion.models import ConflictResolution

admin.site.register(SelectionPhase)
admin.site.register(PaperAssignment)
admin.site.register(PaperReview)
admin.site.register(ConflictResolution)
