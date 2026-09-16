#!/usr/bin/env python3
"""
Regenera `datasets/raw/books_raw.pkl`: los embeddings SBERT de los
libros, a partir de sus sinopsis.

El pipeline original usaba el modelo `all-distilroberta-v1` de
sentence-transformers (768 dimensiones). Este script reproduce ese
pipeline para quien necesite regenerar o extender los embeddings.

Requisitos (no incluidos en `requirements.txt`, porque son solo de
pipeline de datos):

    pip install sentence-transformers

Uso:
    python scripts/build_book_embeddings.py
    python scripts/build_book_embeddings.py --model all-distilroberta-v1

Entrada:
    datasets/goodbooks_ext/books_enriched.csv  (columna `description`)

Salida:
    datasets/raw/books_raw.pkl  (book_id, semantic_sbert)
"""

import argparse
import os

import pandas as pd

REPO_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model",
        default="all-distilroberta-v1",
        help="Modelo sentence-transformers a usar (por defecto el original).",
    )
    parser.add_argument(
        "--batch-size", type=int, default=64, help="Tamaño de batch."
    )
    args = parser.parse_args()

    books_path = os.path.join(
        REPO_ROOT, "datasets", "goodbooks_ext", "books_enriched.csv"
    )
    out_path = os.path.join(REPO_ROOT, "datasets", "raw", "books_raw.pkl")

    books_df = pd.read_csv(books_path, index_col=[0])
    # Solo libros con sinopsis (los embeddings se calculan sobre ella).
    books_df = books_df[books_df["description"].notna()]
    print(f"Libros con sinopsis: {len(books_df)}")

    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(args.model)
    print(f"Modelo: {args.model} (dim={model.get_sentence_embedding_dimension()})")

    embeddings = model.encode(
        books_df["description"].fillna("").tolist(),
        batch_size=args.batch_size,
        show_progress_bar=True,
        normalize_embeddings=False,
    )

    out = pd.DataFrame(
        {
            "book_id": books_df["book_id"].to_numpy(),
            "semantic_sbert": list(embeddings),
        }
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    out.to_pickle(out_path)
    print(f"OK {out_path} ({len(out)} libros, {os.path.getsize(out_path) / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
