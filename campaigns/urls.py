from django.urls import path

from . import views

app_name = "campaigns"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("campaigns/new/", views.create_campaign, name="create"),
    path("campaigns/<int:pk>/", views.campaign_detail, name="detail"),
    path("campaigns/<int:pk>/send/", views.send_campaign, name="send"),
    path("unsubscribe/<str:token>/", views.unsubscribe_confirm, name="unsubscribe"),
]
