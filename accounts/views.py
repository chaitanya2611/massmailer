from django.conf import settings
from django.contrib.auth import login
from django.shortcuts import redirect, render

from core.ratelimit import rate_limit

from .forms import SignupForm


@rate_limit("signup", *settings.SIGNUP_RATE_LIMIT)
def signup(request):
    if request.user.is_authenticated:
        return redirect("campaigns:dashboard")

    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("campaigns:dashboard")
    else:
        form = SignupForm()

    return render(request, "accounts/signup.html", {"form": form})
