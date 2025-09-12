from django import forms
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import Comment, Post

User = get_user_model()


class CreatePostForm(forms.ModelForm):
    pub_date = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(
            attrs={'type': 'datetime-local'},
            format='%Y-%m-%dT%H:%M',
        ),
    )

    class Meta:
        model = Post
        exclude = ('author',)


class CreateCommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)


class EditProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'Имя'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Фамилия'}),
            'email': forms.EmailInput(attrs={
                'placeholder': 'example@mail.com'
            }
            ),
        }
