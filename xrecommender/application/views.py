from django.views import generic
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate

from .forms import SignUpForm
from .recommend import recommend_books
from .xai import pyvis_graph_html


class HomeView(generic.TemplateView):
    """Vista basada en clase para la página principal."""

    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        """
        Override del método get_context_data para añadir el contexto

        Author: Álvaro Rodero
        """
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            # Mostrar últimos 5 libros añadidos
            context['user'] = self.request.user
        return context


class SignupView(generic.CreateView):
    """Vista basada en clase para el registro de usuarios."""

    form_class = SignUpForm
    template_name = 'registration/signup.html'

    def get(self, request, *args, **kwargs):
        """
        Override del método get para mostrar el formulario de registro

        ## Argumentos:
        - `request`: Petición HTTP.
        """
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        """
        Override del método post para registrar al usuario

        ## Argumentos:
        - `request`: Petición HTTP.
        """
        form = self.form_class(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=raw_password)
            login(request, user)
            return redirect('home')
        return render(request, self.template_name, {'form': form})


class RecommendView(generic.TemplateView):
    """Vista basada en clase para mostrar las recomendaciones."""

    template_name = 'recommender/recommend.html'

    def get_context_data(self, **kwargs):
        """
        Override del método get_context_data para añadir el contexto

        Author: Álvaro Rodero
        """
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if user.is_authenticated:
            # Mostrar recomendaciones
            rec_books = [b for b, _ in recommend_books(user)]
            context['net_html'] = pyvis_graph_html(user, rec_books)
        return context
