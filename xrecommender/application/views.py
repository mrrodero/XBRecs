"""
Vistas de la aplicación XBRecs.
"""

import logging

from django.contrib.auth import authenticate, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import generic
from django.views.decorators.http import require_POST

from .forms import SignUpForm
from .models import Book, Rating
from .recommend import recompute_recommendations
from .xai import (
    get_explanation,
    pyvis_graph_html,
    sort_rec_books_by_keyword_count,
    xai_explanation_dict,
)

logger = logging.getLogger(__name__)

PAGE_SIZE = 20


class HomeView(generic.TemplateView):
    """Vista basada en clase para la página principal."""

    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context["user"] = self.request.user
        return context


class SignupView(generic.CreateView):
    """Vista basada en clase para el registro de usuarios."""

    form_class = SignUpForm
    template_name = "registration/signup.html"

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        return render(request, self.template_name, {"form": form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get("username")
            raw_password = form.cleaned_data.get("password1")
            user = authenticate(username=username, password=raw_password)
            login(request, user)
            return redirect("home")
        return render(request, self.template_name, {"form": form})


class BookSearchView(LoginRequiredMixin, generic.ListView):
    """
    Vista basada en clase para la búsqueda de libros.

    Usa la búsqueda de texto completo de PostgreSQL (tsvector + GIN)
    en lugar de Whoosh/haystack.
    """

    template_name = "search/results.html"
    context_object_name = "results"
    paginate_by = PAGE_SIZE

    def get_queryset(self):
        query = self.request.GET.get("q", "").strip()
        if not query:
            return Book.objects.none()
        return Book.objects.search(query)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = self.request.GET.get("q", "").strip()
        return context


class DiscoverView(LoginRequiredMixin, generic.ListView):
    """Vista basada en clase para descubrir libros (paginada)."""

    template_name = "recommender/discover.html"
    context_object_name = "books"
    paginate_by = PAGE_SIZE

    def get_queryset(self):
        return (
            Book.objects.prefetch_related("authors", "keywords")
        )


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
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        return JsonResponse({"error": "Invalid request."}, status=400)
    if not request.user.is_authenticated:
        return JsonResponse({"error": "No autenticado."}, status=401)

    try:
        # El formulario envía estrellas (1-5); se convierte a 0.0-1.0.
        rating_value = float((int(request.POST.get("rating")) - 1) / 4)
    except (TypeError, ValueError):
        return JsonResponse(
            {"error": "Valoración inválida (debe ser de 1 a 5)."},
            status=400,
        )
    if not 0.0 <= rating_value <= 1.0:
        return JsonResponse(
            {"error": "Valoración inválida (debe ser de 1 a 5)."},
            status=400,
        )

    book = get_object_or_404(Book, pk=book_id)
    user = request.user
    with transaction.atomic():
        Rating.objects.update_or_create(
            user=user, book=book, defaults={"rating": rating_value}
        )
    return JsonResponse({"message": "Valoración guardada."})


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
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        return JsonResponse({"error": "Invalid request."}, status=400)
    if not request.user.is_authenticated:
        return JsonResponse({"error": "No autenticado."}, status=401)

    book = get_object_or_404(Book, pk=book_id)
    user = request.user
    deleted, _ = Rating.objects.filter(user=user, book=book).delete()
    if not deleted:
        return JsonResponse(
            {"error": "No se ha encontrado la valoración."}, status=404
        )
    return JsonResponse({"message": "Valoración eliminada."})


class BookDetailView(LoginRequiredMixin, generic.DetailView):
    """Vista basada en clase para mostrar el detalle de un libro."""

    model = Book
    template_name = "recommender/book-detail.html"
    pk_url_kwarg = "book_id"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        book = self.get_object()
        context["book"] = book
        # Número de estrellas dada al libro por el usuario (0-5).
        user = self.request.user
        rating = book.ratings.filter(user=user).first()
        context["user_rating"] = (
            int(rating.rating * 4 + 1) if rating is not None else 0
        )
        return context


class ProfileView(LoginRequiredMixin, generic.TemplateView):
    """Vista basada en clase para mostrar el perfil de usuario."""

    template_name = "registration/user-profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["books"] = user.get_read_books().prefetch_related("authors")
        # Obtener las valoraciones de cada libro (una sola consulta).
        ratings = {
            r.book_id: int(r.rating * 4 + 1)
            for r in user.ratings.select_related("book").iterator()
        }
        context["user_ratings"] = ratings
        return context


class RecommendView(LoginRequiredMixin, generic.TemplateView):
    """
    Vista basada en clase para mostrar las recomendaciones.

    Las recomendaciones se sirven de la tabla `Recommendation`
    (precalculada y actualizada con cada cambio de valoración). Si el
    usuario aún no tiene recomendaciones, se generan al vuelo con la
    estrategia de cold start.
    """

    template_name = "recommender/recommend.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Obtener parámetro count de la petición
        count = self.kwargs.get("count", 10)
        try:
            count = max(1, min(int(count), 50))
        except (TypeError, ValueError):
            count = 10

        recs = list(
            user.recommendations.select_related("book")
            .prefetch_related("book__keywords")[:count]
        )
        if not recs:
            # Cold start: recomendar al vuelo y persistir.
            recompute_recommendations(user, k=count)
            recs = list(
                user.recommendations.select_related("book")
                .prefetch_related("book__keywords")[:count]
            )

        rec_books = [rec.book for rec in recs]
        explain_info_dict = xai_explanation_dict(user, rec_books)
        sorted_rec_books = sort_rec_books_by_keyword_count(
            explain_info_dict, rec_books
        )
        context["rec_items"] = [
            {
                "book": book,
                "explanation": get_explanation(user, book),
            }
            for book in sorted_rec_books
        ]
        context["net_html"] = pyvis_graph_html(
            user, sorted_rec_books, explain_info_dict
        )
        return context
