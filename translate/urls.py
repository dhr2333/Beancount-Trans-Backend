from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

urlpatterns = [
                  path('trans', views.analyze, name='trans'),
                  # path("map/expense", views.ExpenseMapList.as_view(), name="expense"),
                  # path("map/expense/<int:pk>", views.ExpenseMapDetail.as_view(), name="expensedetail"),
                  path("map/assets", views.AssetsMapList.as_view(), name="assets"),
                  path("map/assets/<int:pk>", views.AssetsMapDetail.as_view(), name="assetsdetail"),
              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

router = DefaultRouter()
router.register("map/expense", views.ExpenseMapViewSet)
urlpatterns += router.urls
