# Datos de XBRecs

Este documento describe todos los datos que usa el proyecto, de dónde
proceden, cómo se regeneran y cómo se distribuyen.

## Origen

Los datos proceden del dataset **GoodBooks-10k** (Malcolm Osh,
[github.com/malcolmosh/goodbooks-10k](https://github.com/malcolmosh/goodbooks-10k)),
ampliado en el proyecto original con sinopsis, autores y géneros
(`books_enriched.csv`). Sobre esa base se generaron:

- embeddings de libros (SBERT, modelo `all-distilroberta-v1`, 768 dims),
- perfiles de usuario (media ponderada de los embeddings de los libros
  que a cada usuario le gustaron, rating ≥ 0.75),
- palabras clave por libro (KeyBERT + lematización WordNet),
- particiones de entrenamiento/test y predicciones del modelo user-user.

## Archivos

| Archivo | Tamaño aprox. | Descripción |
| --- | --- | --- |
| `datasets/goodbooks_ext/books_enriched.csv` | 13 MB | Metadatos de los libros (título, autores, año, ISBN, portada, sinopsis). |
| `datasets/raw/books_raw.pkl` | 49 MB | Embeddings SBERT de los libros (`book_id`, `semantic_sbert`, ...). |
| `datasets/ready/ratings.csv` | 82 MB | Valoraciones completas del dataset original. |
| `datasets/training/train_reduced.tsv` | 12 MB | Entrenamiento reducido: 10.000 usuarios (`user_id  book_id  rating`). |
| `datasets/training/test_reduced.tsv` | 3 MB | Test reducido (mismos usuarios). |
| `datasets/training/train.tsv` / `test.tsv` | 65/16 MB | Entrenamiento/test completos. |
| `datasets/training/train_train*.tsv`, `train_valid*.tsv` | — | Sub-particiones para la búsqueda de hiperparámetros. |
| `datasets/training/predictions/predictions_cf_100_35.tsv` | ~1 MB | Predicciones user-user (100 vecinos, 35 libros) para Elliot. |
| `models/user_profiles.pkl` | 31 MB | Perfiles (embeddings) de los 10.000 usuarios. |
| `xrecommender/keyword_books_lemmatized.json` | 1 MB | Palabras clave lematizadas por libro (`{book_id: [palabra, ...]}`). |
| `xrecommender/keyword_books.json` | 1 MB | Palabras clave sin lematizar (archivo histórico). |

## Distribución

Los archivos grandes **no se versionan en git** (ver `.gitignore`). Se
distribuyen de estas formas:

1. **`books_enriched.csv`**: se descarga desde el repositorio público
   original:
   ```bash
   python scripts/fetch_data.py
   ```
2. **`books_raw.pkl`, `ratings.csv`, `datasets/training/*`**: se publican
   como *assets* de una *release* de GitHub (o en Hugging Face Hub) para
   no inflar el historial de git. Para reproducirlos desde cero:
   - `books_raw.pkl`: `python scripts/build_book_embeddings.py`
     (requiere `pip install sentence-transformers`).
   - `user_profiles.pkl`: `python scripts/build_user_profiles.py`.
   - `predictions_cf_100_35.tsv`: `python scripts/build_predictions.py`.
   - `keyword_books_lemmatized.json`: `python scripts/build_keywords.py`
     (requiere `pip install keybert nltk`).
3. Los archivos ya descargados quedan en el árbol local y son los que usa
   `manage.py populate`.

## Carga en la base de datos

```bash
# Desde la carpeta xrecommender/ (o: make populate)
python manage.py populate
```

El comando:

1. Borra los datos existentes.
2. Crea libros (con `search_text` para la búsqueda a texto completo),
   autores, palabras clave y embeddings (pgvector).
3. Crea los 10.000 usuarios con contraseñas aleatorias y sus perfiles.
4. Carga las valoraciones de `train_reduced.tsv`.
5. Recalcula las recomendaciones precalculadas de todos los usuarios.

## Invariantes

- **Embedding de usuario** = media ponderada por la nota de los
  embeddings de los libros con rating ≥ 0.75 (los que le "gustan").
  Lo mantienen a raya las señales de `Rating` en `application/models.py`,
  por lo que `populate` y las valoraciones en runtime producen el mismo
  resultado.
- **Recomendaciones** = KNN user-user (35 vecinos) sobre los embeddings,
  con *cold start* (contenido + popularidad) para usuarios con menos de
  3 valoraciones o sin vecinos útiles. Se persisten en la tabla
  `Recommendation` y se recalculan ante cada cambio de valoración.
