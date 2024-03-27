import numpy as np
import pickle

from django.db import models
from django.contrib.auth.models import AbstractUser


class Keyword(models.Model):
    """Modelo para manejar las palabras clave de la base de datos"""
    word = models.CharField(max_length=200)

    def __str__(self) -> str:
        """
        Representación en string de la palabra clave.

        ## Retorno:
        - Nombre de la palabra clave.
        """
        return self.word


class Book(models.Model):
    """Modelo para manejar los libros de la base de datos"""
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=200)
    year = models.IntegerField()
    isbn = models.CharField(max_length=13)
    cover = models.CharField(max_length=200)  # URL de la imagen de portada
    description = models.TextField()
    embedding = models.BinaryField()  # Embedding SBERT del libro
    keywords = models.ManyToManyField(Keyword)  # Palabras clave del libro

    def set_embedding(self, embedding: np.ndarray) -> None:
        """
        Ajusta el embedding del libro.

        ## Argumentos:
        - `embedding`: Embedding del libro.
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
    """Modelo para manejar los usuarios de la base de datos"""
    pass


class UserProfile(models.Model):
    """Modelo para manejar los perfiles de usuario de la base de datos"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    read_books = models.ManyToManyField(Book)  # Libros leídos por el usuario
    embedding = models.BinaryField()  # Embedding SBERT del usuario

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

    def __str__(self) -> str:
        """
        Representación en string del perfil de usuario.

        ## Retorno:
        - Nombre de usuario.
        """
        return self.user.username


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
