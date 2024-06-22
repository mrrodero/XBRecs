import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from typing import Dict, List, Tuple

from .models import User, Book, Rating, LIKES

# TODO: Función k_nearest más general con Union[User, Book]


def k_nearest(user: User, k: int) -> List[Tuple[User, float]]:
    """
    Calcula los k usuarios más próximos a un usuario.

    ## Parámetros:
    - `user`: Objeto `User` del usuario del que queremos obtener los `k`
    usuarios más próximos.
    - `k`: Número de vecinos más próximos que queremos obtener.

    ## Retorna:
    - k tuplas (`User`, similitud) con los `k` usuarios más próximos
    al usuario.
    """
    # Embedding del usuario
    user_embedding = user.get_embedding().reshape(1, -1)
    # Obtenemos todos los usuarios menos el usuario actual
    users = User.objects.exclude(id=user.id)
    users_embeddings = np.array([u.get_embedding() for u in users])
    # Similitudes (coseno) entre el usuario y todos los demás
    similarities = cosine_similarity(
        user_embedding, users_embeddings
    ).flatten()
    users_sim = list(zip(users, similarities))
    # Obtenemos los k vecinos más próximos
    users_sim.sort(key=lambda x: x[1], reverse=True)
    return users_sim[:k]


def top_k_books(
    user: User, nearest_users_sim: List[Tuple[User, float]], k: int
) -> List[Tuple[Book, float]]:
    """
    Obtiene los libros mejor valorados por los usuarios más próximos
    al usuario.

    ## Parámetros:
    - `user`: Objeto `User` del usuario al que queremos recomendar libros.
    - `nearest_users_sim`: Lista de tuplas (`User`, similitud) con los usuarios
    más próximos al usuario.
    - `k`: Número de libros que queremos obtener.

    ## Retorna:
    - Lista de tuplas (`Book`, predicción) con los `k` libros con mejor
    valoración por los usuarios más próximos.
    """
    # Obtenemos los k usuarios más próximos y sus similitudes
    nearest_users = [u for u, _ in nearest_users_sim]
    nearest_sims = [s for _, s in nearest_users_sim]

    # Obtenemos los ratings positivos de los k usuarios más próximos
    nearest_ratings = Rating.objects.filter(
        user__in=nearest_users
    ).filter(rating__gte=LIKES)

    # Obtenemos los ratings de libros que no ha valorado el usuario
    user_ratings = Rating.objects.filter(user=user)
    not_read_nearest_ratings = nearest_ratings.exclude(
        book__in=user_ratings.values('book')
    )

    # Calculamos la predicción de los libros, que será la suma agregada
    # de las valoraciones multiplicadas por la similitud entre usuarios
    book_pred: Dict[Book, float] = dict()
    for rating in not_read_nearest_ratings:
        book = rating.book
        if book not in book_pred:
            book_pred[book] = 0.0
        book_pred[book] += rating.rating * \
            nearest_sims[nearest_users.index(rating.user)]

    # Obtenemos los k libros mejor valorados
    top_books = list(book_pred.items())
    top_books.sort(key=lambda x: x[1], reverse=True)
    return top_books[:k]


def recommend_books(
    user: User, n: int = 35, k: int = 5
) -> List[Tuple[Book, float]]:
    """
    Recomienda libros a un usuario basándose en los `k` libros mejor valorados
    por los `n` usuarios más próximos.

    ## Parámetros:
    - `user`: Objeto `User` del usuario al que queremos recomendar libros.
    - `n`: Número de usuarios más próximos para los que se obtendrán
    los libros mejor valorados. Por defecto su valor es 35.
    - `k`: Número de libros que queremos obtener. Por defecto su valor es 5.

    ## Retorna:
    - Lista de tuplas (`Book`, predicción) con los `k` libros que
    se recomiendan al usuario.
    """
    # Obtenemos los k libros mejor valorados por los n usuarios más próximos
    return top_k_books(user, k_nearest(user, n), k)
