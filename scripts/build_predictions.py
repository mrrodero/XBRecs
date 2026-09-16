#!/usr/bin/env python3
"""
Genera `datasets/training/predictions/predictions_cf_<n>_<k>.tsv`:
predicciones de un modelo user-user (KNN sobre perfiles de usuario)
para el evaluador Elliot (modelo `ProxyRecommender`).

Reproduce el pipeline del notebook
`notebooks/models/ProxyRecommender_UserUser.ipynb`:

1. Vecinos: los `n` usuarios más similares por coseno sobre los
   perfiles (`models/user_profiles.pkl`).
2. Predicción: para cada libro no valorado por el usuario, suma
   `valoración × similitud` sobre los vecinos que le gustó el libro
   (rating >= 0.75); se conservan los `k` libros con mayor puntuación.

El formato del TSV es `user_id<TAB>book_id<TAB>prediction` (sin cabecera).

Uso:
    python scripts/build_predictions.py            # n=100, k=35
    python scripts/build_predictions.py --neighbors 55 --books 50

Requiere `models/user_profiles.pkl` (ver `build_user_profiles.py`).
"""

import argparse
import os

import numpy as np
import pandas as pd

REPO_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
LIKES = 0.75
BATCH = 1000  # usuarios por bloque para la matriz de similitud


def k_nearest(
    user_vec: np.ndarray,
    all_vecs: np.ndarray,
    exclude_idx: int,
    n: int,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Índices y similitudes coseno de los `n` usuarios más parecidos.

    ## Argumentos:
    - `user_vec`: Vector del usuario de referencia.
    - `all_vecs`: Matriz (n_usuarios, dim) de perfiles.
    - `exclude_idx`: Índice del usuario de referencia (se excluye).
    - `n`: Número de vecinos.

    ## Retorno:
    Tupla `(índices, similitudes)` de los vecinos.
    """
    sims = all_vecs @ user_vec
    sims[exclude_idx] = -np.inf
    top = np.argpartition(-sims, min(n, len(sims) - 1))[:n]
    top = top[np.argsort(-sims[top])]
    return top, sims[top]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--neighbors", type=int, default=100)
    parser.add_argument("--books", type=int, default=35)
    args = parser.parse_args()

    profiles_path = os.path.join(REPO_ROOT, "models", "user_profiles.pkl")
    train_path = os.path.join(
        REPO_ROOT, "datasets", "training", "train_reduced.tsv"
    )
    out_dir = os.path.join(REPO_ROOT, "datasets", "training", "predictions")
    out_path = os.path.join(
        out_dir, f"predictions_cf_{args.neighbors}_{args.books}.tsv"
    )

    users_df = pd.DataFrame(pd.read_pickle(profiles_path))
    train_df = pd.read_csv(train_path, sep="\t", header=None)
    train_df.columns = ["user_id", "book_id", "rating"]

    user_ids = users_df["user_id"].to_numpy()
    all_vecs = np.asarray(
        users_df["semantic_sbert"].tolist(), dtype=np.float32
    )
    # Normalización por filas (la similitud coseno es invariante a escala,
    # pero normalizar acelera el producto y evita desbordes).
    norms = np.linalg.norm(all_vecs, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    all_vecs = all_vecs / norms
    # Valoraciones >= LIKES por usuario: {user_id: {book_id: rating}}
    likes = train_df[train_df["rating"] >= LIKES]
    liked_by_user: dict[int, dict[int, float]] = {
        int(uid): dict(zip(g["book_id"], g["rating"]))
        for uid, g in likes.groupby("user_id")
    }
    rated_by_user: dict[int, set[int]] = {
        int(uid): set(g["book_id"])
        for uid, g in train_df.groupby("user_id")
    }

    print(f"Usuarios: {len(user_ids)}, vecinos: {args.neighbors}, libros: {args.books}")

    rows = []
    for i, uid in enumerate(user_ids):
        if i % 1000 == 0:
            print(f"  {i}/{len(user_ids)}")
        top_idx, sims = k_nearest(all_vecs[i], all_vecs, i, args.neighbors)
        neighbors = [(int(user_ids[j]), float(s)) for j, s in zip(top_idx, sims)]
        sim_by_neighbor = {nid: s for nid, s in neighbors}

        # Suma ponderada por libro de los vecinos que le gustó.
        scores: dict[int, float] = {}
        for nid, _ in neighbors:
            for bid, rating in liked_by_user.get(nid, {}).items():
                if int(uid) in rated_by_user and bid in rated_by_user[int(uid)]:
                    continue
                scores[bid] = scores.get(bid, 0.0) + float(rating) * sim_by_neighbor[nid]

        top_books = sorted(scores.items(), key=lambda item: item[1], reverse=True)[
            : args.books
        ]
        rows.extend((int(uid), int(bid), float(score)) for bid, score in top_books)

    os.makedirs(out_dir, exist_ok=True)
    pd.DataFrame(rows, columns=["user_id", "book_id", "prediction"]).to_csv(
        out_path, sep="\t", header=None, index=False
    )
    print(
        f"OK {out_path} ({len(rows)} filas, "
        f"{os.path.getsize(out_path) / 1e6:.2f} MB)"
    )


if __name__ == "__main__":
    main()
