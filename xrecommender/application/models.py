import numpy as np
import pickle

from django.db import models
from django.contrib.auth.models import AbstractUser
# from django.db.models.signals import post_save, post_delete
# from django.dispatch import receiver

LIKES = 0.75
EMBEDDING_DIM = 768


class Keyword(models.Model):
    """Modelo para manejar las palabras clave de libros de la base de datos."""
    word = models.CharField(max_length=200, unique=True)

    def __str__(self) -> str:
        """
        Representación en string de la palabra clave.

        ## Retorno:
        - Nombre de la palabra clave.
        """
        return self.word


class Author(models.Model):
    """Modelo para manejar los autores de libros de la base de datos."""
    name = models.CharField(max_length=200, unique=True)

    def __str__(self) -> str:
        """
        Representación en string del autor.

        ## Retorno:
        - Nombre del autor.
        """
        return self.name


class Book(models.Model):
    """Modelo para manejar los libros de la base de datos."""

    def default_embedding() -> bytes:
        """
        Embedding por defecto del usuario.

        ## Retorno:
        - Vector de ceros.
        """
        return pickle.dumps(np.zeros(EMBEDDING_DIM))

    title = models.CharField(max_length=200)
    authors = models.ManyToManyField(Author)  # Autores del libro
    year = models.IntegerField()
    isbn = models.CharField(max_length=13)
    cover = models.CharField(max_length=200)  # URL de la imagen de portada
    description = models.TextField()
    embedding = models.BinaryField(
        default=default_embedding
    )  # Embedding SBERT del libro
    keywords = models.ManyToManyField(Keyword)  # Palabras clave del libro

    def set_embedding(self, embedding: np.ndarray) -> None:
        """
        Ajusta el embedding del libro.

        ## Argumentos:
        - `embedding`: Embedding del libro. Por defecto, es un
        vector de ceros.
        """
        self.embedding = pickle.dumps(embedding)

    def get_embedding(self) -> np.ndarray:
        """
        Obtiene el embedding del libro.

        ## Retorno:
        - Embedding del libro.
        """
        return pickle.loads(self.embedding)

    def __str__(self) -> str:
        """
        Representación en string del libro.

        ## Retorno:
        - Título del libro.
        """
        return self.title


class User(AbstractUser):
    """Modelo para manejar los usuarios de la base de datos."""

    def default_embedding() -> bytes:
        """
        Embedding por defecto del usuario.

        ## Retorno:
        - Vector de ceros.
        """
        return pickle.dumps(np.zeros(EMBEDDING_DIM))

    embedding = models.BinaryField(
        default=default_embedding
    )  # Embedding SBERT del usuario
    sum_ratings = models.FloatField(default=0.0)  # Suma de las valoraciones

    def set_embedding(self, embedding: np.ndarray) -> None:
        """
        Ajusta el embedding del usuario.

        ## Argumentos:
        - `embedding`: Embedding del usuario.
        """
        self.embedding = pickle.dumps(embedding)

    def get_embedding(self) -> np.ndarray:
        """
        Obtiene el embedding del usuario.

        ## Retorno:
        - Embedding del usuario.
        """
        return pickle.loads(self.embedding)

    def get_liked_books(self) -> models.QuerySet[Book]:
        """
        Obtiene los libros que le gustan al usuario.

        ## Retorno:
        - Libros que le gustan al usuario.
        """
        return Book.objects.filter(rating__user=self, rating__rating=LIKES)

    def get_keywords(self) -> models.QuerySet[Keyword]:
        """
        Obtiene las palabras clave de los libros que le gustan al usuario.

        ## Retorno:
        - Palabras clave de los libros que le gustan al usuario.
        """
        return Keyword.objects.filter(
            book__rating__user=self, book__rating__rating=LIKES
        ).distinct()

    def __str__(self) -> str:
        """
        Representación en string del perfil de usuario.

        ## Retorno:
        - Nombre de usuario.
        """
        return self.username


class Rating(models.Model):
    """Modelo para manejar las valoraciones de los libros por los usuarios"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    rating = models.FloatField()  # 0.0, 0.25, 0.5, 0.75, 1.0

    def __str__(self) -> str:
        """
        Representación en string de la valoración.

        ## Retorno:
        - Valoración del libro por el usuario.
        """
        return f'{self.user} - {self.book} - {self.rating}'


# @receiver([post_save, post_delete], sender=Rating)
# def update_user_embedding(sender, instance: Rating, **kwargs) -> None:
#     """
#     Actualiza el embedding del usuario tras añadir o eliminar una valoración.

#     ## Argumentos:
#     - `sender`: Modelo que envía la señal.
#     - `instance`: Instancia de la señal.
#     - `kwargs`: Argumentos adicionales.
#     """
#     # Actualización de la suma de las valoraciones
#     user = instance.user
#     rating = instance.rating
#     new_sum_ratings = user.sum_ratings
#     if kwargs['signal'] == post_save:
#         new_sum_ratings += rating
#     else:
#         new_sum_ratings -= rating

#     user.sum_ratings = new_sum_ratings
#     user.save()

#     # Si la valoración es negativa, no se actualiza el embedding
#     if rating < LIKES:
#         return

#     # Actualización del embedding
#     book_embedding = instance.book.get_embedding()
#     new_user_embedding = user.get_embedding()
#     if kwargs['signal'] == post_save:
#         new_user_embedding += rating * book_embedding
#     else:
#         new_user_embedding -= rating * book_embedding

#     # Suma ponderada de las valoraciones
#     if new_sum_ratings != 0.0:
#         new_user_embedding /= new_sum_ratings

#     # Normalización del embedding
#     norm = np.linalg.norm(new_user_embedding)
#     if norm != 0.0:
#         new_user_embedding /= norm

#     user.set_embedding(new_user_embedding)
#     user.save()
