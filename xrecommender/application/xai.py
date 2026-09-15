"""
Explicabilidad (XAI) de las recomendaciones.

La explicación por defecto se basa en las palabras clave compartidas
entre los libros que le gustan al usuario y el libro recomendado, y se
visualiza con un grafo (pyvis).

Opcionalmente, si se configura un proveedor de LLM compatible con la
API de OpenAI mediante variables de entorno (`LLM_API_KEY`,
`LLM_API_BASE`, `LLM_MODEL`), se genera una explicación en lenguaje
natural. Las explicaciones se cachean en la tabla `Explanation` para
no repetirlas.
"""

import logging
import os
from collections.abc import Iterable

import requests
import seaborn as sns
from pyvis.network import Network

from .models import Book, Explanation, Keyword, User

logger = logging.getLogger(__name__)

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

# Configuración del proveedor LLM (compatible con la API de OpenAI).
LLM_TIMEOUT = 20  # segundos


def _book_keyword_map(books: Iterable[Book]) -> dict[int, set[str]]:
    """
    Devuelve `{book_id: {palabra clave, ...}}` con una sola consulta.

    ## Argumentos:
    - `books`: Libros para los que obtener las palabras clave.

    ## Retorno:
    - Diccionario de id de libro a conjunto de palabras clave.
    """
    book_ids = [b.pk for b in books]
    mapping: dict[int, set[str]] = {bid: set() for bid in book_ids}
    for row in Book.objects.filter(pk__in=book_ids).values(
        "id", "keywords__word"
    ):
        mapping[row["id"]].add(row["keywords__word"])
    return mapping


def shared_keywords(user: User, book: Book) -> list[str]:
    """
    Palabras clave compartidas entre el libro y los libros que le
    gustan al usuario.

    ## Argumentos:
    - `user`: Usuario de referencia.
    - `book`: Libro recomendado.

    ## Retorno:
    - Lista de palabras clave compartidas.
    """
    user_kw = set(user.get_keywords().values_list("word", flat=True))
    book_kw = set(book.keywords.values_list("word", flat=True))
    return sorted(user_kw & book_kw)


def keyword_explanation(user: User, book: Book) -> str:
    """
    Explicación basada en las palabras clave compartidas.

    ## Argumentos:
    - `user`: Usuario de referencia.
    - `book`: Libro recomendado.

    ## Retorno:
    - Texto de la explicación.
    """
    shared = shared_keywords(user, book)
    if not shared:
        return "Recomendado por usuarios con gustos similares a los tuyos."
    top = ", ".join(shared[:5])
    return f"Comparte con libros que te gustan las palabras clave: {top}."


def _llm_explanation(user: User, book: Book, shared: list[str]) -> str | None:
    """
    Genera una explicación con un LLM compatible con la API de OpenAI.

    ## Argumentos:
    - `user`: Usuario de referencia.
    - `book`: Libro recomendado.
    - `shared`: Palabras clave compartidas (contexto para el prompt).

    ## Retorno:
    - Texto de la explicación, o `None` si el LLM no está configurado
      o falla (en cuyo caso se usa la explicación por palabras clave).
    """
    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        return None
    api_base = os.environ.get(
        "LLM_API_BASE", "https://api.openai.com/v1"
    ).rstrip("/")
    model = os.environ.get("LLM_MODEL", "gpt-4o-mini")

    liked_titles = ", ".join(
        user.get_liked_books().values_list("title", flat=True)[:10]
    )
    prompt = (
        "Eres el asistente de un sistema de recomendación de libros. "
        f"Explica en 2-3 frases, en español, por qué podría gustarle a un "
        f"usuario el libro «{book.title}» "
        f"({book.description[:200]}). "
        f"El usuario ha valorado positivamente libros como: {liked_titles}. "
        f"Palabras clave en común con sus libros preferidos: {', '.join(shared) or 'ninguna'}. "
        "Sé concreto y evita mencionar que eres un modelo de lenguaje."
    )
    try:
        response = requests.post(
            f"{api_base}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "temperature": 0.3,
                "max_tokens": 200,
                "messages": [
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=LLM_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        logger.exception("Fallo al generar explicación con LLM; usando fallback")
        return None


def get_explanation(user: User, book: Book) -> str:
    """
    Devuelve la explicación de una recomendación, cacheándola en la
    tabla `Explanation`.

    ## Argumentos:
    - `user`: Usuario de referencia.
    - `book`: Libro recomendado.

    ## Retorno:
    - Texto de la explicación.
    """
    existing = Explanation.objects.filter(user=user, book=book).first()
    if existing is not None:
        return existing.text

    shared = shared_keywords(user, book)
    text = _llm_explanation(user, book, shared)
    source = "llm" if text is not None else "keywords"
    if text is None:
        text = keyword_explanation(user, book)
    Explanation.objects.update_or_create(
        user=user, book=book, defaults={"text": text, "source": source}
    )
    return text


def xai_explanation_dict(
    user: User, rec_books: list[Book]
) -> dict[Keyword, list[Book]]:
    """
    Obtiene la información de la explicación de las recomendaciones
    para generar grafos de explicabilidad.

    ## Parámetros:
    - `user`: Objeto `User` del usuario para el que se explicará
      la recomendación.
    - `rec_books`: Lista de libros recomendados.

    ## Retorna:
    - Diccionario con las palabras clave que explican las recomendaciones
      y los libros del perfil de usuario y de los recomendados que
      contienen dichas palabras clave.
    """
    rec_keywords = Keyword.objects.filter(books__in=rec_books)
    common_keywords = list(rec_keywords.intersection(user.get_keywords()))
    if not common_keywords:
        return {}
    liked_books = list(user.get_liked_books())
    all_books = liked_books + list(rec_books)
    # Una sola consulta para las palabras clave de todos los libros.
    kw_map = _book_keyword_map(all_books)
    return {
        kw: [b for b in all_books if kw.word in kw_map.get(b.pk, set())]
        for kw in common_keywords
    }


def sort_rec_books_by_keyword_count(
    explain_info_dict: dict[Keyword, list[Book]], rec_books: list[Book]
) -> list[Book]:
    """
    Ordena los libros recomendados por la cantidad de palabras clave
    que explican la recomendación.

    ## Argumentos:
    - `explain_info_dict`: Diccionario con las palabras clave que
      explican las recomendaciones y los libros que las contienen.
    - `rec_books`: Lista de libros recomendados.

    ## Retorno:
    - Lista de libros recomendados ordenada por la importancia de las
      palabras clave que explican las recomendaciones.
    """
    kw_word = {kw.word: books for kw, books in explain_info_dict.items()}
    kw_map = _book_keyword_map(rec_books)

    def score(book: Book) -> int:
        return sum(
            len(kw_word[kw])
            for kw in kw_map.get(book.pk, set())
            if kw in kw_word
        )

    return sorted(rec_books, key=score, reverse=True)


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
    rec_books: list[Book],
    kw_dict: dict[Keyword, list[Book]],
) -> Network:
    """
    Método para generar un grafo con la librería pyVis y
    devolver su código HTML.

    ## Argumentos:
    - `user`: Objeto `User` del usuario para el que se explicará
      la recomendación.
    - `rec_books`: Lista de libros recomendados.
    - `kw_dict`: Diccionario con las palabras clave que explican las
      recomendaciones y los libros que las contienen.

    ## Retorno:
    - Grafo generado con pyVis.
    """
    # Obtener información del usuario para la recomendación
    net = Network(height=HEIGHT, width=WIDTH, heading="")
    # Añadir nodos de libros (serán portadas de los libros)
    for book in rec_books:
        net.add_node(
            book.id,
            shape="image",
            label=book.title,
            title=book.title,
            image=book.cover,
            size=COVER_SIZE,
            font={"size": FONT_MIN, "face": FONT_FACE},
        )
    keywords = list(kw_dict.keys())
    # Añadir nodos de libros que le gustan al usuario conectados
    # con los libros recomendados por palabras clave
    ratings = {
        r.book_id: r.rating
        for r in user.ratings.select_related("book").iterator()
    }
    for book in _get_liked_books_with_certain_keywords(user, keywords):
        rating_value = ratings.get(book.id)
        if rating_value is None:
            continue
        rating = int(4 * rating_value + 1)
        net.add_node(
            book.id,
            shape="image",
            label=rating * "\u2B50",
            title=book.title,
            image=book.cover,
            size=SMALL_COVER_SIZE,
            font={"size": FONT_MIN, "face": FONT_FACE},
        )

    # Añadir nodos de palabras clave
    keyword_names = [kw.word for kw in keywords]
    keyword_ids = ["keyword_" + kw_name for kw_name in keyword_names]
    net.add_nodes(
        keyword_ids,
        label=keyword_names,
        title=keyword_names,
        shape=["ellipse" for _ in keyword_names],
    )
    # Añadir aristas entre libros y palabras clave
    edges = [
        ("keyword_" + kw.word, book.id)
        for kw, books in kw_dict.items()
        for book in books
    ]
    net.add_edges(edges)
    # Cambiar tamaño y color de los nodos de palabras clave
    neighbor_map = net.get_adj_list()
    for i, kw in enumerate(kw_dict):
        font = RADIUS_MULT * len(neighbor_map["keyword_" + kw.word])
        if font < FONT_MIN:
            font = FONT_MIN
        elif font > FONT_MAX:
            font = FONT_MAX
        node = net.get_node("keyword_" + kw.word)
        node["font"] = {"size": font, "face": FONT_FACE}
        node["color"] = _generate_random_color(i)

    return net


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


def pyvis_graph_html(
    user: User,
    rec_books: list[Book],
    kw_dict: dict[Keyword, list[Book]],
) -> str:
    """
    Método para generar un grafo con la librería pyVis y
    devolver su código HTML.

    ## Argumentos:
    - `user`: Usuario para el que se generará la recomendación.
    - `rec_books`: Lista de libros recomendados.
    - `kw_dict`: Diccionario con las palabras clave que explican las
      recomendaciones y los libros que las contienen.

    ## Retorno:
    - Código HTML del grafo.
    """
    return _pyvis_graph(user, rec_books, kw_dict).generate_html()
