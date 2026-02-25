from django.urls import include, path

urlpatterns = [
    path('', include('apps.selection.features.distribution.metadata.urls')),
    path('', include('apps.selection.features.distribution.fulltext.urls')),
]
