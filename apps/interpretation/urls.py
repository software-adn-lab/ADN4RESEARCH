from django.urls import path
from . import views
from . import theme_discovery_views

app_name = 'interpretation'

urlpatterns = [
    # Scenario 1: Inicio de la Asistencia Contextual de Interpretación
    path('', views.index, name='index'),
    path('start/<int:subtheme_id>/', views.start_interpretation, name='start_interpretation'),
    path('context/<int:context_id>/', views.conversation_view, name='conversation'),
    
    # Scenario 2: Refinamiento Iterativo
    path('context/<int:context_id>/draft/', views.create_draft, name='create_draft'),
    path('context/<int:context_id>/refine/<int:prop_id>/', views.refine_proposition, name='refine_proposition'),
    path('context/<int:context_id>/finalize/<int:prop_id>/', views.finalize_proposition, name='finalize_proposition'),
    
    # AI-Driven Theme Discovery
    path('theme-discovery/<int:project_id>/', theme_discovery_views.theme_discovery_view, name='theme_discovery'),
    path('theme-discovery/<int:project_id>/normalize/', theme_discovery_views.normalize_codes, name='normalize_codes'),
    path('theme-discovery/<int:project_id>/manual-normalize/', theme_discovery_views.create_manual_normalization, name='create_manual_normalization'),
    path('theme-discovery/normalization/<int:proposal_id>/accept/', theme_discovery_views.accept_normalization, name='accept_normalization'),
    path('theme-discovery/<int:project_id>/accept-all-normalizations/', theme_discovery_views.accept_all_normalizations, name='accept_all_normalizations'),
    path('theme-discovery/<int:project_id>/generate-themes/', theme_discovery_views.generate_themes, name='generate_themes'),
    path('theme-discovery/<int:project_id>/manual-theme/', theme_discovery_views.create_manual_theme, name='create_manual_theme'),
    path('theme-discovery/code/<int:code_id>/update-rq/', theme_discovery_views.update_rq_focus, name='update_rq_focus'),
    path('theme-discovery/theme/<int:proposal_id>/accept/', theme_discovery_views.accept_theme, name='accept_theme'),
    path('theme-discovery/<int:project_id>/accept-all-themes/', theme_discovery_views.accept_all_themes, name='accept_all_themes'),
    path('theme-discovery/<int:project_id>/finalize/', theme_discovery_views.finalize_themes, name='finalize_themes'),
    
    # Themes Created & Interpretation
    path('themes-created/', theme_discovery_views.themes_created_view, name='themes_created'),
    path('theme/<int:theme_id>/interpret/', views.start_theme_interpretation, name='start_theme_interpretation'),
    
    # Results Dashboard
    path('dashboard/<int:project_id>/', views.results_dashboard, name='results_dashboard'),
    path('dashboard/<int:project_id>/export/', views.export_findings, name='export_findings'),
]
