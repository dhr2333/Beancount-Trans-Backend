from django import forms

from .models import MyCmodel


class MyForm(forms.ModelForm):
    class Meta:
        model = MyCmodel
        fields = ["image"]
