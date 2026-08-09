from django.urls import path

from . import views

app_name = "datafiles"

urlpatterns = [
    path("", views.list_files, name="list"),
    path("upload/", views.upload_file, name="upload"),
    path("<int:pk>/", views.file_detail, name="detail"),
]
