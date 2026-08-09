from django import forms

from .models import EmailTemplate


class EmailTemplateForm(forms.ModelForm):
    class Meta:
        model = EmailTemplate
        fields = ["name", "subject", "body", "is_html"]
        widgets = {
            "subject": forms.TextInput(attrs={"id": "id_subject"}),
            "body": forms.Textarea(attrs={"id": "id_body", "rows": 14}),
        }
