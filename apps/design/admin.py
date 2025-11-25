from django.contrib import admin

from apps.design.eligibility_criteria.models.eligibility_criteria import EligibilityCriterion
from apps.design.research_question.models.research_question import ResearchQuestion
from apps.design.search_strategy.models.keyword import Keyword, ExclusionTerm, ProjectKeyword
from apps.design.search_strategy.models.search_strategy import SearchStrategy

# Register your models here.
admin.site.register(ResearchQuestion)
admin.site.register(EligibilityCriterion)
admin.site.register(Keyword)
admin.site.register(ExclusionTerm)
admin.site.register(SearchStrategy)
admin.site.register(ProjectKeyword)