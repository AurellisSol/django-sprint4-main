from django.shortcuts import redirect
from django.db.models import Count
from django.utils import timezone

from .models import Post


def get_post_queryset(apply_filters=False, apply_annotation=False):
    """Базовый запрос для модели Post."""
    queryset = Post.objects.select_related(
        'author', 'location', 'category'
    )

    if apply_filters:
        queryset = queryset.filter(
            is_published=True,
            pub_date__lte=timezone.now(),
            category__is_published=True
        )

    if apply_annotation:
        queryset = queryset.annotate(
            comment_count=Count('comments')
        ).order_by('-pub_date')

    return queryset


class AuthorOrStaffRequiredMixin:
    """Доступ разрешён только автору или админу."""

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if request.user == obj.author:
            return super().dispatch(request, *args, **kwargs)
        return redirect('blog:post_detail', post_pk=kwargs.get('post_pk'))
