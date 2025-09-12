from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
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
from django.http import Http404, HttpResponseRedirect
from django.utils import timezone

from .forms import CreateCommentForm, CreatePostForm, EditProfileForm
from .models import Category, Comment, Post, User
from .mixins import AuthorRequiredMixin, get_post_queryset

PAGINATED_BY = 10


class PostDeleteView(
    AuthorRequiredMixin,
    LoginRequiredMixin,
    DeleteView
):
    """Удаление постов"""

    model = Post
    pk_url_kwarg = 'post_pk'
    template_name = 'blog/delete.html'
    success_url = reverse_lazy('blog:index')

    def get_object(self, queryset=None):
        return get_object_or_404(
            Post,
            pk=self.kwargs['post_pk']
        )


class PostUpdateView(
    AuthorRequiredMixin,
    UpdateView
):
    """Изменение постов"""

    model = Post
    pk_url_kwarg = 'post_pk'
    form_class = CreatePostForm
    template_name = 'blog/create.html'

    def get_queryset(self):
        return get_post_queryset().filter(author=self.request.user)


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    template_name = "blog/create.html"
    form_class = CreatePostForm

    def get_queryset(self):
        # тесты должны видеть все посты, без фильтров
        return Post.all_objects.all()

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("blog:profile", args=[self.request.user.username])


class PostDetailView(DetailView):
    """Детальная страница поста"""

    model = Post
    template_name = 'blog/detail.html'
    pk_url_kwarg = 'post_pk'

    def get_object(self, queryset=None):
        post = get_object_or_404(
            Post.objects.select_related('author', 'location', 'category'),
            pk=self.kwargs['post_pk']
        )

        if (
            post.author != self.request.user and (
                not post.is_published
                or not post.category.is_published
                or post.pub_date > timezone.now()
            )
        ):
            raise Http404("Пост недоступен")

        return post

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CreateCommentForm()
        context['comments'] = (
            self.object.comments
            .select_related('author')
            .all()
        )
        return context


class CommentCreateView(LoginRequiredMixin, CreateView):
    """Написание комментариев"""

    model = Comment
    form_class = CreateCommentForm

    def form_valid(self, form):
        form.instance.post = get_object_or_404(
            Post,
            pk=self.kwargs['post_pk']
        )
        form.instance.author = self.request.user
        self.object = form.save()
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse(
            'blog:post_detail',
            kwargs={'post_pk': self.kwargs['post_pk']}
        )


class CommentDeleteView(
    AuthorRequiredMixin,
    LoginRequiredMixin,
    DeleteView
):
    """Удаление комментариев"""

    model = Comment
    pk_url_kwarg = "comment_pk"
    template_name = "blog/comment.html"

    def get_object(self, queryset=None):
        return get_object_or_404(
            Comment,
            pk=self.kwargs["comment_pk"],
            post__pk=self.kwargs["post_pk"]
        )

    def get_success_url(self):
        return reverse(
            "blog:post_detail",
            kwargs={"post_pk": self.kwargs["post_pk"]}
        )


class CommentUpdateView(
    AuthorRequiredMixin,
    LoginRequiredMixin,
    UpdateView
):
    """Изменение комментариев"""

    model = Comment
    form_class = CreateCommentForm
    pk_url_kwarg = "comment_pk"
    template_name = "blog/comment.html"

    def get_object(self, queryset=None):
        return get_object_or_404(
            Comment,
            pk=self.kwargs["comment_pk"],
            post__pk=self.kwargs["post_pk"]
        )

    def get_success_url(self):
        return reverse(
            "blog:post_detail",
            kwargs={"post_pk": self.kwargs["post_pk"]}
        )


class EditProfileView(LoginRequiredMixin, UpdateView):
    """Изменение профиля"""

    model = User
    form_class = EditProfileForm
    template_name = 'blog/user.html'

    def get_object(self, queryset=None):
        return self.request.user

    def get_success_url(self):
        return reverse(
            'blog:profile',
            kwargs={'username': self.request.user.username}
        )


class AuthorProfileListView(ListView):
    model = Post
    template_name = 'blog/profile.html'
    paginate_by = PAGINATED_BY

    def get_profile_user(self):
        """Возвращает пользователя профиля или 404"""
        return get_object_or_404(User, username=self.kwargs['username'])

    def get_queryset(self):
        profile_user = self.get_profile_user()

        if self.request.user == profile_user:
            queryset = get_post_queryset(
                apply_filters=False,
                apply_annotation=True
            )
        else:
            queryset = get_post_queryset(
                apply_filters=True,
                apply_annotation=True
            )

        return queryset.filter(author=profile_user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = self.get_profile_user()
        return context


class BlogIndexListView(ListView):
    """Главная страница блога"""

    queryset = get_post_queryset(apply_filters=True, apply_annotation=True)
    template_name = 'blog/index.html'
    paginate_by = PAGINATED_BY


class BlogCategoryListView(ListView):
    """Страница категории блога"""

    template_name = 'blog/category.html'
    paginate_by = PAGINATED_BY

    def get_category(self):
        """Возвращает категорию или 404"""
        return get_object_or_404(
            Category,
            slug=self.kwargs['category_slug'],
            is_published=True
        )

    def get_queryset(self):
        category = self.get_category()
        return (
            get_post_queryset(apply_filters=True, apply_annotation=True)
            .filter(category=category)
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.get_category()
        return context


class RegistrationView(FormView):
    """Регистрация нового пользователя"""

    form_class = UserCreationForm
    template_name = 'registration/registration_form.html'

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return redirect('blog:profile', username=user.username)
