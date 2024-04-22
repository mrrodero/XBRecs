import os
import pandas as pd
from typing import List
from ast import literal_eval
from application.models import User
from application.recommend import recommend_books

dataset_path = os.path.join(os.getcwd(), "datasets")
model_path = os.path.join(os.getcwd(), "models")
train_df = pd.read_csv(
    os.path.join(dataset_path, "training", "train_reduced.tsv"),
    sep='\t', names=['user_id', 'book_id', 'rating']
)

book_ids: List[int] = sorted(train_df['book_id'].unique())
print(f"Libros: {len(book_ids)}")

[print(book_id) for book_id in book_ids[:5]]

books_full_df = pd.read_csv(
    os.path.join(dataset_path, "goodbooks_ext", "books_enriched.csv"),
    index_col=[0],
    converters={"genres": literal_eval, "authors": literal_eval}
)

books_full_df = books_full_df[books_full_df['book_id'].isin(book_ids)]
print(books_full_df['isbn13'].notna().sum())

bad_auth: List[str] = books_full_df.loc[
    books_full_df['book_id'] == 10000, 'authors'
].values[0]

i = 0
for _, row in books_full_df.iterrows():
    bad_auth: List[str] = row['authors']
    authors = [author.strip('[').strip(']') for author in bad_auth]
    [print(author) for author in authors]
    print(authors)
    i += 1
    if i == 8:
        break

print(book_ids[-1])

print(str(int(9.780439e+12)))

user = User.objects.get(id=8)
recommended_books = recommend_books(user)
for book, prediction in recommended_books:
    print(f"{book} - {prediction}")
