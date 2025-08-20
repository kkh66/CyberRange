from django import forms
from tinymce.widgets import TinyMCE
from .models import Tutorial, Section


class SectionForm(forms.ModelForm):
    content = forms.CharField(widget=TinyMCE())

    class Meta:
        model = Section
        fields = ['title', 'content']
