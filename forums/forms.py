from django import forms
from .models import Forum, Post, Comment
from django.core.exceptions import ValidationError
import os


class ForumForm(forms.ModelForm):
    class Meta:
        model = Forum
        fields = ["name", "description", "display_picture"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "topic__title",
                    "id": "topic__title",
                    "placeholder": "Enter forum name *",
                    "maxlength": "50",
                    "required": True,
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "topic__content",
                    "id": "description__input",
                    "rows": 6,
                    "cols": 40,
                    "placeholder": "Enter a description *",
                    "maxlength": "250",
                    "required": True,
                }
            ),
            "display_picture": forms.ClearableFileInput(
                attrs={"class": "form-control", "accept": "image/*"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["display_picture"].required = False


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ["title", "content", "image", "video"]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "topic__title",
                    "id": "topic__title",
                    "placeholder": "Enter a title for your topic...",
                    "maxlength": 200,
                }
            ),
            "content": forms.Textarea(
                attrs={
                    "class": "topic__content",
                    "id": "topic__content",
                    "placeholder": "Write something interesting...",
                    "rows": 6,
                }
            ),
            "image": forms.ClearableFileInput(
                attrs={
                    "class": "topic__image",
                    "id": "topic__image",
                    "accept": "image/*",
                }
            ),
            "video": forms.ClearableFileInput(
                attrs={
                    "class": "topic__video",
                    "id": "topic__video",
                     "accept": "video/mp4, video/avi, video/mov, video/mkv, video/webm",
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        content = cleaned_data.get("content")
        image = cleaned_data.get("image")
        video = cleaned_data.get("video")

        if not content and not image and not video:
            raise ValidationError("A post must have content, an image, or a video.")
        if image and video:
            raise ValidationError("A post cannot have both an image and a video.")

        return cleaned_data

    def clean_video(self):
        video = self.cleaned_data.get("video")
        if video:
            max_size_mb = 10
            if video.size > max_size_mb * 1024 * 1024:
                raise ValidationError(f"Video file size must not exceed {max_size_mb}MB.")
            
            valid_extensions = ['mp4', 'mov', 'avi', 'mkv']
            ext = os.path.splitext(video.name)[1][1:].lower()
            if ext == "webm":
                raise ValidationError("WebM files are not supported. Please upload a different format.")
            
            if ext not in valid_extensions:
                raise ValidationError(
                    f"Unsupported file extension. Allowed extensions: {', '.join(valid_extensions)}"
                )
        return video



class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["content"]
    content = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'comment__input',
            'rows': 2,
            'placeholder': 'Write your comment here...'
        })
    )