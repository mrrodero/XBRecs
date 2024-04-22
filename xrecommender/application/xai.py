import seaborn as sns
from typing import Dict, List, Iterable

from pyvis.network import Network

from .models import User, Book, Keyword

COL = 255
COL_MULT = 16
COVER_SIZE = 50
RADIUS_MULT = 5
HEIGHT = "750px"
WIDTH = "100%"

# TODO: Función para mostrar más información sobre la recomendación
# con las métricas del recomendador user-user y la similitud entre
# embedding de libro y usuario


def _get_liked_books_with_certain_keywords(
    user: User, keywords: Iterable[Keyword]
) -> Iterable[Book]:
    """
    Obtiene los libros que le gustan al usuario y que contienen
    alguna de las palabras clave dadas.

    ## Argumentos:
    - `user`: Usuario para el que se obtendrán los libros que le gustan.
    - `keywords`: Lista de palabras clave.

    ## Retorno:
    - Libros que le gustan al usuario y que contienen alguna
    de las palabras clave.
    """
    liked_books = user.get_liked_books().filter(keywords__in=keywords)
    return liked_books


def _xai_explanation_full_dict(
    user: User, rec_books: List[Book]
) -> Dict[Keyword, List[Book]]:
    """
    Obtiene la información de la explicación de las recomendaciones
    para generar grafos de explicabilidad.

    ## Parámetros:
    - `user`: Objeto `User` del usuario para el que se explicará
    la recomendación.
    - `rec_books`: Lista de libros recomendados.

    ## Retorna:
    - Diccionario con las palabras clave que explican las recomendaciones
    y los libros del perfil de usuario y de los recomendados que contienen
    dichas palabras clave.
    """
    # Obtener palabras clave comunes entre los libros recomendados y el usuario
    rec_keywords = Keyword.objects.filter(book__in=rec_books)
    common_keywords = rec_keywords.intersection(user.get_keywords())
    liked_books = user.get_liked_books()
    # Los libros que le gustan al usuario y los recomendados
    # con las palabras clave
    liked_rec_books = list(liked_books) + rec_books
    explain_info_dict = {
        kw: [b for b in liked_rec_books if kw in b.keywords.all()]
        for kw in common_keywords
    }
    return explain_info_dict


def _generate_random_color(counter: int) -> str:
    """
    Genera un color aleatorio.

    ## Retorno:
    - Color en formato hexadecimal.
    """
    color_palette = sns.color_palette("husl", 256)
    r, g, b = color_palette[COL_MULT * counter % 256]
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
    net = Network(height=HEIGHT, width=WIDTH, heading='')
    # Añadir nodos de libros (serán portadas de los libros)
    for book in rec_books:
        net.add_node(
            book.id,
            shape='image',
            label=book.title,
            title=book.title,
            image=book.cover,
            size=COVER_SIZE
        )
    kw_dict = _xai_explanation_full_dict(user, rec_books)
    keywords = list(kw_dict.keys())
    for book in _get_liked_books_with_certain_keywords(user, keywords):
        net.add_node(
            book.id,
            shape='image',
            label=book.title,
            title=book.title,
            image=book.cover,
            size=COVER_SIZE // 2
        )

    # Añadir nodos de palabras clave
    keyword_names = [kw.word for kw in keywords]
    net.add_nodes(
        keyword_names,
        label=keyword_names,
        title=keyword_names
    )
    # Añadir aristas entre libros y palabras clave
    net.add_edges(
        [
            (kw.word, book.id)
            for kw, books in kw_dict.items()
            for book in books
        ]
    )
    # Cambiar tamaño y color de los nodos de palabras clave
    neighbor_map = net.get_adj_list()
    i = 0
    for kw in kw_dict:
        # _, freq = kw_dict[kw]
        radius = RADIUS_MULT * len(neighbor_map[kw.word])
        node = net.get_node(kw.word)
        node['size'] = radius
        node['color'] = _generate_random_color(i)
        i += 1

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
