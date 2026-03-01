from django.urls import include, path

urlpatterns = [
    path('', include('apps.selection.features.discussion.metadata.urls')),
    path('', include('apps.selection.features.discussion.fulltext.urls')),
]
