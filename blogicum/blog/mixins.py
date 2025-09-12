from .models import Comment, Post
from django.shortcuts import redirect


class PostsQuerySetMixin:
    def get_queryset(self):
        return Post.objects.select_related("author", "location", "category")


class PostsEditMixin:
    model = Post
    template_name = "blog/create.html"
    queryset = Post.objects.select_related("author", "location", "category")


class CommentEditMixin:
    model = Comment
    pk_url_kwarg = "comment_pk"
    template_name = "blog/comment.html"


class AuthorOrStaffRequiredMixin:
    """Доступ разрешён только автору или админу."""
    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if request.user == obj.author or request.user.is_staff:
            return super().dispatch(request, *args, **kwargs)
        return redirect("blog:post_detail", pk=obj.pk)

