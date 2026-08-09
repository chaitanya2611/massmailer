from django import forms

from .models import Campaign


class CampaignCreateForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = ["name", "template", "data_file", "sending_account", "email_column"]
        widgets = {
            "email_column": forms.TextInput(attrs={"list": "email-column-options", "id": "id_email_column"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["template"].queryset = user.templates.all()
        self.fields["data_file"].queryset = user.data_files.all()
        self.fields["sending_account"].queryset = user.sending_accounts.filter(status="active")
        self.fields["sending_account"].required = True
