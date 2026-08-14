"""
Django settings for the fhir_portal project.

All secrets and environment-specific values are sourced from environment
variables so the same image can be promoted across dev/staging/prod without
rebuilds. See `.env.example` for the required keys.
"""
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent


def _env(key, default=None, required=False):
    # Small helper so misconfigurations fail loudly at boot instead of at
    # first request. Kept local to avoid pulling in django-environ.
    value = os.environ.get(key, default)
    if required and (value is None or value == ''):
        raise RuntimeError(
            f"Required environment variable '{key}' is not set")
    return value


def _env_bool(key, default=False):
    raw = os.environ.get(key)
    if raw is None:
        return default
    return raw.strip().lower() in ('1', 'true', 'yes', 'on')


def _env_list(key, default=None, separator=','):
    raw = os.environ.get(key)
    if not raw:
        return list(default or [])
    return [item.strip() for item in raw.split(separator) if item.strip()]


# SECURITY: never fall back to a hardcoded key outside DEBUG mode.
DEBUG = _env_bool('DJANGO_DEBUG', default=False)
SECRET_KEY = _env(
    'DJANGO_SECRET_KEY',
    default='insecure-dev-key-change-me' if DEBUG else None,
    required=not DEBUG,
)

ALLOWED_HOSTS = _env_list(
    'DJANGO_ALLOWED_HOSTS',
    default=['localhost', '127.0.0.1'] if DEBUG else [],
)


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'rest_framework',
    'drf_spectacular',

    # Local
    'app.apps.AppConfig',
]


REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
    # API is intentionally open for the OSS demo; layer auth on top in
    # deployments that need it.
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
    # OpenAPI schema generator used by drf-spectacular.
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}


# drf-spectacular: metadata for the generated OpenAPI 3 document + Swagger UI.
SPECTACULAR_SETTINGS = {
    'TITLE': 'FHIR Patient Portal API',
    'DESCRIPTION': (
        'Open-source FHIR R4 Patient Portal demo. All request and response '
        'bodies conform to the FHIR R4 JSON representation of the named '
        'resource; list endpoints return a `Bundle` of type `searchset`.'
    ),
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    # Our viewsets accept opaque FHIR JSON rather than DRF-typed fields, so
    # suppress the "could not resolve serializer" warnings that would fire
    # for every endpoint.
    'DISABLE_ERRORS_AND_WARNINGS': True,
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'fhir_portal.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'fhir_portal.wsgi.application'
ASGI_APPLICATION = 'fhir_portal.asgi.application'


# Database is always PostgreSQL; the credentials must be injected by the
# orchestrator (docker-compose, k8s secret, etc.) rather than committed.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': _env('POSTGRES_DB', required=True),
        'USER': _env('POSTGRES_USER', required=True),
        'PASSWORD': _env('POSTGRES_PASSWORD', required=True),
        'HOST': _env('POSTGRES_HOST', default='db'),
        'PORT': _env('POSTGRES_PORT', default='5432'),
        'CONN_MAX_AGE': int(_env('POSTGRES_CONN_MAX_AGE', default='60')),
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


LANGUAGE_CODE = 'en-us'
TIME_ZONE = _env('DJANGO_TIME_ZONE', default='UTC')
USE_I18N = True
USE_TZ = True


STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Hardened defaults when running behind Nginx/TLS in non-DEBUG environments.
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(_env('DJANGO_HSTS_SECONDS', default='3600'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '[%(asctime)s] %(levelname)s %(name)s: %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': _env('DJANGO_LOG_LEVEL', default='INFO'),
    },
}
