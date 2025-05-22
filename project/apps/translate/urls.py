from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from translate.views import view

urlpatterns = [
    path('trans', view.AnalyzeView.as_view(), name='trans'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
