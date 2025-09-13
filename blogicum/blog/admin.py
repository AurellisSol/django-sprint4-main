from django.contrib import admin
from .models import Post, Category, Location

# Register your models here.
admin.site.register([Post, Category, Location])
