"""
Django settings for the xrecommender project.

Toda la configuración sensible se lee de variables de entorno. Ver
`.env.example` en la raíz del repositorio para la lista completa.

En producción, `SECRET_KEY` y `DATABASE_URL` son obligatorias; si faltan,
el arranque falla de forma explícita (fail fast).
"""

import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def env_str(name: str, default: str | None = None) -> str | None:
    """Lee una variable de entorno de texto."""
    return os.environ.get(name, default)


def env_bool(name: str, default: bool = False) -> bool:
    """Lee una variable de entorno booleana (true/1/yes)."""
    return os.environ.get(name, str(default)).strip().lower() in ('true', 't', '1', 'yes')


def env_list(name: str, default: list[str] | None = None) -> list[str]:
    """Lee una variable de entorno como lista separada por comas."""
    raw = os.environ.get(name)
    if raw is None:
        return list(default or [])
    return [item.strip() for item in raw.split(',') if item.strip()]


# --- Seguridad -------------------------------------------------------------
DEBUG = env_bool('DEBUG', False)

SECRET_KEY = env_str('SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        # Clave solo para desarrollo local. Nunca usar en producción.
        SECRET_KEY = 'django-insecure-dev-only-set-the-secret-key-env-var'
    else:
        raise ImproperlyConfigured(
            'SECRET_KEY es obligatoria en producción. '
            'Defina la variable de entorno SECRET_KEY.'
        )

ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', ['localhost', '127.0.0.1'])
# Render (u otra PaaS) fija esta variable con el hostname público.
RENDER_EXTERNAL_HOSTNAME = env_str('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# Cabeceras de seguridad para producción (desactivadas con DEBUG).
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_PROXY_SSL_HEADER = (
    ('HTTP_X_FORWARDED_PROTO', 'https') if not DEBUG else None
)
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Orígenes permitidos para CSRF, p. ej. 'https://app.example.com'.
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS')

# --- Aplicaciones ----------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',
    'application.apps.ApplicationConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'xrecommender.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'xrecommender.wsgi.application'

# --- Base de datos ---------------------------------------------------------
DATABASE_URL = env_str('DATABASE_URL')
if not DATABASE_URL:
    if DEBUG:
        # Por defecto para desarrollo local (sin credenciales en el repo).
        # El servidor local usa autenticación de confianza para postgres.
        DATABASE_URL = 'postgres://postgres@localhost:5432/xrecommender_dev'
    else:
        raise ImproperlyConfigured(
            'DATABASE_URL es obligatoria en producción. '
            'Defina la variable de entorno DATABASE_URL.'
        )

DATABASES = {
    'default': dj_database_url.config(default=DATABASE_URL, conn_max_age=600),
}
DEFAULT_TIMEOUT = 30

# --- Autenticación ----------------------------------------------------------
AUTH_USER_MODEL = 'application.User'

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# --- Internacionalización ----------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# --- Archivos estáticos ------------------------------------------------------
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': (
            'whitenoise.storage.CompressedManifestStaticFilesStorage'
            if not DEBUG
            else 'django.contrib.staticfiles.storage.StaticFilesStorage'
        ),
    },
}

# --- Correo ------------------------------------------------------------------
EMAIL_BACKEND = env_str(
    'EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend'
)

# --- Logs --------------------------------------------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {'format': '{levelname} {name}: {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'simple'},
    },
    'root': {'handlers': ['console'], 'level': 'INFO'},
}
