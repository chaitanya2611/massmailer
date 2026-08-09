from django import forms

from .models import DataFile


class DataFileUploadForm(forms.ModelForm):
    class Meta:
        model = DataFile
        fields = ["file"]
        widgets = {"file": forms.ClearableFileInput(attrs={"accept": ".csv,.xlsx,.xls"})}
