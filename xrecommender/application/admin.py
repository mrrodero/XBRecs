from django.contrib import admin
# from django.contrib.auth.admin import UserAdmin

from .models import Keyword, Author, Book, User, Rating

# Registro de los modelos en el panel de administración
# admin.site.register(UserAdmin)
admin.site.register(Keyword)
admin.site.register(Author)
admin.site.register(Book)
admin.site.register(User)
admin.site.register(Rating)
