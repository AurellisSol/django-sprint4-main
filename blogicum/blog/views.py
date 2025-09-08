from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.generic import ListView, DetailView, CreateView
from django.db.models import QuerySet
from django.urls import reverse_lazy
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import Post, Category


class PostQuerySetMixin:
    """Миксин для получения базового QuerySet публикаций"""

    def get_base_queryset(self) -> QuerySet:
        return Post.objects.select_related(
            'category', 'location', 'author'
        ).filter(
            is_published=True,
            pub_date__lte=timezone.now(),
            category__is_published=True
        )


class PostListView(PostQuerySetMixin, ListView):
    """Базовый класс для списка публикаций"""
    paginate_by = 5
    context_object_name = 'post_list'
    template_name = 'blog/index.html'

    def get_queryset(self) -> QuerySet:
        return self.get_base_queryset()


class IndexView(PostListView):
    """Главная страница блога"""

    def get_queryset(self) -> QuerySet:
        return super().get_queryset()[:self.paginate_by]


class PostDetailView(PostQuerySetMixin, DetailView):
    """Детальное представление публикации"""
    model = Post
    context_object_name = 'post'
    template_name = 'blog/detail.html'
    pk_url_kwarg = 'post_id'

    def get_queryset(self) -> QuerySet:
        return self.get_base_queryset()


class CategoryPostsView(PostListView):
    """Список публикаций категории"""
    template_name = 'blog/category.html'

    def get_queryset(self) -> QuerySet:
        category_slug = self.kwargs['category_slug']
        self.category = get_object_or_404(
            Category.objects.filter(is_published=True),
            slug=category_slug
        )
        return super().get_queryset().filter(category=self.category)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        return context


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    template_name = 'blog/create_post.html'
    fields = ['title', 'text', 'pub_date', 'location', 'category']
    success_url = reverse_lazy('blog:index')

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)


class ProfileView(DetailView):
    model = User
    template_name = 'blog/profile.html'
    context_object_name = 'profile_user'
    slug_field = 'username'
    slug_url_kwarg = 'username'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()
        # Добавьте логику для получения постов пользователя, если нужно
        # context['posts'] = user.posts.all()
        context['is_owner'] = self.request.user == user
        return context
    

class AutoLoginMixin:
    """Миксин для автоматического входа после регистрации"""
    
    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response
