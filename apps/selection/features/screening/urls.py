from django.urls import include, path

urlpatterns = [
    path('', include('apps.selection.features.screening.metadata.urls')),
    path('', include('apps.selection.features.screening.fulltext.urls')),
]
