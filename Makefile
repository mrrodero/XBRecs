# Automatización de tareas de XBRecs.
# Uso: make <target>  (ej.: make dev, make test, make docker-build)

VENV      := .venv
PYTHON    := $(VENV)/Scripts/python.exe
PIP       := $(VENV)/Scripts/python.exe -m pip
PYTEST    := $(VENV)/Scripts/python.exe -m pytest
DJANGO    := $(PYTHON) xrecommender/manage.py
APP_DIR   := xrecommender

# Por defecto, desarrollo local contra PostgreSQL.
export DEBUG        ?= 1
export DATABASE_URL ?= postgres://postgres@localhost:5432/xrecommender_dev
export DJANGO_SETTINGS_MODULE ?= xrecommender.settings

.PHONY: help venv install install-dev check migrate makemigrations migrate \
        superuser runserver populate recompute test lint format docker-build \
        docker-up docker-down

help:
	@echo "Objetivos disponibles:"
	@echo "  make venv           Crea el entorno virtual (.venv)"
	@echo "  make install        Instala dependencias de producción"
	@echo "  make install-dev    Instala dependencias de desarrollo"
	@echo "  make check          Verifica la configuración de Django"
	@echo "  make migrate        Aplica migraciones"
	@echo "  make makemigrations Genera nuevas migraciones"
	@echo "  make superuser      Crea un superusuario (pregunta usuario/pass)"
	@echo "  make runserver      Arranca el servidor de desarrollo"
	@echo "  make populate       Carga datasets/ en la base de datos"
	@echo "  make recompute      Recalcula las recomendaciones de todos los usuarios"
	@echo "  make test           Ejecuta la suite de pruebas (pytest)"
	@echo "  make lint           Lintea con ruff"
	@echo "  make format         Formatea el código con ruff"
	@echo "  make docker-build   Construye la imagen Docker"
	@echo "  make docker-up      Levanta la app + PostgreSQL (Docker Compose)"
	@echo "  make docker-down    Detiene y elimina los contenedores"

venv:
	$(PYTHON) -m venv $(VENV) || python -m venv $(VENV)

install:
	$(PIP) install -r xrecommender/requirements.txt

install-dev:
	$(PIP) install -r xrecommender/requirements-dev.txt

check:
	$(DJANGO) check

migrate:
	$(DJANGO) migrate

makemigrations:
	$(DJANGO) makemigrations application

superuser:
	$(DJANGO) createsuperuser

runserver:
	$(DJANGO) runserver 0.0.0.0:8000

populate:
	$(DJANGO) populate

recompute:
	$(DJANGO) recompute_recommendations

test:
	cd $(APP_DIR) && $(PYTEST)

lint:
	$(VENV)/Scripts/ruff.exe check xrecommender/ scripts/ elliot/

format:
	$(VENV)/Scripts/ruff.exe format xrecommender/ scripts/ elliot/

docker-build:
	docker build -t xrecommender .

docker-up:
	docker compose up --build

docker-down:
	docker compose down
