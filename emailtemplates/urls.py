from django.urls import path

from . import views

app_name = "emailtemplates"

urlpatterns = [
    path("", views.list_templates, name="list"),
    path("new/", views.create_template, name="create"),
    path("<int:pk>/edit/", views.edit_template, name="edit"),
    path("preview/", views.preview_partial, name="preview"),
]
