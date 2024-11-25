from django import forms
from .models import Forum


class ForumForm(forms.ModelForm):
    class Meta:
        model = Forum
        fields = ["name", "description", "display_picture"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control name__input",
                    "placeholder": "Enter forum name",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control description__input",
                    "id": "description__input",
                    "rows": 4,
                    "cols": 40,
                    "placeholder": "Enter a description",
                    "maxlength": "250",  # Set the maximum number of characters
                }
            ),
            "display_picture": forms.ClearableFileInput(
                attrs={"class": "form-control", "accept": "image/*"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["display_picture"].required = False
