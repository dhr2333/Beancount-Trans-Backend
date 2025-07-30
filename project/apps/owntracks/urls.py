from django.urls import path

from project.apps.owntracks import views

app_name = "owntracks"

urlpatterns = [
    path('logtracks', views.manage_owntrack_log, name='logtracks'),
    path('show_maps', views.show_maps, name='show_maps'),
    path('get_datas', views.get_datas, name='get_datas'),
    path('show_dates', views.show_log_dates, name='show_dates')
]
