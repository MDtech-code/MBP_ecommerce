import os
from pathlib import Path
import environ
env=environ.Env()


#________ django project directory path and read .env file 
BASE_DIR = Path(__file__).resolve().parent.parent
environ.Env.read_env(BASE_DIR / ".env")


# ─── Core ────────────────────────────────────────────
SECRET_KEY = env('SECRET_KEY')
DEBUG = env.bool('DEBUG',default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False



# ______ Django-debug tool bar config _________________________
INTERNAL_IPS = [
    "127.0.0.1",
    "localhost",
]
# Detect Docker internal IPs
import socket
try:
    hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
    INTERNAL_IPS += [ip[:-1] + "1" for ip in ips]
except Exception:
    pass



# ─── Apps ────────────────────────────────────────────

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    'django.contrib.sessions',       
    'django.contrib.messages', 
    # Third party
    'rest_framework',
    'corsheaders',
    'debug_toolbar',
    'django_extensions',
    'integration_test',
    'drf_spectacular',
]

MIDDLEWARE = [
    # 1. Third‑party / cross‑origin
    'corsheaders.middleware.CorsMiddleware',

    # 2. Security 
    'django.middleware.security.SecurityMiddleware',
    # 3. serve static file before gunicorn
    "whitenoise.middleware.WhiteNoiseMiddleware",
    # 4. common protections
    'django.middleware.common.CommonMiddleware',

    # 5. Session & authentication (needed for admin)
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',

    # 6. CSRF & messages (needed for forms/admin)
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',

    # 7. Clickjacking protection
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    # 8. Debug Toolbar (only in DEBUG mode)
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]


# ─── Templates (admin only) ───────────────────────────
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

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'



# ─── Database ─────────────────────────────────────────

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB"),
        "USER": env("POSTGRES_USER"),
        "PASSWORD": env("POSTGRES_PASSWORD"),
        "HOST": env('POSTGRES_HOST', default='localhost'),
        "PORT": env("POSTGRES_PORT", default="5432"),
    }
}


# ─── Auth & Password ──────────────────────────────────

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
# ─── DRF ─────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 12,
}
# ─── CORS ─────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[
    'http://localhost:5173',   # Vite dev
    'http://localhost:3000',
])
# ─── JWT ──────────────────────────────────────────────
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
}

# ─── Internationalisation ─────────────────────────────

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─── Static & Media ───────────────────────────────────

STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'



# ─── Redis Cache ──────────────────────────────────────
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': env('REDIS_URL', default='redis://127.0.0.1:6380/0'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# ─── Celery ───────────────────────────────────────────
CELERY_BROKER_URL = env('REDIS_URL', default='redis://127.0.0.1:6380/0')
CELERY_RESULT_BACKEND = env('REDIS_URL', default='redis://127.0.0.1:6380/0')
BROKER_TRANSPORT_OPTIONS = {"protocol": 2}
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_TIMEZONE = 'Asia/Karachi'