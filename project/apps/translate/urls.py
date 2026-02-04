# project/apps/translate/urls.py
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from project.apps.translate.views import views

urlpatterns = [
    # path('trans', views.BillAnalyzeView.as_view(), name='trans'),
    path('trans', views.SingleBillAnalyzeView.as_view(), name='trans'),
    path('multi', views.MultiBillAnalyzeView.as_view(), name='multi'),
    path('task_group_status', views.TaskGroupStatusView.as_view(), name='task_group_status'),
    path('reparse', views.ReparseEntryView.as_view(), name='reparse'),
    path('cancel', views.CancelParseView.as_view(), name='cancel'),
    # 解析待办审核 API
    path('parse-review/<int:task_id>/results', views.ParseReviewResultsView.as_view(), name='parse_review_results'),
    path('parse-review/<int:task_id>/reparse', views.ParseReviewReparseView.as_view(), name='parse_review_reparse'),
    path('parse-review/<int:task_id>/entries/<str:uuid>/edit', views.ParseReviewEditView.as_view(), name='parse_review_edit'),
    path('parse-review/<int:task_id>/confirm', views.ParseReviewConfirmView.as_view(), name='parse_review_confirm'),
    path('parse-review/<int:task_id>/reparse-all', views.ParseReviewReparseAllView.as_view(), name='parse_review_reparse_all'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
