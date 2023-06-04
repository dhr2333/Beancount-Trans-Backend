from django.urls import path

from . import views

urlpatterns = [
    path('users', views.indexUsers, name="indexusers"),
    path('users/add', views.addUsers, name="addusers"),
    path('users/insert', views.insertUsers, name="insertusers"),
    path('users/del/<int:uid>', views.delUsers, name="delusers"),
    path('users/edit/<int:uid>', views.editUsers, name="editusers"),
    path('users/update', views.updateUsers, name="updateusers"),
    path('cookie', views.demo_view),
    path('session', views.session_demo),
    # path('tpl', views.tpl),
    path('users/api', views.UserListView.as_view()),
    path('users/api/<id>', views.UserDetailView.as_view()),
    path('user', views.UserList.as_view(), name="user"),
    path('user/<int:pk>', views.UserDetail.as_view(), name="userdetail"),
    # path('upload', views.upload_file, name='upload_file'),
    # path('image_show', views.image_view, name='image_show'),
]
