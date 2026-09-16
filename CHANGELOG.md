# Registro de cambios

Todas las modificaciones notables de este proyecto se documentan en este
archivo. El formato sigue [Keep a Changelog](https://keepachangelog.com/es/1.1.0/)
y el proyecto usa [versionado semántico](https://semver.org/lang/es/).

## [2.0.3] - 2026-09-15

### Corregido

- `pip-audit` en CI ya no falla al intentar auditar el paquete editable
  local `xrecommender-testenv` (no existe en PyPI): ahora se ejecuta con
  `--skip-editable`.

## [2.0.2] - 2026-09-15

### Corregido

- El workflow de seguridad (`pip-audit`) se ejecutaba desde la raíz del
  repositorio, donde la ruta relativa `-e ../devtools` de
  `requirements-dev.txt` no se resolvía (pip resuelve rutas relativas de
  requisitos respecto al directorio de trabajo). Ahora se ejecuta desde
  `xrecommender/`, igual que el workflow de tests.

## [2.0.1] - 2026-09-15

### Corregido

- El plugin de pytest `testenv` ya no depende del directorio de trabajo
  en `sys.path`: ahora se instala como paquete editable (`devtools/`),
  de modo que `pytest` funciona tanto como script de consola (CI) como
  con `python -m pytest` (local).

## [2.0.0] - 2026-09-15

Modernización completa del proyecto (Etapas 0-6 del plan de
modernización).

### Añadido

- Búsqueda full-text con PostgreSQL (`tsvector` generado + índice GIN,
  `ts_rank`, `ts_headline`) con paginación (20 resultados por página).
- Embeddings de libros y usuarios en `pgvector` (768 dimensiones,
  índice HNSW `vector_cosine_ops`) para búsqueda ANN.
- Recomendaciones precalculadas persistidas en `Recommendation`,
  recalculadas ante cada cambio de valoración (señales) o con
  `manage.py recompute_recommendations`.
- Cold start por contenido (palabras clave compartidas) con fallback a
  populares para usuarios con menos de 3 valoraciones.
- Explicaciones XAI por palabras clave compartidas (cache en
  `Explanation`), grafo interactivo `pyvis` y explicaciones opcionales
  con LLM (API compatible con OpenAI, por variables de entorno).
- `UniqueConstraint` en `Rating (user, book)`.
- Suite de pruebas `pytest` + `pytest-django` (34 pruebas) y `ruff`.
- `Dockerfile`, `docker-compose.yml` (app + `pgvector/pgvector:pg17`) y
  `docker-entrypoint.sh`.
- CI/CD: GitHub Actions (tests con Postgres 17 + pgvector, ruff, pytest;
  `pip-audit` en PR y semanal) y Dependabot semanal.
- `docs/DATA.md` (procedencia y regeneración de datos),
  `elliot/README.md`, `sanity_check.py` (verificación de humo) y
  `scripts/build_predictions.py`.
- `CONTRIBUTING.md` con el modelo Git Flow y este `CHANGELOG.md`.

### Cambiado

- Django 5.1 → **6.0** (Python ≥ 3.12, `psycopg2-binary`, `gunicorn`,
  `whitenoise`).
- La configuración sensible (secret key, base de datos) se lee de
  variables de entorno; en producción son obligatorias (fail fast).
- Cabeceras de seguridad, cookies seguras y HSTS en producción.
- El perfil de usuario (`sum_ratings`) se recalcula con
  `select_for_update` en las señales, sin estado global.
- `populate` corregido (deduplicación de autores y palabras clave,
  `sum_ratings` por SQL) y comando `recompute_recommendations` arreglado.
- `elliot/requirements.txt`: commit fijado del paquete Elliot, sin
  TensorFlow.
- `Makefile` reescrito (venv, test, lint, docker, …).

### Eliminado

- Whoosh / `django-haystack` (sustituido por FTS de PostgreSQL).
- Embeddings picklados en `BinaryField` (sustituidos por `pgvector`).
- Archivos de datos grandes des-versionados (~306 MB: `books_raw.pkl`,
  `ratings.csv`, `datasets/training/*.tsv`); ver `docs/DATA.md`.
- `xrecommender/makefile` y `xrecommender/build.sh` (credenciales
  hardcodeadas), `elliot/reqs.txt`, `search_indexes.py` y
  `static/application/js/discover.js`.

## [1.0.0] - 2026-04-04

Estado original del repositorio (Django 5.1.15, Whoosh 2.7.4,
`django-haystack`, datos versionados en git). Tag añadida
retrospectivamente para anclar la línea de versiones.
