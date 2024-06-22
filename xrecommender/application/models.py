import numpy as np
import pickle

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver

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

    def get_book_rating(self, book: Book) -> float:
        """
        Obtiene la valoración del usuario para un libro.

        ## Argumentos:
        - `book`: Libro para el que se obtendrá la valoración.

        ## Retorno:
        - Valoración del usuario para el libro.
        """
        return Rating.objects.filter(
            user=self, book=book
        ).first().rating

    def get_read_books(self) -> models.QuerySet[Book]:
        """
        Obtiene los libros leídos por el usuario.

        ## Retorno:
        - Libros leídos por el usuario.
        """
        return Book.objects.filter(
            rating__user=self
        ).distinct()

    def get_liked_books(self) -> models.QuerySet[Book]:
        """
        Obtiene los libros que le gustan al usuario.

        ## Retorno:
        - Libros que le gustan al usuario.
        """
        return Book.objects.filter(
            rating__user=self, rating__rating__gte=LIKES
        ).distinct()

    def get_keywords(self) -> models.QuerySet[Keyword]:
        """
        Obtiene las palabras clave de los libros que le gustan al usuario.

        ## Retorno:
        - Palabras clave de los libros que le gustan al usuario.
        """
        return Keyword.objects.filter(
            book__rating__user=self, book__rating__rating__gte=LIKES
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


@receiver([pre_save], sender=Rating)
def capture_previous_rating(sender, instance: Rating, **kwargs) -> None:
    """
    Captura la valoración anterior del usuario para un libro.

    ## Argumentos:
    - `sender`: Modelo que envía la señal.
    - `instance`: Instancia de la señal.
    - `kwargs`: Argumentos adicionales.
    """
    global previous_rating_value
    # Acceder a la valoración anterior
    if instance.pk:
        previous_rating = Rating.objects.filter(
            user=instance.user, book=instance.book
        ).first().rating
        # Guardar la valoración anterior
        previous_rating_value = previous_rating


@receiver([post_save], sender=Rating)
def update_user_embedding_after_new_rating(
    sender, instance: Rating, created: bool, **kwargs
) -> None:
    """
    Actualiza el embedding del usuario tras añadir o
    actualizar una valoración.

    ## Argumentos:
    - `sender`: Modelo que envía la señal.
    - `instance`: Instancia de la señal.
    - `created`: Indica si la señal es por una nueva creación.
    - `kwargs`: Argumentos adicionales.
    """
    global previous_rating_value
    # Datos de usuario y valoración
    user = instance.user
    new_user_embedding = user.sum_ratings * user.get_embedding()
    new_sum_ratings = user.sum_ratings
    new_rating_value = instance.rating
    book_embedding = instance.book.get_embedding()
    # Caso en el que se añade una valoración por primera vez
    if created:
        print("Trigger para añadir valoración")
        print(f"Nuevo rating: {new_rating_value}")
        if new_rating_value < LIKES:
            print("Valoración negativa, no se actualiza embedding")
            return
        new_sum_ratings += new_rating_value
        new_user_embedding += new_rating_value * book_embedding
    # Caso en el que se actualiza la valoración
    else:
        print("Trigger para actualizar valoración")
        print(f"Rating anterior: {previous_rating_value}")
        print(f"Nuevo rating: {new_rating_value}")
        if previous_rating_value < LIKES and new_rating_value < LIKES:
            print(
                "Ambas valoraciones son negativas, no se actualiza embedding"
            )
            return
        elif previous_rating_value < LIKES and new_rating_value >= LIKES:
            print("Valoración anterior negativa, nueva positiva")
            new_sum_ratings += new_rating_value
            new_user_embedding += new_rating_value * book_embedding
        elif previous_rating_value >= LIKES and new_rating_value < LIKES:
            print("Valoración anterior positiva, nueva negativa")
            new_sum_ratings -= previous_rating_value
            new_user_embedding -= previous_rating_value * book_embedding
        elif previous_rating_value >= LIKES and new_rating_value >= LIKES:
            print("Ambas valoraciones son positivas")
            new_sum_ratings -= previous_rating_value
            new_sum_ratings += new_rating_value
            new_user_embedding -= previous_rating_value * book_embedding
            new_user_embedding += new_rating_value * book_embedding

    # Suma ponderada de las valoraciones
    if new_sum_ratings != 0.0:
        new_user_embedding /= new_sum_ratings

    # Se actualizan los datos del usuario
    user.sum_ratings = new_sum_ratings
    user.set_embedding(new_user_embedding)
    user.save()


@receiver([post_delete], sender=Rating)
def update_user_embedding_after_delete_rating(
    sender, instance: Rating, **kwargs
) -> None:
    """
    Actualiza el embedding del usuario tras eliminar una valoración.

    ## Argumentos:
    - `sender`: Modelo que envía la señal.
    - `instance`: Instancia de la señal.
    - `kwargs`: Argumentos adicionales.
    """
    print("Trigger para eliminar valoración")
    deleted_rating_value = instance.rating
    if deleted_rating_value < LIKES:
        print("Valoración negativa, no se actualiza embedding")
        return

    # Datos de usuario y valoración
    user = instance.user
    new_user_embedding = user.sum_ratings * user.get_embedding()
    new_sum_ratings = user.sum_ratings
    book_embedding = instance.book.get_embedding()

    # Recálculo de la suma de las valoraciones y del embedding
    new_sum_ratings -= deleted_rating_value
    new_user_embedding -= deleted_rating_value * book_embedding

    # Suma ponderada de las valoraciones
    if new_sum_ratings != 0.0:
        new_user_embedding /= new_sum_ratings

    # Se actualizan los datos del usuario
    user.sum_ratings = new_sum_ratings
    user.set_embedding(new_user_embedding)
    user.save()
