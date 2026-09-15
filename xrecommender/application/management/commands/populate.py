"""
Puebla la base de datos a partir del dataset GoodBooks10k.

Fuentes de datos (ver `docs/DATA.md`):

- `datasets/goodbooks_ext/books_enriched.csv` — metadatos de los libros.
- `datasets/raw/books_raw.pkl` — embeddings SBERT de los libros.
- `models/user_profiles.pkl` — embeddings de los usuarios (regenerable
  con `scripts/build_user_profiles.py`).
- `keyword_books_lemmatized.json` — palabras clave de los libros.
- `datasets/training/train_reduced.tsv` — valoraciones (10.000 usuarios).

El comando borra los datos existentes, crea libros, usuarios y
valoraciones, y recalcula las recomendaciones de todos los usuarios.
"""

import json
import os
import secrets
from ast import literal_eval

import pandas as pd
from application.models import (
    LIKES,
    Author,
    Book,
    Explanation,
    Keyword,
    Rating,
    Recommendation,
    User,
)
from application.recommend import recompute_recommendations
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db import connection, transaction

DATASET_PATH = os.path.join(os.getcwd(), "..", "datasets")
MODELS_PATH = os.path.join(os.getcwd(), "..", "models")
KEYWORDS_JSON = "keyword_books_lemmatized.json"

BATCH = 5000


class Command(BaseCommand):
    """Clase para poblar la base de datos a partir del dataset GoodBooks10k."""

    help = "Puebla la base de datos a partir del dataset GoodBooks10k."

    def handle(self, *args, **kwargs):
        self.stdout.write("Cargando conjunto de entrenamiento...")
        train_df = pd.read_csv(
            os.path.join(DATASET_PATH, "training", "train_reduced.tsv"),
            sep="\t",
            names=["user_id", "book_id", "rating"],
        )
        self.clean()
        self.load_books(train_df)
        self.load_users()
        self.load_ratings(train_df)
        self.recompute_all()
        self.stdout.write(self.style.SUCCESS("Base de datos poblada."))

    def clean(self) -> None:
        """Limpia la base de datos al completo."""
        self.stdout.write("Limpiando base de datos...")
        with transaction.atomic():
            for model in (
                Explanation,
                Recommendation,
                Rating,
                Keyword,
                Author,
                Book,
                User,
            ):
                model.objects.all().delete()

    def load_books(self, train_df: pd.DataFrame) -> None:
        """Crea las entradas de libros, autores, palabras clave y embeddings."""
        self.stdout.write("Creando libros...")
        books_full_df = pd.read_csv(
            os.path.join(DATASET_PATH, "goodbooks_ext", "books_enriched.csv"),
            index_col=[0],
            converters={"authors": literal_eval, "genres": literal_eval},
        )
        books_embedding_df = pd.DataFrame(
            pd.read_pickle(os.path.join(DATASET_PATH, "raw", "books_raw.pkl"))
        )
        # Filtrar los libros que aparecen en el conjunto de entrenamiento.
        book_ids: list[int] = sorted(train_df["book_id"].unique())
        books_full_df = books_full_df[
            books_full_df["book_id"].isin(book_ids)
        ].reset_index()
        books_embedding_df = books_embedding_df[
            books_embedding_df["book_id"].isin(book_ids)
        ]
        with open(KEYWORDS_JSON, "r") as jsonfile:
            books_keyword_dict: dict[int, list[str]] = {
                int(k): v for k, v in json.load(jsonfile).items()
            }

        # Embeddings por id de libro.
        embedding_by_id: dict[int, list] = {
            int(row.book_id): list(row.semantic_sbert)
            for row in books_embedding_df.itertuples(index=False)
        }

        # Autores y palabras clave (bulk).
        author_names = set()
        for authors in books_full_df["authors"]:
            author_names.update(a.strip("[]") for a in authors)
        authors = {
            name: Author(name=name) for name in sorted(author_names)
        }
        Author.objects.bulk_create(list(authors.values()), batch_size=BATCH)

        keyword_words = set()
        for keywords in books_keyword_dict.values():
            keyword_words.update(keywords)
        keywords = {word: Keyword(word=word) for word in sorted(keyword_words)}
        Keyword.objects.bulk_create(list(keywords.values()), batch_size=BATCH)

        # Libros (bulk), con search_text y embedding ya asignados.
        books: list[Book] = []
        for row in books_full_df.itertuples(index=False):
            # Algunos libros repiten autores en la lista original; se
            # deduplican preservando el orden.
            author_list = list(dict.fromkeys(a.strip("[]") for a in row.authors))
            description = (
                row.description if isinstance(row.description, str) else ""
            )
            book = Book(
                id=int(row.book_id),
                title=row.title,
                year=(
                    int(row.original_publication_year)
                    if not pd.isna(row.original_publication_year)
                    else -1
                ),
                isbn=(
                    str(int(row.isbn13))
                    if not pd.isna(row.isbn13)
                    else ""
                ),
                cover=(
                    row.image_url if isinstance(row.image_url, str) else ""
                ),
                description=description,
                search_text=(
                    f"{row.title} {' '.join(author_list)} {description}".strip()
                ),
            )
            if int(row.book_id) in embedding_by_id:
                book.set_embedding(embedding_by_id[int(row.book_id)])
            books.append(book)
        Book.objects.bulk_create(books, batch_size=BATCH)

        # Relaciones libro-autor (bulk sobre la tabla intermedia).
        through_author = Book.authors.through
        Book.authors.through.objects.bulk_create(
            [
                through_author(book_id=int(row.book_id), author_id=author.pk)
                for row in books_full_df.itertuples(index=False)
                for author in (
                    authors[a]
                    for a in dict.fromkeys(a.strip("[]") for a in row.authors)
                )
            ],
            batch_size=BATCH,
        )

        # Relaciones libro-palabra clave (bulk sobre la tabla intermedia).
        through_keyword = Book.keywords.through
        Book.keywords.through.objects.bulk_create(
            [
                through_keyword(book_id=book_id, keyword_id=keyword.pk)
                for book_id, words in books_keyword_dict.items()
                for keyword in (
                    keywords[w]
                    for w in dict.fromkeys(words)  # deduplica preservando orden
                )
            ],
            batch_size=BATCH,
        )
        self.stdout.write(f"  {Book.objects.count()} libros creados.")

    def load_users(self) -> None:
        """Crea las entradas de usuarios con sus embeddings."""
        self.stdout.write("Creando usuarios...")
        profiles_path = os.path.join(MODELS_PATH, "user_profiles.pkl")
        if not os.path.exists(profiles_path):
            raise SystemExit(
                "Falta models/user_profiles.pkl. Genéralo con:\n"
                "  python scripts/build_user_profiles.py\n"
                "(ver docs/DATA.md)"
            )
        users_df = pd.DataFrame(pd.read_pickle(profiles_path))
        users = [
            User(
                id=int(row.user_id),
                username=f"usuario_{int(row.user_id)}",
                # Contraseña aleatoria por usuario (no patrón predecible).
                password=make_password(secrets.token_urlsafe(16)),
                embedding=list(row.semantic_sbert),
            )
            for row in users_df.itertuples(index=False)
        ]
        User.objects.bulk_create(users, batch_size=BATCH)
        self.stdout.write(f"  {User.objects.count()} usuarios creados.")

    def load_ratings(self, train_df: pd.DataFrame) -> None:
        """Crea las entradas de valoraciones y la suma por usuario."""
        self.stdout.write("Creando valoraciones...")
        ratings = [
            Rating(
                user_id=int(row.user_id),
                book_id=int(row.book_id),
                rating=float(row.rating),
            )
            for row in train_df.itertuples(index=False)
            if pd.notna(row.rating)
        ]
        Rating.objects.bulk_create(ratings, batch_size=BATCH)
        # Suma de valoraciones >= LIKES por usuario (una sola consulta;
        # 0 para los usuarios sin valoraciones "gustadas").
        with connection.cursor() as cur:
            cur.execute(
                """
                UPDATE application_user u
                SET sum_ratings = COALESCE(
                    (
                        SELECT SUM(r.rating)
                        FROM application_rating r
                        WHERE r.user_id = u.id AND r.rating >= %s
                    ),
                    0
                )
                """,
                [LIKES],
            )
        self.stdout.write(f"  {Rating.objects.count()} valoraciones creadas.")

    def recompute_all(self) -> None:
        """Recalcula las recomendaciones de todos los usuarios."""
        self.stdout.write("Recalculando recomendaciones de todos los usuarios...")
        total = User.objects.count()
        for i, user in enumerate(User.objects.order_by("id").iterator(chunk_size=500), 1):
            recompute_recommendations(user)
            if i % 1000 == 0 or i == total:
                self.stdout.write(f"  {i}/{total} usuarios")
