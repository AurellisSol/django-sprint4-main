from django.urls import path
from . import views

app_name = 'pages'

handler403 = views.csrf_failure
handler404 = views.page_not_found
handler500 = views.server_error

urlpatterns = [
    path("about/", views.AboutPageView.as_view(), name="about"),
    path("rules/", views.RulesPageView.as_view(), name="rules"),
]
