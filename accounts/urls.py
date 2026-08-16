from django.conf import settings
from django.contrib.auth import views as auth_views
from django.urls import path

from core.ratelimit import rate_limit

from . import views

app_name = "accounts"

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path(
        "login/",
        rate_limit("login", *settings.LOGIN_RATE_LIMIT)(
            auth_views.LoginView.as_view(template_name="accounts/login.html")
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]
