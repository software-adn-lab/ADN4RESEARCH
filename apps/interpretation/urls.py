from django.urls import path
from . import views

app_name = 'interpretation'

urlpatterns = [
    path('', views.index, name='index'),
    path('start/<int:subtheme_id>/', views.start_interpretation, name='start_interpretation'),
    path('context/<int:context_id>/', views.conversation_view, name='conversation'),
    path('context/<int:context_id>/draft/', views.create_draft, name='create_draft'),
    path('context/<int:context_id>/refine/<int:prop_id>/', views.refine_proposition, name='refine_proposition'),
    path('context/<int:context_id>/finalize/<int:prop_id>/', views.finalize_proposition, name='finalize_proposition'),
]
