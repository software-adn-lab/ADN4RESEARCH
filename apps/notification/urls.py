from django.urls import path
from apps.notification import views

app_name = 'notification'

urlpatterns = [
    path('', views.notification_list, name='list'),
    path('<int:notification_id>/read/', views.mark_as_read, name='mark_as_read'),
    path('mark-all-read/', views.mark_all_as_read, name='mark_all_as_read'),
    path('unread-count/', views.unread_count, name='unread_count'),
]
