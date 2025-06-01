from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from translate.views import views

urlpatterns = [
    path('analyze', views.UnifiedAnalyzeView.as_view(), name='analyze'),
    path('trans', views.SingleBillAnalyzeView.as_view(), name='trans'),
    path('multi', views.MultipleBillAnalyzeView.as_view(), name='multi'),
    path('entry', views.SingleEntryAnalyzeView.as_view(), name='entry'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
