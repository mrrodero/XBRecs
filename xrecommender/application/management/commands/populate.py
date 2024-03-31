import os
import pandas as pd
import json
from ast import literal_eval
from typing import Dict, List

from django.core.management.base import BaseCommand
from application.models import Keyword, Author, Book, User, Rating
from django.contrib.auth.hashers import make_password

dataset_path = os.path.join(os.getcwd(), "..", "datasets")
model_path = os.path.join(os.getcwd(), "..", "models")
json_file_path = "keyword_books_lemmatized.json"
train_df = pd.read_csv(
    os.path.join(dataset_path, "training", "train_reduced.tsv"),
    sep='\t', names=['user_id', 'book_id', 'rating']
)


class Command(BaseCommand):
    """Clase para poblar la base de datos a partir del dataset GoodBooks10k."""
    help = "Puebla la base de datos a partir del dataset GoodBooks10k."

    def __init__(self, sneaky=True, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def handle(self, *args, **kwargs):
        """
        Esta función se ejecuta cuando se llama al comando desde la terminal.
        """
        self.cleanDataBase()  # Limpia la base de datos
        self.book()  # Crea los libros
        self.user()  # Crea los usuarios
        self.rating()  # Crea las valoraciones

    def cleanDataBase(self):
        """
        Limpia la base de datos al completo.
        """
        print("Limpiando base de datos...")
        classList = [Keyword, Author, Rating, Book, User]
        for c in classList:
            c.objects.all().delete()

    def book(self):
        """
        Se crean las entradas de libros en la base de datos.
        """
        print("Creando libros...")
        # Se cargan los datos completos de los libros
        books_full_df = pd.read_csv(
            os.path.join(dataset_path, "goodbooks_ext", "books_enriched.csv"),
            index_col=[0],
            converters={"authors": literal_eval, "genres": literal_eval}
        )
        # Se cargan los embeddings de los libros
        books_embedding_df = pd.DataFrame(
            pd.read_pickle(os.path.join(dataset_path, "raw", "books_raw.pkl"))
        )
        # Se filtran los libros que aparecen en el conjunto de entrenamiento
        book_ids: List[int] = sorted(train_df['book_id'].unique())
        books_full_df = books_full_df[books_full_df['book_id'].isin(book_ids)]
        books_embedding_df = books_embedding_df[
            books_embedding_df['book_id'].isin(book_ids)
        ]
        with open(json_file_path, "r") as jsonfile:
            books_keyword_dict: Dict[int, List[str]] = json.load(jsonfile)

        # Creación de las entradas de libros
        Book.objects.bulk_create([
            Book(
                id=row['book_id'],
                title=row['title'],
                year=int(row['original_publication_year'])
                if not pd.isna(row['original_publication_year']) else -1,
                isbn=str(row['isbn']) if not pd.isna(row['isbn']) else "",
                cover=row['image_url'],
                description=row['description'],
            ) for _, row in books_full_df.iterrows()
        ])

        # Creación de las relaciones entre libros y autores
        for _, row in books_full_df.iterrows():
            book = Book.objects.get(id=row['book_id'])
            bad_authors: List[str] = row['authors']
            authors = [
                Author.objects.get_or_create(name=author)[0]
                for author in [a.strip('[').strip(']') for a in bad_authors]
            ]
            book.authors.add(*authors)
            book.save()

        # Actualización de los embeddings de los libros
        for _, row in books_embedding_df.iterrows():
            book = Book.objects.get(id=row['book_id'])
            book.set_embedding(row['semantic_sbert'])
            book.save()

        # Creación de las relaciones entre libros y palabras clave
        for book_id, keywords in books_keyword_dict.items():
            book = Book.objects.get(id=book_id)
            keywords = [
                Keyword.objects.get_or_create(word=keyword)[0]
                for keyword in keywords
            ]
            book.keywords.add(*keywords)
            book.save()

    def user(self):
        """
        Se crean las entradas de usuarios en la base de datos.
        """
        print("Creando usuarios...")
        users_df = pd.DataFrame(
            pd.read_pickle(os.path.join(model_path, "user_profiles.pkl"))
        )
        # Creación de las entradas de usuarios
        User.objects.bulk_create([
            User(
                id=row['user_id'],
                username=f"usuario_{row['user_id']}",
                password=make_password(f"3BP_san-ti_{row['user_id']}"),
            ) for _, row in users_df.iterrows()
        ])

        # Actualización de los embeddings de los usuarios
        for _, row in users_df.iterrows():
            user = User.objects.get(id=row['user_id'])
            user.set_embedding(row['semantic_sbert'])
            user.save()

    def rating(self):
        """
        Se crean las entradas de valoraciones en la base de datos.
        """
        print("Creando ratings...")
        # Creación de las entradas de valoraciones
        Rating.objects.bulk_create([
            Rating(
                user_id=row['user_id'],
                book_id=row['book_id'],
                rating=row['rating']
            ) for _, row in train_df.iterrows()
        ])

        # Actualización de la suma de las valoraciones de los usuarios
        users = User.objects.all()
        for user in users:
            user.sum_ratings = sum(
                [r.rating for r in Rating.objects.filter(user=user)]
            )
            user.save()
