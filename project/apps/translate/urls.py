# project/apps/translate/urls.py
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from project.apps.translate.views import views

urlpatterns = [
    # path('trans', views.BillAnalyzeView.as_view(), name='trans'),
    path('trans', views.SingleBillAnalyzeView.as_view(), name='trans'),
    path('multi', views.MultiBillAnalyzeView.as_view(), name='multi'),
    path('reparse', views.ReparseEntryView.as_view(), name='reparse'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
