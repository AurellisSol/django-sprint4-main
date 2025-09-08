from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.generic import ListView, DetailView, CreateView, FormView, UpdateView, DeleteView
from django.db.models import QuerySet
from django.urls import reverse_lazy
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.forms import UserCreationForm
from django.db import models
from django.core.paginator import Paginator

from .forms import CommentForm
from .models import Post, Category


class PostQuerySetMixin:
    """Миксин для получения базового QuerySet публикаций"""
    
    def get_base_queryset(self) -> QuerySet:
        # Для анонимных пользователей - только опубликованные посты
        # Для авторизованных - свои посты показываются всегда
        queryset = Post.objects.select_related('category', 'location', 'author')
        
        if not self.request.user.is_authenticated:
            # Анонимные пользователи видят только опубликованные посты
            return queryset.filter(
                is_published=True,
                pub_date__lte=timezone.now(),
                category__is_published=True
            )
        else:
            # Авторизованные пользователи видят свои посты + опубликованные чужие
            return queryset.filter(
                models.Q(author=self.request.user) |
                models.Q(
                    is_published=True,
                    pub_date__lte=timezone.now(),
                    category__is_published=True
                )
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
    pass


class PostDetailView(PostQuerySetMixin, DetailView):
    """Детальное представление публикации"""
    model = Post
    context_object_name = 'post'
    template_name = 'blog/detail.html'
    pk_url_kwarg = 'post_id'

    def get_queryset(self) -> QuerySet:
        return self.get_base_queryset()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CommentForm()
        context['comments'] = self.object.comments.select_related('author')
        return context


def add_comment(request, post_id):
    """Добавление комментария"""
    post = get_object_or_404(Post, id=post_id)
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.author = request.user
            comment.post = post
            comment.save()
            messages.success(request, 'Комментарий добавлен!')
    return redirect('blog:post_detail', post_id=post_id)



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


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    template_name = 'blog/create_post.html'
    fields = ['title', 'text', 'pub_date', 'location', 'category', 'image']
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
    paginate_by = 10  # Добавляем пагинацию для профиля
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()
        
        if self.request.user == user:
            posts = user.posts.all()  # Все посты для автора
        else:
            posts = user.posts.filter(
                is_published=True,
                pub_date__lte=timezone.now(),
                category__is_published=True
            )

        paginator = Paginator(posts, self.paginate_by)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context['posts'] = page_obj
        context['is_owner'] = self.request.user == user
        return context

class AutoLoginMixin:
    """Миксин для автоматического входа после регистрации"""

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response


class RegistrationView(FormView):
    """CBV класс для регистрации с автоматическим входом (используем FormView)"""
    form_class = UserCreationForm
    template_name = 'registration/registration_form.html'
    success_url = reverse_lazy('blog:index')
    
    def form_valid(self, form):
        # Сохраняем пользователя
        user = form.save()
        # Автоматически логиним пользователя
        login(self.request, user)
        # Добавляем сообщение об успехе
        return super().form_valid(form)


class PostCreateView(LoginRequiredMixin, CreateView):
    """Создание новой публикации"""
    model = Post
    template_name = 'blog/create.html'
    fields = ['title', 'text', 'pub_date', 'location', 'category']
    
    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('blog:profile', kwargs={'username': self.request.user.username})


class PostUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Редактирование публикации"""
    model = Post
    template_name = 'blog/create.html'
    fields = ['title', 'text', 'pub_date', 'location', 'category', 'image']

    def test_func(self):
        # Только автор может редактировать пост
        post = self.get_object()
        return self.request.user == post.author

    def form_valid(self, form):
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('blog:post_detail', kwargs={'post_id': self.object.id})


class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Удаление публикации"""
    model = Post
    template_name = 'blog/create.html'

    def test_func(self):
        # Только автор может удалить пост
        post = self.get_object()
        return self.request.user == post.author

    def get_success_url(self):
        return reverse_lazy('blog:profile', kwargs={'username': self.request.user.username})


