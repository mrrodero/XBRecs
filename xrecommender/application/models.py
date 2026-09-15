"""
Modelos de la aplicación XBRecs.

Los embeddings (768 dimensiones, SBERT) se almacenan con pgvector
(`VectorField`) en lugar de blobs binarios picklados, lo que permite
búsquedas ANN (approximate nearest neighbors) directamente en
PostgreSQL.

Las señales de `Rating` recalculan el estado del usuario (suma de
valoraciones y embedding) sin estado global compartido, evitando la
condición de carrera del código anterior.
"""

import logging

import numpy as np
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver
from pgvector.django import VectorField

logger = logging.getLogger(__name__)

# Umbral de valoración a partir del cual un libro "gusta" al usuario.
LIKES = 0.75
# Dimensionalidad de los embeddings SBERT.
EMBEDDING_DIM = 768


class Keyword(models.Model):
    """Modelo para manejar las palabras clave de libros de la base de datos."""

    word = models.CharField(max_length=200, unique=True)

    def __str__(self) -> str:
        return self.word


class Author(models.Model):
    """Modelo para manejar los autores de libros de la base de datos."""

    name = models.CharField(max_length=200, unique=True)

    def __str__(self) -> str:
        return self.name


class BookQuerySet(models.QuerySet):
    """QuerySet de `Book` con búsqueda de texto completo (PostgreSQL FTS)."""

    def search(self, query: str, limit: int = 500) -> list["Book"]:
        """
        Busca libros con texto completo (tsvector + GIN).

        ## Argumentos:
        - `query`: Consulta de búsqueda (tipo "plain": sin sintaxis).
        - `limit`: Máximo de resultados.

        ## Retorno:
        - Lista de `Book` ordenada por relevancia, con los atributos
          adicionales `search_rank` (float) y `search_headline`
          (fragmento resaltado de la descripción).
        """
        # `plainto_tsquery` (semántica "plain": AND de todas las palabras)
        # se evalúa dentro de PostgreSQL como argumento parametrizado, por
        # lo que la consulta no es interpretable como sintaxis de tsquery.
        return list(
            self.raw(
                """
                SELECT application_book.*,
                       ts_rank(
                           application_book.search_vector,
                           plainto_tsquery('english', %s)
                       ) AS search_rank,
                       ts_headline(
                           'english',
                           coalesce(application_book.description, ''),
                           plainto_tsquery('english', %s),
                           'StartSel=<mark>, StopSel=</mark>, MinWords=15,
                            MaxWords=25, HighlightAll=FALSE, ShortWord=3'
                       ) AS search_headline
                FROM application_book
                WHERE application_book.search_vector
                    @@ plainto_tsquery('english', %s)
                ORDER BY search_rank DESC
                LIMIT %s
                """,
                [query, query, query, limit],
            )
        )


class Book(models.Model):
    """Modelo para manejar los libros de la base de datos."""

    title = models.CharField(max_length=200)
    authors = models.ManyToManyField(Author, related_name="books")
    year = models.IntegerField()
    isbn = models.CharField(max_length=13)
    cover = models.CharField(max_length=200)  # URL de la imagen de portada
    description = models.TextField(blank=True, default="")
    # Embedding SBERT del libro (pgvector).
    embedding = VectorField(dimensions=EMBEDDING_DIM, null=True, blank=True)
    keywords = models.ManyToManyField(Keyword, related_name="books")
    # Texto plano (título + autores + descripción) usado por la columna
    # generada `search_vector` (tsvector) que crea la migración inicial.
    search_text = models.TextField(blank=True, default="")

    objects = BookQuerySet.as_manager()

    class Meta:
        ordering = ["id"]

    def save(self, *args, **kwargs):
        self.refresh_search_text()
        super().save(*args, **kwargs)

    def refresh_search_text(self) -> None:
        """
        Recalcula `search_text` a partir del título, autores y descripción.
        """
        if self.pk is None:
            # Instancia sin guardar: aún no se pueden consultar los autores.
            authors = ""
        else:
            authors = " ".join(self.authors.values_list("name", flat=True))
        self.search_text = f"{self.title} {authors} {self.description}".strip()

    def get_embedding(self) -> np.ndarray:
        """
        Obtiene el embedding del libro.

        ## Retorno:
        - Embedding del libro (vector de ceros si no se ha asignado).
        """
        if self.embedding is None:
            return np.zeros(EMBEDDING_DIM, dtype=np.float32)
        return np.asarray(self.embedding, dtype=np.float32)

    def set_embedding(self, embedding: np.ndarray) -> None:
        """
        Ajusta el embedding del libro.

        ## Argumentos:
        - `embedding`: Embedding del libro (768 dimensiones).
        """
        self.embedding = np.asarray(embedding, dtype=np.float32)

    def __str__(self) -> str:
        return self.title


class User(AbstractUser):
    """Modelo para manejar los usuarios de la base de datos."""

    # Embedding SBERT del usuario: media ponderada (por valoración) de los
    # embeddings de los libros que le gustan (valoración >= LIKES).
    embedding = VectorField(dimensions=EMBEDDING_DIM, null=True, blank=True)
    # Suma de las valoraciones >= LIKES (denominador de la media ponderada).
    sum_ratings = models.FloatField(default=0.0)

    def get_embedding(self) -> np.ndarray:
        """
        Obtiene el embedding del usuario.

        ## Retorno:
        - Embedding del usuario (vector de ceros si no se ha asignado).
        """
        if self.embedding is None:
            return np.zeros(EMBEDDING_DIM, dtype=np.float32)
        return np.asarray(self.embedding, dtype=np.float32)

    def set_embedding(self, embedding: np.ndarray) -> None:
        """
        Ajusta el embedding del usuario.

        ## Argumentos:
        - `embedding`: Embedding del usuario (768 dimensiones).
        """
        self.embedding = np.asarray(embedding, dtype=np.float32)

    def get_book_rating(self, book: "Book") -> float | None:
        """
        Obtiene la valoración del usuario para un libro.

        ## Argumentos:
        - `book`: Libro para el que se obtiene la valoración.

        ## Retorno:
        - Valoración (0.0-1.0) o `None` si el usuario no lo ha valorado.
        """
        rating = self.ratings.filter(book=book).first()
        return rating.rating if rating is not None else None

    def get_read_books(self) -> models.QuerySet["Book"]:
        """
        Obtiene los libros leídos (valorados) por el usuario.

        ## Retorno:
        - Libros valorados por el usuario.
        """
        return Book.objects.filter(ratings__user=self).distinct()

    def get_liked_books(self) -> models.QuerySet["Book"]:
        """
        Obtiene los libros que le gustan al usuario (valoración >= LIKES).

        ## Retorno:
        - Libros que le gustan al usuario.
        """
        liked_ids = self.ratings.filter(
            rating__gte=LIKES
        ).values_list("book_id", flat=True)
        return Book.objects.filter(id__in=list(liked_ids)).prefetch_related(
            "keywords"
        )

    def get_keywords(self) -> models.QuerySet[Keyword]:
        """
        Obtiene las palabras clave de los libros que le gustan al usuario.

        ## Retorno:
        - Palabras clave de los libros que le gustan al usuario.
        """
        return Keyword.objects.filter(
            books__in=self.get_liked_books()
        ).distinct()

    def __str__(self) -> str:
        return self.username


class Rating(models.Model):
    """Modelo para manejar las valoraciones de los libros por los usuarios."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="ratings"
    )
    book = models.ForeignKey(
        Book, on_delete=models.CASCADE, related_name="ratings"
    )
    rating = models.FloatField()  # 0.0, 0.25, 0.5, 0.75, 1.0

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "book"], name="unique_user_book_rating"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user} - {self.book} - {self.rating}"


class Recommendation(models.Model):
    """
    Recomendación precalculada para un usuario.

    Se recalcula cada vez que el usuario añade, modifica o elimina una
    valoración (ver señales de `Rating`) y desde el comando
    `recompute_recommendations`.
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="recommendations"
    )
    book = models.ForeignKey(
        Book, on_delete=models.CASCADE, related_name="recommendations"
    )
    score = models.FloatField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-score"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "book"],
                name="unique_user_book_recommendation",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user} -> {self.book} ({self.score:.3f})"


class Explanation(models.Model):
    """
    Explicación (XAI) cacheada de una recomendación para un usuario.

    `source` indica si la explicación se generó con palabras clave
    (`keywords`) o con un modelo de lenguaje (`llm`).
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="explanations"
    )
    book = models.ForeignKey(
        Book, on_delete=models.CASCADE, related_name="explanations"
    )
    text = models.TextField()
    source = models.CharField(max_length=32, default="keywords")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "book"],
                name="unique_user_book_explanation",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user} -> {self.book} [{self.source}]"


# --- Señales ---------------------------------------------------------------


def _recompute_user_state(user: User) -> None:
    """
    Recalcula `sum_ratings` y el embedding del usuario a partir de sus
    valoraciones actuales (solo cuentan las valoraciones >= LIKES).

    El recálculo completo (en lugar del incremento) es robusto frente a
    condiciones de carrera y mantiene la invariantes del embedding:
    media ponderada por valoración de los embeddings de los libros que
    le gustan.
    """
    total = 0.0
    acc = np.zeros(EMBEDDING_DIM, dtype=np.float64)
    liked = (
        Rating.objects.filter(user=user, rating__gte=LIKES)
        .select_related("book")
        .iterator()
    )
    for rating in liked:
        total += rating.rating
        acc += rating.rating * rating.book.get_embedding()
    user.sum_ratings = total
    if total > 0.0:
        user.set_embedding(acc / total)
    else:
        user.set_embedding(np.zeros(EMBEDDING_DIM, dtype=np.float32))
    user.save(update_fields=["sum_ratings", "embedding"])


def _on_rating_change(sender, instance: Rating, **kwargs) -> None:
    """
    Recalcula el estado del usuario y sus recomendaciones tras un cambio
    de valoración.

    La fila del usuario se bloquea (`select_for_update`) para serializar
    actualizaciones concurrentes del mismo usuario.
    """
    from application.recommend import recompute_recommendations

    user = User.objects.select_for_update().get(pk=instance.user_id)
    _recompute_user_state(user)
    recompute_recommendations(user)
    logger.info(
        "Recomputado estado y recomendaciones del usuario %s", user.pk
    )


@receiver(post_save, sender=Rating)
def update_user_after_rating_save(sender, instance, created, **kwargs) -> None:
    _on_rating_change(sender, instance, created=created)


@receiver(post_delete, sender=Rating)
def update_user_after_rating_delete(sender, instance, **kwargs) -> None:
    _on_rating_change(sender, instance)


@receiver(m2m_changed, sender=Book.authors.through)
def refresh_book_search_text_on_author_change(
    sender, instance: Book, action, **kwargs
) -> None:
    """
    Actualiza `search_text` cuando cambian los autores de un libro.
    """
    if action in ("post_add", "post_remove", "post_clear"):
        instance.refresh_search_text()
        instance.save(update_fields=["search_text"])
