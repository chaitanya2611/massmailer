from django.urls import path

from . import views

app_name = "sending"

urlpatterns = [
    path("", views.list_accounts, name="list"),
    path("connect/<str:provider>/", views.connect_start, name="connect"),
    path("callback/<str:provider>/", views.oauth_callback, name="callback"),
    path("<int:pk>/disconnect/", views.disconnect, name="disconnect"),
]
