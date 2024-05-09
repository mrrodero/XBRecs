import seaborn as sns
from typing import Dict, List, Iterable

from pyvis.network import Network

from .models import User, Book, Keyword

COL = 255
COL_MULT = 16
COVER_SIZE = 80
SMALL_COVER_SIZE = 36
RADIUS_MULT = 6
FONT_MIN = 20
FONT_MAX = 60
FONT_FACE = "monospace"
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


def xai_explanation_dict(
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


def sort_rec_books_by_keyword_count(
    explain_info_dict: Dict[Keyword, List[Book]],
    rec_books: List[Book]
) -> List[Book]:
    """
    Ordena los libros recomendados por la cantidad de palabras clave.

    ## Argumentos:
    - `explain_info_dict`: Diccionario con las palabras clave que explican
    las recomendaciones y los libros del perfil de usuario y de los
    recomendados que contienen dichas palabras clave.
    - `rec_books`: Lista de libros recomendados.

    ## Retorno:
    - Lista de libros recomendados ordenados por la importancia de las
    palabras clave que explican las recomendaciones.
    """
    # Ordenar los libros recomendados por la cantidad de palabras clave
    rec_books = sorted(
        rec_books,
        key=lambda book: sum(
            len(explain_info_dict.get(kw)) for kw in book.keywords.all()
            if explain_info_dict.get(kw) is not None
        ),
        reverse=True
    )
    return rec_books


def _generate_random_color(counter: int) -> str:
    """
    Genera un color aleatorio.

    ## Retorno:
    - Color en formato hexadecimal.
    """
    color_palette = sns.color_palette("husl", 256)
    r, g, b = color_palette[COL_MULT * counter % 256]
    return f"#{int(r * COL):02x}{int(g * COL):02x}{int(b * COL):02x}"


def _pyvis_graph(
    user: User,
    rec_books: List[Book],
    kw_dict: Dict[Keyword, List[Book]]
) -> Network:
    """
    Método para generar un grafo con la librería pyVis y
    devolver su código HTML.

    ## Argumentos:
    - `user`: Objeto `User` del usuario para el que se explicará
    la recomendación.
    - `rec_books`: Lista de libros recomendados.
    - `kw_dict`: Diccionario con las palabras clave que explican las
    recomendaciones y los libros del perfil de usuario y de los
    recomendados que contienen dichas palabras clave.

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
            size=COVER_SIZE,
            font={"size": FONT_MIN, "face": FONT_FACE}
        )
    keywords = list(kw_dict.keys())
    # Añadir nodos de libros que le gustan al usuario conectados
    # con los libros recomendados por palabras clave
    for book in _get_liked_books_with_certain_keywords(user, keywords):
        rating = int(4 * user.get_book_rating(book) + 1)
        net.add_node(
            book.id,
            shape='image',
            label=rating * "\u2B50",  # f"{rating}\u2B50",
            title=book.title,
            image=book.cover,
            size=SMALL_COVER_SIZE,
            font={"size": FONT_MIN, "face": FONT_FACE}
        )

    # Añadir nodos de palabras clave
    keyword_names = [kw.word for kw in keywords]
    net.add_nodes(
        keyword_names,
        label=keyword_names,
        title=keyword_names,
        shape=['ellipse' for _ in keyword_names],
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
        font = RADIUS_MULT * len(neighbor_map[kw.word])
        if font < FONT_MIN:
            font = FONT_MIN
        elif font > FONT_MAX:
            font = FONT_MAX
        node = net.get_node(kw.word)
        node['font'] = {"size": font, "face": FONT_FACE}
        node['color'] = _generate_random_color(i)
        i += 1

    return net


def pyvis_graph_html(
    user: User,
    rec_books: List[Book],
    kw_dict: Dict[Keyword, List[Book]]
) -> str:
    """
    Método para generar un grafo con la librería pyVis y
    devolver su código HTML.

    ## Argumentos:
    - `user`: Usuario para el que se generará la recomendación.
    - `rec_books`: Lista de libros recomendados.
    - `kw_dict`: Diccionario con las palabras clave que explican las
    recomendaciones y los libros del perfil de usuario y de los
    recomendados que contienen dichas palabras clave.

    ## Retorno:
    - Código HTML del grafo.
    """
    return _pyvis_graph(user, rec_books, kw_dict).generate_html()
