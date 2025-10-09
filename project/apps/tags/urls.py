from rest_framework.routers import DefaultRouter
from project.apps.tags.views import TagViewSet

router = DefaultRouter()
router.register(r'tags', TagViewSet, basename='tag')

urlpatterns = router.urls



