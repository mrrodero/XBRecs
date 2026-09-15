#!/usr/bin/env python3
"""
Regenera `xrecommender/keyword_books_lemmatized.json`: las palabras
clave (lemmatizadas) de cada libro, extraídas de su sinopsis.

Reproduce el pipeline original (notebook `notebooks/analysis/explain.ipynb`):
extracción con KeyBERT sobre el modelo `all-distilroberta-v1` (el mismo
usado para los embeddings), con stopwords de NLTK + stopwords propias de
dominio, y lematización con WordNet.

Requisitos (solo de pipeline de datos, no en `requirements.txt`):

    pip install keybert nltk
    python -m nltk.downloader wordnet stopwords

Uso:
    python scripts/build_keywords.py

Entrada:
    datasets/goodbooks_ext/books_enriched.csv  (columna `description`)

Salida:
    xrecommender/keyword_books_lemmatized.json  ({book_id: [palabra, ...]})
"""

import json
import os

import pandas as pd

REPO_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
N_WORDS = 10

# Stopwords propias de dominio (aparecen demasiado a menudo en sinopsis).
BOOK_STOPWORDS = [
    "novel",
    "novels",
    "book",
    "books",
    "story",
    "stories",
    "fiction",
    "author",
    "authors",
    "written",
    "bestseller",
    "bestselling",
    "published",
    "publisher",
    "publishers",
]


def main() -> None:
    books_path = os.path.join(
        REPO_ROOT, "datasets", "goodbooks_ext", "books_enriched.csv"
    )
    out_path = os.path.join(
        REPO_ROOT, "xrecommender", "keyword_books_lemmatized.json"
    )

    books_df = pd.read_csv(books_path, index_col=[0])
    books_df = books_df[books_df["description"].notna()]
    print(f"Libros con sinopsis: {len(books_df)}")

    from keybert import KeyBERT
    from nltk.corpus import stopwords
    from nltk.stem import WordNetLemmatizer

    stop = set(stopwords.words("english")) | set(BOOK_STOPWORDS)
    lemmatizer = WordNetLemmatizer()
    kw_model = KeyBERT(model="all-distilroberta-v1")

    result = {}
    for i, (idx, row) in enumerate(books_df.iterrows()):
        keywords = kw_model.extract_keywords(
            row["description"], top_n=N_WORDS, stop_words=stop
        )
        words = [
            lemmatizer.lemmatize(word)
            for word, _ in keywords
            if lemmatizer.lemmatize(word) not in stop
        ]
        if words:
            result[int(row.book_id)] = words
        if (i + 1) % 1000 == 0:
            print(f"  {i + 1}/{len(books_df)}")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)
    print(
        f"OK {out_path} ({len(result)} libros, "
        f"{os.path.getsize(out_path) / 1e6:.2f} MB)"
    )


if __name__ == "__main__":
    main()
