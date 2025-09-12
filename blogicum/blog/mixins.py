from .models import Comment, Post
from django.core.exceptions import PermissionDenied


class PostsQuerySetMixin:
    def get_queryset(self):
        return Post.post_list


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
        raise PermissionDenied
