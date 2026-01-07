"""
URLs - Core Bounded Context
"""
from django.urls import path
from . import views

urlpatterns = [
     # Papers
     path('<int:pk>/', 
          views.PaperDetailView.as_view(), 
          name='paper_detail'),

     path('<int:pk>/pdf/', 
          views.PaperPDFView.as_view(), 
          name='paper_pdf'),

     # Completar paper
     path('<int:pk>/complete/', 
          views.PaperCompleteView.as_view(), 
          name='paper_complete'),

     # Quotes (API endpoints - sin DRF)
     path('quotes/create/', 
          views.QuoteCreateView.as_view(), 
          name='quote_create'),

     path('quotes/<int:pk>/delete/', 
          views.QuoteDeleteView.as_view(), 
          name='quote_delete'),
]