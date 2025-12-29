"""
URLs del Bounded Context: Core (Papers y Quotes)
"""
from django.urls import path
from .views import (
    PDFServeView,
    PaperWorkspaceView,
    QuoteCreateView,
    QuoteDeleteView,
)

urlpatterns = [
    # Gestión de Papers
    path('<int:paper_id>/pdf/', 
         PDFServeView.as_view(), 
         name='serve_pdf'),
    
    path('<int:pk>/workspace/', 
         PaperWorkspaceView.as_view(), 
         name='paper_workspace'),
    
    # Gestión de Quotes
    path('quotes/create/', 
         QuoteCreateView.as_view(), 
         name='quote_create'),

    path('quotes/delete/<int:quote_id>/', 
         QuoteDeleteView.as_view(), 
         name='quote_delete'),

]