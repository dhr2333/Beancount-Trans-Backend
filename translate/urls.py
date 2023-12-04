from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from translate.views import view

urlpatterns = [
                  #   path('trans', view.py.analyze, name='trans'),
                  #   path('trans', views_test.analyze, name='trans'),
                  path('trans', view.AnalyzeView.as_view(), name='trans'),
                  # path("map/expense", view.py.ExpenseMapList.as_view(), name="expense"),
                  # path("map/expense/<int:pk>", view.py.ExpenseMapDetail.as_view(), name="expensedetail"),
                  # path("map/assets", view.py.AssetsMapList.as_view(), name="assets"),
                  # path("map/assets/<int:pk>", view.py.AssetsMapDetail.as_view(), name="assetsdetail"),
              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# router = DefaultRouter()
# router.register("map/expense", view.py.ExpenseMapViewSet)
# router.register("map/assets", view.py.AssetsMapViewSet)
# urlpatterns += router.urls
