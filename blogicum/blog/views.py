from django.shortcuts import get_object_or_404, redirect
from django.views.generic import (
    ListView, DetailView, CreateView,
    UpdateView, DeleteView, FormView,
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import QuerySet, Count
from django.urls import reverse_lazy
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.paginator import Paginator

from .models import Post, Category, Comment
from .forms import CommentForm


class PostQuerySetMixin:
    """Mixin для выборки опубликованных постов с общими условиями."""

    def get_base_queryset(self) -> QuerySet:
        return (
            Post.objects.select_related("category", "location", "author")
            .filter(
                is_published=True,
                pub_date__lte=timezone.now(),
                category__is_published=True,
            )
            .annotate(comment_count=Count("comments"))
        )


class PostListView(PostQuerySetMixin, ListView):
    """Базовый список постов с пагинацией."""

    paginate_by = 10
    context_object_name = "post_list"
    template_name = "blog/index.html"

    def get_queryset(self) -> QuerySet:
        return self.get_base_queryset()


class IndexView(PostListView):
    """Главная страница блога."""


class PostDetailView(PostQuerySetMixin, DetailView):
    """Детальная страница поста с комментариями и формой."""

    model = Post
    context_object_name = "post"
    template_name = "blog/detail.html"
    pk_url_kwarg = "post_id"

    def get_queryset(self) -> QuerySet:
        return self.get_base_queryset()

    def _get_post_comments(self):
        return (
            self.object.comments
            .select_related("author")
            .order_by("created_at")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "comment_form": CommentForm(),
                "comments": self._get_post_comments(),
                "is_form_disabled": True,
            }
        )
        return context


class CategoryPostsView(PostListView):
    """Список постов конкретной категории."""

    template_name = "blog/category.html"

    def get_queryset(self) -> QuerySet:
        self.category = get_object_or_404(
            Category.objects.filter(is_published=True),
            slug=self.kwargs["category_slug"],
        )
        return super().get_queryset().filter(category=self.category)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["category"] = self.category
        return context


class ProfileView(DetailView):
    """Профиль пользователя с его постами и пагинацией."""

    model = User
    template_name = "blog/profile.html"
    context_object_name = "profile_user"
    slug_field = "username"
    slug_url_kwarg = "username"
    paginate_by = 10

    def _get_user_posts(self, user: User) -> QuerySet:
        posts = user.posts.annotate(comment_count=Count("comments"))
        if self.request.user == user:
            return posts
        return posts.filter(
            is_published=True,
            pub_date__lte=timezone.now(),
            category__is_published=True,
        )

    def _paginate_posts(self, posts: QuerySet):
        paginator = Paginator(posts, self.paginate_by)
        return paginator.get_page(self.request.GET.get("page"))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()
        posts = self._get_user_posts(user)
        page_obj = self._paginate_posts(posts)

        context.update(
            {
                "page_obj": page_obj,
                "is_owner": self.request.user == user,
            }
        )
        return context


class PostCreateView(LoginRequiredMixin, CreateView):
    """Создание нового поста."""

    model = Post
    template_name = "blog/create.html"
    fields = ["title", "text", "pub_date", "location", "category", "image"]

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            "blog:profile",
            kwargs={"username": self.request.user.username},
        )


class PostUpdateView(LoginRequiredMixin, UpdateView):
    """Редактирование существующего поста."""

    model = Post
    template_name = "blog/create.html"
    fields = ["title", "text", "pub_date", "location", "category", "image"]

    def get_queryset(self):
        return Post.objects.filter(author=self.request.user)

    def get_success_url(self):
        return reverse_lazy(
            "blog:post_detail",
            kwargs={"post_id": self.object.id},
        )


class PostDeleteView(LoginRequiredMixin, DeleteView):
    """Удаление поста автором."""

    model = Post
    template_name = "blog/create.html"
    pk_url_kwarg = "post_id"

    def get_queryset(self):
        return Post.objects.filter(author=self.request.user)

    def get_success_url(self):
        return reverse_lazy("blog:index")


class CommentUpdateView(LoginRequiredMixin, UpdateView):
    """Редактирование комментария пользователем."""

    model = Comment
    form_class = CommentForm
    template_name = "blog/detail.html"
    pk_url_kwarg = "comment_id"

    def get_queryset(self):
        return Comment.objects.filter(author=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = CommentForm
        context.update(
            {
                "form": form,
                "comment_form": form,
                "comments": self._get_post_comments(),
                "is_form_disabled": True,
            }
        )
        return context


    def get_success_url(self):
        return reverse_lazy(
            "blog:post_detail",
            kwargs={"post_id": self.object.post.id},
        )


class CommentDeleteView(LoginRequiredMixin, DeleteView):
    """Удаление комментария пользователем."""

    model = Comment
    template_name = "blog/comment.html"
    pk_url_kwarg = "comment_id"

    def get_queryset(self):
        return Comment.objects.filter(author=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "post": self.object.post,
                "comments": self.object.post.comments.select_related("author"),
                "comment_being_deleted": self.object,
                "is_delete_confirmation": True,
            }
        )
        return context

    def get_success_url(self):
        return reverse_lazy(
            "blog:post_detail",
            kwargs={"post_id": self.object.post.id},
        )


class RegistrationView(FormView):
    """Регистрация нового пользователя."""

    form_class = UserCreationForm
    template_name = "registration/registration_form.html"
    success_url = reverse_lazy("blog:index")

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return super().form_valid(form)


@login_required
def add_comment(request, post_id):
    """Добавление комментария к посту."""
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect("blog:post_detail", post_id=post_id)
    