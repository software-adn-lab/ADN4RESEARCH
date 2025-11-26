from django.urls import path
from . import views

app_name = 'extraction'

urlpatterns = [
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),
    
    # API endpoints
    path('api/extraction/quotes/', views.QuoteAPIView.as_view(), name='api_quotes'),
    path('api/extraction/quotes/<int:quote_id>/', views.QuoteAPIView.as_view(), name='api_quote_detail'),
    
    path('api/extraction/tags/<int:tag_id>/', views.TagAPIView.as_view(), name='api_tag_detail'),
    path('api/extraction/tags/<int:tag_id>/approve/', views.TagApproveView.as_view(), name='api_tag_approve'),
    path('api/extraction/tags/<int:tag_id>/reject/', views.TagRejectView.as_view(), name='api_tag_reject'),
    
    path('api/extraction/phase/activate/', views.PhaseActivateView.as_view(), name='api_phase_activate'),
    path('api/extraction/complete/<int:extraction_id>/', views.ExtractionCompleteView.as_view(), name='api_extraction_complete'),
]
