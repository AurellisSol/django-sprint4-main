from django.contrib import admin
from django.urls import path, include
from django.views.generic.edit import CreateView

from blog.views import AutoLoginMixin


class RegistrationView(AutoLoginMixin, CreateView):
    pass


handler403 = 'pages.views.csrf_failure'
handler404 = 'pages.views.page_not_found'
handler500 = 'pages.views.server_error'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('django.contrib.auth.urls')),
    path('', include('blog.urls')),
    path('pages/', include('pages.urls')),
    path('auth/registration/', RegistrationView.as_view(), name='registration'),
]
