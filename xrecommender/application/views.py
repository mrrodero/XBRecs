from django.views import generic
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from haystack import generic_views
from haystack.query import SearchQuerySet

from .models import Book, Rating
from .forms import SignUpForm
from .recommend import recommend_books
from .xai import (
    xai_explanation_dict,
    sort_rec_books_by_keyword_count,
    pyvis_graph_html
)


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


class BookSearchView(LoginRequiredMixin, generic_views.SearchView):
    """Vista basada en clase para la búsqueda de libros."""

    template_name = 'search/results.html'
    form_class = generic_views.ModelSearchForm
    context_object_name = 'book_results'

    def get_queryset(self):
        """
        Override del método get_queryset para obtener los resultados de
        la búsqueda

        Author: Álvaro Rodero
        """
        query = self.request.GET.get('q', '')
        if query:
            return SearchQuerySet().auto_query(query)
        return SearchQuerySet().all()


class DiscoverView(LoginRequiredMixin, generic.TemplateView):
    """Vista basada en clase para descubrir libros."""

    template_name = 'recommender/discover.html'

    def get_context_data(self, **kwargs):
        """
        Override del método get_context_data para añadir el contexto

        Author: Álvaro Rodero
        """
        context = super().get_context_data(**kwargs)
        context['books'] = Book.objects.all()
        return context


@require_POST
def book_rate(request, book_id):
    """
    Vista para calificar un libro.

    ## Argumentos:
    - `request`: Petición HTTP.
    - `book_id`: ID del libro.

    ## Retorna:
    - `JsonResponse`: Respuesta JSON.
    """
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        rating_value = int(request.POST.get('rating'))
        book = get_object_or_404(Book, id=book_id)
        user = request.user

        rating_value = float((rating_value - 1) / 4)

        # Comprobar si el usuario ya ha valorado el libro
        try:
            rating = Rating.objects.get(user=user, book=book)
        except Rating.DoesNotExist:
            rating = Rating(user=user, book=book)

        # Actualizar la valoración
        rating.rating = rating_value
        rating.save()

        return JsonResponse({'message': 'Valoración guardadada.'})

    return JsonResponse({'error': 'Invalid request.'}, status=400)


@require_POST
def book_rate_remove(request, book_id):
    """
    Vista para eliminar la calificación de un libro.

    ## Argumentos:
    - `request`: Petición HTTP.
    - `book_id`: ID del libro.

    ## Retorna:
    - `JsonResponse`: Respuesta JSON.
    """
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        book = get_object_or_404(Book, id=book_id)
        user = request.user

        # Comprobar si existe la valoración y eliminarla
        try:
            rating = Rating.objects.get(user=user, book=book)
            rating.delete()
        except Rating.DoesNotExist:
            return JsonResponse(
                {'error': 'No se ha encontrado la valoración.'}
            )

        return JsonResponse({'message': 'Valoración eliminada.'})

    return JsonResponse({'error': 'Invalid request.'}, status=400)


class BookDetailView(LoginRequiredMixin, generic.DetailView):
    """Vista basada en clase para mostrar el detalle de un libro."""

    model = Book
    template_name = 'recommender/book-detail.html'
    pk_url_kwarg = 'book_id'

    def get_context_data(self, **kwargs):
        """
        Override del método get_context_data para añadir el contexto

        Author: Álvaro Rodero
        """
        context = super().get_context_data(**kwargs)
        book = self.get_object()
        context['book'] = book
        # Número de estrellas dada al libro por el usuario
        user = self.request.user
        # Comprobar si el usuario ha valorado el libro
        context['user_rating'] = 0
        try:
            rating = Rating.objects.get(user=user, book=book)
            context['user_rating'] = int(rating.rating * 4 + 1)
        except Rating.DoesNotExist:
            pass
        return context


class ProfileView(LoginRequiredMixin, generic.TemplateView):
    """Vista basada en clase para mostrar el perfil de usuario."""

    template_name = 'registration/user-profile.html'

    def get_context_data(self, **kwargs):
        """
        Override del método get_context_data para añadir el contexto

        Author: Álvaro Rodero
        """
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['books'] = user.get_read_books()
        # Obtener las valoraciones de cada libro
        context['user_ratings'] = {}
        for book in context['books']:
            rating = Rating.objects.get(user=user, book=book)
            context['user_ratings'][book.id] = int(rating.rating * 4 + 1)
        return context


class RecommendView(LoginRequiredMixin, generic.TemplateView):
    """Vista basada en clase para mostrar las recomendaciones."""

    template_name = 'recommender/recommend.html'

    def get_context_data(self, **kwargs):
        """
        Override del método get_context_data para añadir el contexto

        Author: Álvaro Rodero
        """
        context = super().get_context_data(**kwargs)
        user = self.request.user
        # Obtener parámetro count de la petición
        count = self.kwargs.get('count', 5)
        try:
            count = int(count)
        except ValueError:
            count = 5
        # Mostrar recomendaciones
        rec_books = [b for b, _ in recommend_books(user, k=count)]
        explain_info_dict = xai_explanation_dict(user, rec_books)
        sorted_rec_books = sort_rec_books_by_keyword_count(
            explain_info_dict, rec_books
        )
        context['rec_books'] = sorted_rec_books
        context['net_html'] = pyvis_graph_html(
            user, sorted_rec_books, explain_info_dict
        )
        return context
