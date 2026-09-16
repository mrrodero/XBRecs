# XBRecs — Sistema recomendador de libros

Sistema recomendador de libros basado en **Django 6**, **PostgreSQL 17**
(con [pgvector](https://github.com/pgvector/pgvector)) y **SBERT**.
Recomienda libros con un modelo *user-user* (KNN sobre embeddings),
explica sus recomendaciones (XAI) y evalúa el modelo con
[Elliot](https://github.com/sisinflab/elliot).

## Características

- **Recomendaciones colaborativas precalculadas**: KNN user-user sobre
  embeddings SBERT (768 dims) con búsqueda ANN (`pgvector`), persistidas
  en base de datos y recalculadas ante cada cambio de valoración.
- **Cold start**: usuarios con pocas valoraciones reciben recomendaciones
  por contenido (palabras clave compartidas) o por popularidad.
- **Búsqueda a texto completo** con PostgreSQL FTS (`tsvector` + GIN,
  `ts_rank`, `ts_headline`), sin Whoosh/haystack.
- **Explicabilidad (XAI)**: explicaciones por palabras clave compartidas
  con grafo interactivo (pyvis) y, opcionalmente, explicaciones en
  lenguaje natural generadas por un LLM (API compatible con OpenAI).
- **Evaluación reproducible** con Elliot (`ProxyRecommender`):
  nDCG, Precision, Recall, HR, MAP, MAR, MRR, ItemCoverage, EFD, EPC,
  Gini.
- **Calidad**: suite de pruebas (pytest + pytest-django), lint (ruff),
  auditoría de dependencias (pip-audit), CI/CD (GitHub Actions) y
  Docker.

## Requisitos

- Python **3.13**
- PostgreSQL **17** con la extensión `vector` (pgvector)
- (Opcional) Docker y Docker Compose

## Puesta en marcha (local)

```bash
# 1. Entorno virtual y dependencias
make venv
make install-dev

# 2. Variables de entorno (o copia .env.example a .env)
export DEBUG=1
export DATABASE_URL=postgres://postgres@localhost:5432/xrecommender_dev

# 3. Migraciones (crean la extensión vector, los índices HNSW y GIN)
make migrate

# 4. Datos (ver docs/DATA.md para la procedencia de los archivos)
make populate

# 5. Superusuario de prueba
make superuser

# 6. Servidor
make runserver
```

La web queda en <http://localhost:8000>. Crea un perfil, valora libros
(estrellas 1–5) y visita la vista de recomendaciones.

## Puesta en marcha (Docker)

```bash
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(50))")
docker compose up --build
```

Levanta la aplicación (gunicorn + whitenoise) y PostgreSQL con pgvector.
La app queda en <http://localhost:8000>.

## Configuración

Todas las opciones se configuran por variables de entorno (ver
[`.env.example`](.env.example)):

| Variable | Descripción |
| --- | --- |
| `SECRET_KEY` | Clave secreta de Django (obligatoria en producción). |
| `DATABASE_URL` | URL de PostgreSQL (obligatoria en producción). |
| `DEBUG` | `1` en desarrollo; `0` en producción. |
| `ALLOWED_HOSTS` | Hosts permitidos (coma separada). |
| `RENDER_EXTERNAL_HOSTNAME` | Hostname público para URLs absolutas. |
| `CSRF_TRUSTED_ORIGINS` | Orígenes de confianza para CSRF. |
| `SECURE_PROXY_SSL_HEADER` | Cabecera TLS si hay proxy (nginx/ALB). |
| `LLM_API_KEY` / `LLM_API_BASE` / `LLM_MODEL` | LLM opcional para explicaciones. |

En producción la app sirve los estáticos con whitenoise y activa
cabeceras de seguridad (HSTS, cookies seguras, redirección SSL).

## Datos

Ver [`docs/DATA.md`](docs/DATA.md): procedencia (GoodBooks-10k),
tamaños, cómo regenerar cada archivo (`scripts/`) y cómo cargarlo en la
base de datos (`make populate`).

## Pruebas y calidad

```bash
make test      # pytest (34 pruebas)
make lint      # ruff
```

- **CI** (`.github/workflows/test.yml`): PostgreSQL 17 + pgvector como
  servicio, ruff y pytest en cada PR.
- **Seguridad** (`.github/workflows/security.yml`): `pip-audit` en cada
  PR y semanalmente.
- **Dependabot**: actualizaciones semanales de dependencias y acciones.

## Flujo de desarrollo

El repositorio sigue el modelo **Git Flow**: `main` (producción, con tag
por release), `develop` (integración), y ramas `feature/*`, `release/*` y
`hotfix/*`. Ver [`CONTRIBUTING.md`](CONTRIBUTING.md) para el ciclo
completo y [`CHANGELOG.md`](CHANGELOG.md) para el historial de
versiones.

## Evaluación con Elliot

Ver [`elliot/README.md`](elliot/README.md). Resumen:

```bash
python scripts/build_predictions.py   # genera predictions_cf_100_35.tsv
cd elliot && python experiment.py     # evalúa con Elliot
```

## Estructura del proyecto

```
├── xrecommender/          # Aplicación Django
│   ├── application/       # Modelo, recomendador, XAI, vistas, tests
│   │   ├── models.py      # Book, User, Rating, Recommendation, Explanation
│   │   ├── recommend.py   # KNN ANN (pgvector), cold start, precomputación
│   │   ├── xai.py         # Explicaciones (keywords / LLM) y grafo pyvis
│   │   └── tests/         # Suite pytest
│   ├── templates/         # Plantillas (búsqueda FTS, recomendaciones)
│   └── xrecommender/      # settings, urls, wsgi/asgi
├── scripts/               # Pipelines de datos (fetch, embeddings, perfiles, keywords, predicciones)
├── elliot/                # Configuración de evaluación (Elliot)
├── datasets/              # Datos (no versionados; ver docs/DATA.md)
├── models/                # Perfiles de usuario (no versionado)
├── notebooks/             # Notebooks de análisis originales
├── docs/                  # Documentación (DATA.md)
├── Dockerfile             # Imagen de la aplicación
├── docker-compose.yml     # App + PostgreSQL (pgvector)
└── Makefile               # Tareas de desarrollo
```

## Licencia

[BSD 3-Clause](LICENSE).
