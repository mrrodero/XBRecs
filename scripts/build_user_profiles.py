#!/usr/bin/env python3
"""
Genera `models/user_profiles.pkl`: el perfil (embedding) de cada usuario
a partir de sus valoraciones.

El perfil de un usuario es la media ponderada por la nota de los
embeddings SBERT de los libros que valoró con 0.75 o más (los que le
"gustan"). Es la misma invariantes que mantiene la aplicación en
runtime (señales de `Rating` en `application/models.py`), de modo que
los perfiles cargados con `populate` y los recalculados al valorar
coinciden.

Uso:
    python scripts/build_user_profiles.py

Entradas:
    datasets/training/train_reduced.tsv  (user_id, book_id, rating)
    datasets/raw/books_raw.pkl           (book_id, semantic_sbert, ...)

Salida:
    models/user_profiles.pkl             (user_id, semantic_sbert)
"""

import os

import numpy as np
import pandas as pd

REPO_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
LIKES = 0.75
EMBEDDING_DIM = 768


def main() -> None:
    train_path = os.path.join(
        REPO_ROOT, "datasets", "training", "train_reduced.tsv"
    )
    books_path = os.path.join(REPO_ROOT, "datasets", "raw", "books_raw.pkl")
    out_path = os.path.join(REPO_ROOT, "models", "user_profiles.pkl")

    train_df = pd.read_csv(train_path, sep="\t", header=None)
    train_df.columns = ["user_id", "book_id", "rating"]
    books_df = pd.DataFrame(pd.read_pickle(books_path))
    books_df = books_df[["book_id", "semantic_sbert"]]

    likes = train_df[train_df["rating"] >= LIKES]
    print(f"Usuarios: {train_df['user_id'].nunique()}")
    print(f"Valoraciones >= {LIKES}: {len(likes)}")

    # Unimos valoraciones positivas con los embeddings de los libros.
    merged = likes.merge(
        books_df[["book_id", "semantic_sbert"]], on="book_id", how="inner"
    )
    user_ids = merged["user_id"].to_numpy()
    weights = merged["rating"].to_numpy(dtype=np.float64)
    mat = np.asarray(merged["semantic_sbert"].tolist(), dtype=np.float64)

    # Acomulamos suma ponderada y suma de pesos por usuario.
    max_id = int(user_ids.max())
    acc = np.zeros((max_id + 1, EMBEDDING_DIM), dtype=np.float64)
    np.add.at(acc, user_ids, mat * weights[:, None])
    totals = np.bincount(user_ids, weights=weights, minlength=max_id + 1)

    profiles = {
        int(uid): (acc[uid] / totals[uid]).astype(np.float32)
        for uid in range(1, max_id + 1)
        if totals[uid] > 0
    }

    users_df = pd.DataFrame(
        {
            "user_id": list(profiles.keys()),
            "semantic_sbert": list(profiles.values()),
        }
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    users_df.to_pickle(out_path)
    print(
        f"OK {out_path} "
        f"({len(users_df)} usuarios, {os.path.getsize(out_path) / 1e6:.2f} MB)"
    )


if __name__ == "__main__":
    main()
