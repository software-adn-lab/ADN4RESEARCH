from django.contrib import admin
from .core.models import PaperExtraction, Quote
from .taxonomy.models import Tag
from .planning.models import ExtractionPhase


admin.site.register(PaperExtraction)
admin.site.register(Quote)
admin.site.register(Tag)
admin.site.register(ExtractionPhase)