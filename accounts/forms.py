from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class SignupForm(UserCreationForm):
    email = forms.EmailField(required=True)

    # Honeypot: a field real users never see or fill in (hidden off-screen
    # via CSS, not type="hidden", since some bots skip actual hidden
    # inputs but not visually-hidden ones). Any non-blank value here means
    # it was filled by a bot, so we reject the signup — see clean_website.
    website = forms.CharField(
        required=False,
        label="Leave this field blank",
        widget=forms.TextInput(attrs={"autocomplete": "off", "tabindex": "-1"}),
    )

    class Meta:
        model = User
        fields = ("username", "email")

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("website"):
            # Deliberately a non-field, generic error — don't reveal that a
            # honeypot caught it, and surface it somewhere the user (should
            # this ever false-positive on a real person) will actually see it.
            self.add_error(None, "Something went wrong. Please try again.")
        return cleaned_data

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user
