# Beancount-Trans-Backend/project/apps/fava_instances/urls.py
from django.urls import path
from project.apps.fava_instances.views import FavaRedirectView, FavaStopView


urlpatterns = [
    path('',FavaRedirectView.as_view(), name='fava-redirect'),
    path('stop/', FavaStopView.as_view(), name='fava-stop'),
]
