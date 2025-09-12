from django.shortcuts import render
from django.views.generic import TemplateView



class AboutPageView(TemplateView):
    template_name = "pages/about.html"


class RulesPageView(TemplateView):
    template_name = "pages/rules.html"


def csrf_failure(request, reason="", template_name="403_csrf.html", exception=None):
    return render(request, template_name, {"reason": reason})


def page_not_found(request, exception):
    return render(request, 'pages/404.html', status=404)


def server_error(request):
    return render(request, 'pages/500.html', status=500)
