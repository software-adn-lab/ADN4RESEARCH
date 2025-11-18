from django.contrib import admin
from .conclusion_assistant.models import (
    Theme,
    SubTheme,
    InterpretationContext,
    ConversationTrace,
    InterpretativeProposition
)


@admin.register(Theme)
class ThemeAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_by', 'created_at', 'modified_at')
    search_fields = ('name', 'description', 'research_question')
    list_filter = ('created_at', 'created_by')


@admin.register(SubTheme)
class SubThemeAdmin(admin.ModelAdmin):
    list_display = ('name', 'theme', 'status', 'created_at', 'modified_at')
    search_fields = ('name', 'theme__name')
    list_filter = ('status', 'created_at')


@admin.register(InterpretationContext)
class InterpretationContextAdmin(admin.ModelAdmin):
    list_display = ('subtheme', 'theme_name', 'is_active', 'created_at')
    search_fields = ('subtheme__name', 'theme_name', 'research_question')
    list_filter = ('is_active', 'created_at')


@admin.register(ConversationTrace)
class ConversationTraceAdmin(admin.ModelAdmin):
    list_display = ('context', 'role', 'title', 'created_at')
    search_fields = ('title', 'message', 'body')
    list_filter = ('role', 'created_at')
    ordering = ('-created_at',)


@admin.register(InterpretativeProposition)
class InterpretativePropositionAdmin(admin.ModelAdmin):
    list_display = ('subtheme', 'status', 'researcher', 'created_at', 'modified_at')
    search_fields = ('proposition_text', 'supporting_narrative', 'subtheme__name')
    list_filter = ('status', 'created_at', 'researcher')
    readonly_fields = ('created_at', 'modified_at')
