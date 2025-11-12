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
]
