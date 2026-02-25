from django.contrib import admin

from apps.selection.domain.models import SelectionPhase, PaperAssignment, PaperReview, ConflictResolution

admin.site.register(SelectionPhase)
admin.site.register(PaperAssignment)
admin.site.register(PaperReview)
admin.site.register(ConflictResolution)
