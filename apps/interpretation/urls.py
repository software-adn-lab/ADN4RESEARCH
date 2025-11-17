from django.urls import path
from . import views

app_name = 'interpretation'

urlpatterns = [
    # Scenario 1: Inicio de la Asistencia Contextual de Interpretación
    path('', views.index, name='index'),
    path('start/<int:subtheme_id>/', views.start_interpretation, name='start_interpretation'),
    path('context/<int:context_id>/', views.conversation_view, name='conversation'),
    
    # Scenario 2: Refinamiento Iterativo - Currently commented out in feature tests
    # Uncomment when Scenario 2 is activated
    # path('context/<int:context_id>/draft/', views.create_draft, name='create_draft'),
    # path('context/<int:context_id>/refine/<int:prop_id>/', views.refine_proposition, name='refine_proposition'),
    # path('context/<int:context_id>/finalize/<int:prop_id>/', views.finalize_proposition, name='finalize_proposition'),
    
    # AI-Driven Theme Discovery
    path('theme-discovery/<int:project_id>/', views.theme_discovery_view, name='theme_discovery'),
    path('theme-discovery/<int:project_id>/normalize/', views.normalize_codes, name='normalize_codes'),
    path('theme-discovery/normalization/<int:proposal_id>/accept/', views.accept_normalization, name='accept_normalization'),
    path('theme-discovery/<int:project_id>/accept-all-normalizations/', views.accept_all_normalizations, name='accept_all_normalizations'),
    path('theme-discovery/<int:project_id>/generate-themes/', views.generate_themes, name='generate_themes'),
    path('theme-discovery/theme/<int:proposal_id>/accept/', views.accept_theme, name='accept_theme'),
    path('theme-discovery/<int:project_id>/accept-all-themes/', views.accept_all_themes, name='accept_all_themes'),
    path('theme-discovery/<int:project_id>/finalize/', views.finalize_themes, name='finalize_themes'),
]
