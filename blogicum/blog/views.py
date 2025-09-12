from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.db.models import Count
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
    FormView,
)
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.utils import timezone


from .forms import CreateCommentForm, CreatePostForm
from .models import Category, Comment, Post, User
from .mixins import (
    CommentEditMixin, PostsEditMixin,
    PostsQuerySetMixin, AuthorOrStaffRequiredMixin
)

PAGINATED_BY = 10


class PostDeleteView(
    PostsEditMixin,
    LoginRequiredMixin,
    AuthorOrStaffRequiredMixin,
    DeleteView
):
    """Удаление постов"""

    success_url = reverse_lazy('blog:index')


class PostUpdateView(
    PostsEditMixin,
    LoginRequiredMixin,
    AuthorOrStaffRequiredMixin,
    UpdateView
):
    """Изменение постов"""

    form_class = CreatePostForm

    def dispatch(self, request, *args, **kwargs):
        post = get_object_or_404(Post, pk=self.kwargs['pk'])
        if self.request.user != post.author:
            return redirect('blog:post_detail', pk=self.kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)


class PostCreateView(LoginRequiredMixin, CreateView):
    """создание постов"""

    model = Post
    form_class = CreatePostForm
    template_name = 'blog/create.html'

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        # после создания — редирект в профиль автора
        return reverse(
            'blog:profile',
            kwargs={'username': self.request.user.username},
        )


class CommentCreateView(LoginRequiredMixin, CreateView):
    """Написание комментариев"""

    model = Comment
    form_class = CreateCommentForm

    def form_valid(self, form):
        form.instance.post = get_object_or_404(Post, pk=self.kwargs['pk'])
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('blog:post_detail', kwargs={'pk': self.kwargs['pk']})


class CommentDeleteView(
    CommentEditMixin,
    LoginRequiredMixin,
    AuthorOrStaffRequiredMixin,
    DeleteView
):
    """Удаление комментариев"""

    def get_success_url(self):
        return reverse('blog:post_detail', kwargs={'pk': self.kwargs['pk']})

    def delete(self, request, *args, **kwargs):
        comment = get_object_or_404(Comment, pk=self.kwargs['comment_pk'])
        if self.request.user != comment.author:
            return redirect('blog:post_detail', pk=self.kwargs['pk'])
        return super().delete(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.pop('form', None)
        return context


class CommentUpdateView(
    CommentEditMixin,
    LoginRequiredMixin,
    AuthorOrStaffRequiredMixin,
    UpdateView
):
    """Изменение комментариев"""

    form_class = CreateCommentForm

    def dispatch(self, request, *args, **kwargs):
        # безопасно получаем комментарий, иначе сразу 404
        comment = get_object_or_404(Comment, pk=self.kwargs['comment_pk'])
        if request.user != comment.author and not request.user.is_staff:
            return redirect('blog:post_detail', pk=self.kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('blog:post_detail', kwargs={'pk': self.kwargs['pk']})


class EditProfileView(LoginRequiredMixin, UpdateView):
    """Изменение профиля"""

    model = User
    fields = ['first_name', 'last_name', 'email']
    template_name = 'blog/user.html'
    success_url = reverse_lazy('index')

    def get_object(self, queryset=None):
        return self.request.user

    def get_success_url(self):
        return reverse(
            'blog:profile',
            kwargs={'username': self.request.user.username}
        )


class AuthorProfileListView(PostsQuerySetMixin, ListView):
    model = Post
    template_name = 'blog/profile.html'
    paginate_by = PAGINATED_BY

    def get_queryset(self):
        if self.request.user.username == self.kwargs['username']:
            return (
                self.request.user.posts.select_related(
                    'category',
                    'author',
                    'location',
                )
                .all()
                .annotate(comment_count=Count('comments'))
                .order_by('-pub_date')
            )

        return (
            super()
            .get_queryset()
            .filter(author__username=self.kwargs['username'])
            .annotate(comment_count=Count('comments'))
            .order_by('-pub_date')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = get_object_or_404(
            User, username=self.kwargs['username']
        )
        return context


class BlogIndexListView(PostsQuerySetMixin, ListView):
    """Главная страница блога"""

    model = Post
    template_name = 'blog/index.html'
    context_object_name = 'post_list'
    paginate_by = PAGINATED_BY

    def get_queryset(self):
        return (super().get_queryset().filter(
            is_published=True,
            pub_date__lte=timezone.now(),
            category__is_published=True
        ).annotate(
            comment_count=Count('comments')).order_by('-pub_date')
        )


class BlogCategoryListView(PostsQuerySetMixin, ListView):
    """Страница категории блога"""

    model = Post
    template_name = 'blog/category.html'
    context_object_name = 'post_list'
    paginate_by = PAGINATED_BY

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = get_object_or_404(
            Category, slug=self.kwargs['category_slug'], is_published=True
        )
        return context

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(
                category__slug=self.kwargs['category_slug'],
                is_published=True,
                pub_date__lte=timezone.now(),
                category__is_published=True
            )
            .annotate(comment_count=Count('comments'))
            .order_by('-pub_date')
        )


class PostDetailView(PostsQuerySetMixin, DetailView):
    """Детальная страница поста"""

    model = Post
    template_name = 'blog/detail.html'

    def get_queryset(self):
        queryset = super().get_queryset().prefetch_related('comments')
        if self.request.user.is_authenticated:
            return queryset.filter(author=self.request.user) | queryset.filter(
                is_published=True,
                pub_date__lte=timezone.now()
            )
        return queryset.filter(
            is_published=True,
            pub_date__lte=timezone.now()
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CreateCommentForm()
        context['comments'] = (
            self.get_object().comments.select_related('author').all()
        )
        return context


class RegistrationView(FormView):
    """Регистрация нового пользователя"""

    form_class = UserCreationForm
    template_name = 'registration/registration_form.html'

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return redirect('blog:profile', username=user.username)
