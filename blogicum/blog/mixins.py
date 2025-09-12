from django.shortcuts import redirect
from django.db.models import Count
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import Post


def get_post_queryset(apply_filters=False, apply_annotation=False):
    queryset = Post.objects.select_related('author', 'location', 'category')
    if apply_filters:
        queryset = queryset.filter(
            is_published=True,
            category__is_published=True,
            pub_date__lte=timezone.now(),
        )
    if apply_annotation:
        queryset = queryset.annotate(comment_count=Count('comments')).order_by('-pub_date')
    return queryset


class AuthorRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        post = self.get_object()
        if not request.user.is_authenticated:
            # если пользователь не авторизован — редиректим на сам пост
            return redirect("blog:post_detail", pk=post.pk)
        if post.author != request.user:
            # если автор не совпадает — тоже редиректим на пост
            return redirect("blog:post_detail", pk=post.pk)
        return super().dispatch(request, *args, **kwargs)

