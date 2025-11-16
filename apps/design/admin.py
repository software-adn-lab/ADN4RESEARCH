from django.contrib import admin

from apps.design.eligibility_criteria.models.eligibility_criteria import EligibilityCriterion
from apps.design.research_question.models.research_question import ResearchQuestion, ResearchFramework
from apps.design.search_strategy.models.keyword import Keyword, ExclusionTerm
from apps.design.search_strategy.models.search_strategy import SearchStrategy

# Register your models here.
admin.site.register(ResearchQuestion)
admin.site.register(ResearchFramework)
admin.site.register(EligibilityCriterion)
admin.site.register(Keyword)
admin.site.register(ExclusionTerm)
admin.site.register(SearchStrategy)