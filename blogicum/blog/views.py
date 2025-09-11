from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import QuerySet, Count
from django.urls import reverse_lazy
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.views import View

from .models import Post, Category, Comment
from .forms import CommentForm


class PostQuerySetMixin:
    
    def get_base_queryset(self) -> QuerySet:
        return Post.objects.select_related(
            'category', 'location', 'author'
        ).filter(
            is_published=True,
            pub_date__lte=timezone.now(),
            category__is_published=True
        ).annotate(comment_count=Count('comments'))


class PostListView(PostQuerySetMixin, ListView):
    paginate_by = 10
    context_object_name = 'post_list'
    template_name = 'blog/index.html'
    
    def get_queryset(self) -> QuerySet:
        return self.get_base_queryset()


class IndexView(PostListView):
    pass


class PostDetailView(PostQuerySetMixin, DetailView):
    model = Post
    context_object_name = 'post'
    template_name = 'blog/detail.html'
    pk_url_kwarg = 'post_id'
    
    def get_queryset(self) -> QuerySet:
        return self.get_base_queryset()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CommentForm()
        context['comments'] = self.object.comments.select_related('author').order_by('created_at')
        context['disable_form'] = True
        return context



class CategoryPostsView(PostListView):
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


class ProfileView(DetailView):
    model = User
    template_name = 'blog/profile.html'
    context_object_name = 'profile_user'
    slug_field = 'username'
    slug_url_kwarg = 'username'
    paginate_by = 10
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()
        
        if self.request.user == user:
            posts = user.posts.annotate(comment_count=Count('comments'))
        else:
            posts = user.posts.filter(
                is_published=True,
                pub_date__lte=timezone.now(),
                category__is_published=True
            ).annotate(comment_count=Count('comments'))
        
        from django.core.paginator import Paginator
        paginator = Paginator(posts, self.paginate_by)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context['page_obj'] = page_obj
        context['is_owner'] = self.request.user == user
        return context


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    template_name = 'blog/create.html'
    fields = ['title', 'text', 'pub_date', 'location', 'category', 'image']
    
    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('blog:profile', kwargs={'username': self.request.user.username})


class PostUpdateView(LoginRequiredMixin, UpdateView):
    model = Post
    template_name = 'blog/create.html'
    fields = ['title', 'text', 'pub_date', 'location', 'category', 'image']
    
    def get_queryset(self):
        return Post.objects.filter(author=self.request.user)
    
    def form_valid(self, form):
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('blog:post_detail', kwargs={'post_id': self.object.id})


class PostDeleteView(LoginRequiredMixin, DeleteView):
    model = Comment
    template_name = 'blog/detail.html'
    pk_url_kwarg = 'post_id'
    
    def test_func(self, comment_id):
        comment = self.get_object()
        if self.request.user == comment.name:
            return render(request, "comment_confirm_delete.html")
        else:
            return HttpResponseRedirect(reverse('post_detail', args=[slug]))


class CommentUpdateView(LoginRequiredMixin, UpdateView):
    model = Comment
    form_class = CommentForm
    template_name = 'blog/detail.html'
    pk_url_kwarg = 'comment_id'
    
    def get_queryset(self):
        return Comment.objects.filter(author=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['post'] = self.object.post
        context['show_edit_comment'] = True
        context['editing_comment'] = self.object
        return context
    
    def get_success_url(self):
        return reverse_lazy('blog:post_detail', kwargs={'post_id': self.object.post.id})


class CommentDeleteView(LoginRequiredMixin, DeleteView):
    model = Comment
    template_name = 'blog/detail.html'
    pk_url_kwarg = 'comment_id'

    def get_queryset(self):
        return Comment.objects.filter(author=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['post'] = self.object.post
        context['show_delete_comment_confirmation'] = True
        return context

    def get_success_url(self):
        return reverse_lazy(
            'blog:post_detail',
            kwargs={'post_id': self.object.post.id}
        )



class RegistrationView(FormView):
    form_class = UserCreationForm
    template_name = 'registration/registration_form.html'
    success_url = reverse_lazy('blog:index')
    
    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return super().form_valid(form)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('blog:post_detail', post_id=post_id)