from django.urls import include, path

app_name = 'selection'

urlpatterns = [
    path('', include('apps.selection.features.distribution.urls')),
    path('', include('apps.selection.features.screening.urls')),
    path('', include('apps.selection.features.discussion.urls')),
]
