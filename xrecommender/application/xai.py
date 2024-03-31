import random
import seaborn as sns
from typing import Dict, List, Tuple

from pyvis.network import Network

from .models import User, Book, Keyword, Rating, LIKES

COL = 255
RADIUS_MULT = 6
HEIGHT = "750px"
WIDTH = "100%"

# TODO: Función para explicar una recomendación particular basada en
# lecturas pasadas que gustaron al usuario (grafo que une al libro
# con libros que también tenían sus palabras clave)

# TODO: Función para mostrar más información sobre la recomendación
# con las métricas del recomendador user-user y la similitud entre
# embedding de libro y usuario


def _xai_explanation_dict(
    user: User, rec_books: List[Book]
) -> Dict[Keyword, Tuple[List[Book], int]]:
    """
    Obtiene la información de la explicación de las recomendaciones
    para generar grafos de explicabilidad.

    ## Parámetros:
    - `user`: Objeto `User` del usuario para el que se explicará
    la recomendación.
    - `rec_books`: Lista de libros recomendados.

    ## Retorna:
    - Diccionario con las palabras clave que explican las recomendaciones
    y los libros recomendados que contienen dichas palabras clave, junto
    con el número de veces que aparece cada palabra clave en el perfil
    del usuario.
    """
    # Palabras clave de los libros recomendados
    rec_keywords = Keyword.objects.filter(book__in=rec_books)

    # Obtenemos los libros que le gustan al usuario
    liked_books = Rating.objects.filter(
        user=user, rating__gte=LIKES
    ).values_list('book', flat=True)
    # Palabras clave del perfil de usuario (los libros que le gustan)
    user_keywords = Keyword.objects.filter(book__in=liked_books)

    # Palabras clave que están tanto en los libros que le gustan al usuario
    # como en los libros recomendados
    common_keywords = rec_keywords.intersection(user_keywords)

    # Agrupamos los libros recomendados por palabras clave y contamos
    # cuántas veces aparece cada palabra clave en el perfil de usuario
    explain_info_dict: Dict[Keyword, Tuple[List[Book], int]] = dict()
    for kw in common_keywords:
        explain_info_dict[kw] = (
            [b for b in rec_books if kw in b.keywords.all()],
            user_keywords.filter(pk=kw.pk).count()
        )
    return explain_info_dict


def _generate_random_color() -> str:
    """
    Genera un color aleatorio.

    ## Retorno:
    - Color en formato hexadecimal.
    """
    color_palette = sns.color_palette("husl", 256)
    r, g, b = random.choice(color_palette)
    return f"#{int(r * COL):02x}{int(g * COL):02x}{int(b * COL):02x}"


def pyvis_graph(user: User, rec_books: List[Book]) -> Network:
    """
    Método para generar un grafo con la librería pyVis y
    devolver su código HTML.

    ## Argumentos:
    - `user`: Objeto `User` del usuario para el que se explicará
    la recomendación.
    - `rec_books`: Lista de libros recomendados.

    ## Retorno:
    - Grafo generado con pyVis.
    """
    # Obtener información del usuario para la recomendación
    net = Network(height='750px', width='100%', heading='')
    # Añadir nodos de libros (serán portadas de los libros)
    for book in rec_books:
        net.add_node(
            book.id,
            shape='image',
            label=book.title,
            title=book.title,
            image=book.cover
        )
    kw_dict = _xai_explanation_dict(user, rec_books)
    keyword_names = [kw.word for kw in list(kw_dict.keys())]
    # Añadir nodos de palabras clave
    net.add_nodes(
        keyword_names,
        label=keyword_names,
        title=keyword_names
    )
    # Añadir aristas entre libros y palabras clave
    net.add_edges(
        [
            (kw.word, book.id)
            for kw, (books, _) in kw_dict.items()
            for book in books
        ]
    )
    # Cambiar tamaño y color de los nodos de palabras clave
    neighbor_map = net.get_adj_list()
    for kw in kw_dict:
        _, freq = kw_dict[kw]
        radius = RADIUS_MULT * (freq + len(neighbor_map[kw.word]))
        node = net.get_node(kw.word)
        node['size'] = radius
        node['color'] = _generate_random_color()

    return net


def pyvis_graph_html(user: User, rec_books: List[Book]) -> str:
    """
    Método para generar un grafo con la librería pyVis y
    devolver su código HTML.

    ## Argumentos:
    - `user`: Usuario para el que se generará la recomendación.
    - `rec_books`: Lista de libros recomendados.

    ## Retorno:
    - Código HTML del grafo.
    """
    return pyvis_graph(user, rec_books).generate_html()
