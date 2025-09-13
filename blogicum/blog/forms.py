from blog.models import Post, Comment
from django import forms


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'text', 'pub_date', 'location', 'category', 'image']
        widgets = {'pub_date': forms.DateTimeInput(
            attrs={
                'type': 'datetime-local'
            })
        }

    def save(self, commit=True, author=None):
        instance = super().save(commit=False)
        if author:
            instance.author = author
        if commit:
            instance.save()
        return instance


class CommentForm(forms.ModelForm):

    class Meta:
        model = Comment
        fields = ['text']
