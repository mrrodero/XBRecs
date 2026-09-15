"""
Recomendador user-user basado en embeddings SBERT.

La similitud entre usuarios se calcula con búsqueda ANN
(approximate nearest neighbors) sobre PostgreSQL + pgvector, en lugar de
cargar todos los embeddings en memoria.

Además de las recomendaciones colaborativas, se incluyen estrategias de
"cold start" para usuarios con pocas valoraciones (basadas en contenido
y popularidad), y las recomendaciones se precálculan y persisten en la
tabla `Recommendation` para que la vista no tenga que ejecutar el modelo
en cada petición.
"""

import logging

import numpy as np
from django.db import models, transaction
from pgvector.django import CosineDistance

from .models import LIKES, Book, Rating, Recommendation, User

logger = logging.getLogger(__name__)

# Valoraciones mínimas para usar el modelo colaborativo; por debajo se
# usa el cold start (contenido + popularidad).
MIN_RATINGS_FOR_CF = 3
# Número de vecinos y de recomendaciones precalculadas por defecto.
DEFAULT_NEIGHBORS = 35
DEFAULT_RECOMMENDATIONS = 15


def k_nearest(user: User, k: int) -> list[tuple[User, float]]:
    """
    Obtiene los k usuarios más similares al usuario dado (coseno).

    ## Argumentos:
    - `user`: Usuario de referencia.
    - `k`: Número de vecinos.

    ## Retorno:
    - Lista de tuplas `(usuario, similitud)` ordenada por similitud
      descendente.
    """
    vec = user.get_embedding().astype(np.float32)
    if not np.any(vec):
        return []
    qs = (
        User.objects
        .exclude(pk=user.pk)
        .exclude(embedding__isnull=True)
        .annotate(similarity=1.0 - CosineDistance("embedding", vec))
        .order_by("-similarity")[:k]
    )
    return [(u, float(u.similarity)) for u in qs]


def top_k_books(
    user: User, nearest_users: list[tuple[User, float]], k: int
) -> list[tuple[Book, float]]:
    """
    Predice las mejores valoraciones de libros no valorados por el
    usuario, ponderando por la similitud con los usuarios vecinos.

    ## Argumentos:
    - `user`: Usuario al que se recomienda.
    - `nearest_users`: Vecinos `(usuario, similitud)`.
    - `k`: Número de libros a devolver.

    ## Retorno:
    - Lista de tuplas `(libro, puntuación)` ordenada por puntuación
      descendente.
    """
    if not nearest_users:
        return []
    sim_by_user = {u.pk: s for u, s in nearest_users}
    rated_book_ids = set(
        Rating.objects.filter(user=user).values_list("book_id", flat=True)
    )
    ratings = (
        Rating.objects
        .filter(user__in=[u.pk for u, _ in nearest_users], rating__gte=LIKES)
        .exclude(book_id__in=rated_book_ids)
        .iterator()
    )
    book_score: dict[int, float] = {}
    for rating in ratings:
        book_score[rating.book_id] = (
            book_score.get(rating.book_id, 0.0)
            + rating.rating * sim_by_user[rating.user_id]
        )
    top = sorted(book_score.items(), key=lambda item: item[1], reverse=True)[:k]
    if not top:
        return []
    books = {
        b.pk: b for b in Book.objects.filter(pk__in=[bid for bid, _ in top])
    }
    return [(books[bid], score) for bid, score in top if bid in books]


def recommend_books(
    user: User, n: int = DEFAULT_NEIGHBORS, k: int = 5
) -> list[tuple[Book, float]]:
    """
    Recomienda k libros al usuario usando los n usuarios más similares.

    ## Argumentos:
    - `user`: Usuario al que se recomienda.
    - `n`: Número de vecinos a considerar.
    - `k`: Número de libros a devolver.

    ## Retorno:
    - Lista de tuplas `(libro, puntuación)`.
    """
    nearest = k_nearest(user, n)
    return top_k_books(user, nearest, k)


def popular_books(k: int = DEFAULT_RECOMMENDATIONS) -> list[tuple[Book, float]]:
    """
    Libros más populares (más valoraciones, desempate por media).

    ## Argumentos:
    - `k`: Número de libros a devolver.

    ## Retorno:
    - Lista de tuplas `(libro, número de valoraciones)`.
    """
    books = (
        Book.objects
        .annotate(
            n_ratings=models.Count("ratings"),
            avg_rating=models.Avg("ratings__rating"),
        )
        .filter(n_ratings__gte=10)
        .order_by("-n_ratings", "-avg_rating")[:k]
    )
    return [(b, float(b.n_ratings)) for b in books]


def cold_start_recommendations(
    user: User, k: int = DEFAULT_RECOMMENDATIONS
) -> list[tuple[Book, float]]:
    """
    Recomendaciones para usuarios con pocas valoraciones.

    1. Basadas en contenido: libros que comparten palabras clave con los
       libros que le gustan al usuario.
    2. Si no tiene libros que le gusten, libros populares.

    ## Argumentos:
    - `user`: Usuario al que se recomienda.
    - `k`: Número de libros a devolver.

    ## Retorno:
    - Lista de tuplas `(libro, puntuación)`.
    """
    liked_books = user.get_liked_books()
    if liked_books.exists():
        liked_ids = list(liked_books.values_list("id", flat=True))
        rated_ids = set(
            Rating.objects.filter(user=user).values_list("book_id", flat=True)
        )
        liked_kw_ids = list(
            Book.objects.filter(id__in=liked_ids)
            .values_list("keywords__id", flat=True)
            .distinct()
        )
        if liked_kw_ids:
            candidates = (
                Book.objects
                .filter(keywords__in=liked_kw_ids)
                .exclude(id__in=liked_ids)
                .exclude(id__in=rated_ids)
                .annotate(
                    shared=models.Count(
                        "keywords", filter=models.Q(keywords__id__in=liked_kw_ids)
                    )
                )
                .order_by("-shared")[:k]
            )
            if candidates:
                return [(b, float(b.shared)) for b in candidates]
    return popular_books(k)


def recompute_recommendations(
    user: User,
    n: int = DEFAULT_NEIGHBORS,
    k: int = DEFAULT_RECOMMENDATIONS,
) -> None:
    """
    Recalcula y persiste las recomendaciones de un usuario.

    Se invoca tras cada cambio de valoración (señales de `Rating`) y
    desde el comando `recompute_recommendations`.

    ## Argumentos:
    - `user`: Usuario cuyas recomendaciones se recalculan.
    - `n`: Número de vecinos para el modelo colaborativo.
    - `k`: Número de recomendaciones a persistir.
    """
    if user.ratings.count() >= MIN_RATINGS_FOR_CF:
        recs = recommend_books(user, n=n, k=k)
    else:
        recs = []
    if not recs:
        # Sin valoraciones suficientes o sin vecinos útiles: cold start.
        recs = cold_start_recommendations(user, k=k)
    with transaction.atomic():
        Recommendation.objects.filter(user=user).delete()
        Recommendation.objects.bulk_create(
            [
                Recommendation(user=user, book=book, score=score)
                for book, score in recs
            ]
        )
