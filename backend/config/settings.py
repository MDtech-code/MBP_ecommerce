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
CORS_ALLOW_CREDENTIALS=env.bool('CORS_ALLOW_CREDENTIALS',default=False)
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CSRF_COOKIE_SECURE = env.bool('CSRF_COOKIE_SECURE',default=False)
SESSION_COOKIE_SECURE = env.bool('SESSION_COOKIE_SECURE',default=False)



# ______ Django-debug tool bar config _________________________

INTERNAL_IPS=env.list("INTERNAL_IPS",default=['127.0.0.1','localhost'])

# Detect Docker internal IPs
import socket
try:
    hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
    INTERNAL_IPS += [ip[:-1] + "1" for ip in ips]
    #INTERNAL_IPS += [ip.rsplit(".", 1)[0] + ".1" for ip in ips]
except Exception:
    pass



# ─── Apps ────────────────────────────────────────────


DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    'django.contrib.sessions',       
    'django.contrib.messages', 
]
PROJECT_APPS = [
    'apps.core',
    'apps.common',
    'apps.accounts',
    'apps.products',
    'apps.cart',
    'apps.coupons',
    'apps.orders',
    'apps.payments',
    'apps.reviews',
    'apps.contact',
    'apps.wishlist',
    'apps.tax',
    'apps.returns',
    'apps.recomendations',
    'apps.notifications',
    'apps.logistics',
    'apps.analytics',
]
THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'debug_toolbar',
    'django_extensions',
    'drf_spectacular',
    "graphene_django",
]
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + PROJECT_APPS


MIDDLEWARE = [
    # 1. Third‑party / cross‑origin
    'corsheaders.middleware.CorsMiddleware',

    # 1.  track request unique ID
    'apps.core.middleware.RequestIDMiddleware',
    # 3. Security 
    'django.middleware.security.SecurityMiddleware',
    # 4. serve static file before gunicorn
    "whitenoise.middleware.WhiteNoiseMiddleware",
    # 5. common protections
    'django.middleware.common.CommonMiddleware',

    # 6. Session & authentication (needed for admin)
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',

    # 7. CSRF & messages (needed for forms/admin)
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',

    # 8. Clickjacking protection
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

   
]
# ─── Debug Toolbar guard ──────────────────────────────
if DEBUG:
    MIDDLEWARE.append('debug_toolbar.middleware.DebugToolbarMiddleware')


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
    },
    # ── TEMPORARY TEST DATABASE — DELETE AFTER TESTING ──────────────
    #"test_db": {
    #    "ENGINE": "django.db.backends.postgresql",
    #    "NAME": "motorbike_parts_test",        # the DB we just created
    #    "USER": env("POSTGRES_USER"),          # same user is fine
    #    "PASSWORD": env("POSTGRES_PASSWORD"),
    #    "HOST": env('POSTGRES_HOST', default='localhost'),
    #    "PORT": env("POSTGRES_PORT", default="5432"),
    #},
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
    #* Auto-generates OpenAPI schema (used by drf-spectacular for API docs)
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    #* only json render  
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
   
    #* Require all requests to be from authenticated users by default
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    #* JWT configurations 
     'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    #* Paginate results using page numbers (e.g., ?page=2) & mention page size 
    # 'DEFAULT_PAGINATION_CLASS': 'apps.core.pagination.StandardPagination',
    # 'PAGE_SIZE': 10,

    
    'DEFAULT_THROTTLE_CLASSES': [
        'apps.core.throttles.CustomAnonRateThrottle',
        'apps.core.throttles.CustomUserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        "registration": "1000/hour", 
        'anon': '1000/hour',
        'user': '1000/hour',
    },
    "EXCEPTION_HANDLER": "apps.core.api.exceptions.custom_exception_handler",
}

# ─── graphQL ─────────────────────────────────────────────
GRAPHENE = {
    "SCHEMA": "config.schema.schema"
}

# ─── CORS ─────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[
    'https://localhost:5173',   # Vite dev
])

# ─── JWT ──────────────────────────────────────────────
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ─── Google credential  ──────────────────────────────────────────────
GOOGLE_CLIENT_ID     = env("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = env("GOOGLE_CLIENT_SECRET")
# ─── facebook credential  ──────────────────────────────────────────────
FACEBOOK_APP_ID     = env("FACEBOOK_APP_ID")
FACEBOOK_APP_SECRET = env("FACEBOOK_APP_SECRET")
# ── Courier Webhook Secrets ────────────────────────────────────────────────
POSTEX_WEBHOOK_SECRET  = env("POSTEX_WEBHOOK_SECRET",  default="")
TCS_WEBHOOK_SECRET     = env("TCS_WEBHOOK_SECRET",     default="")
LEOPARDS_WEBHOOK_SECRET = env("LEOPARDS_WEBHOOK_SECRET", default="")

# ── Courier Outbound API Credentials ──────────────────────────────────────
# Set in .env after creating courier seller accounts.
# Empty string = API path disabled, falls back to manual AWB entry.

POSTEX_API_KEY      = env("POSTEX_API_KEY",      default="")
POSTEX_API_BASE_URL = env("POSTEX_API_BASE_URL",  default="")

TCS_API_KEY         = env("TCS_API_KEY",          default="")
TCS_API_BASE_URL    = env("TCS_API_BASE_URL",      default="")

LEOPARDS_API_KEY    = env("LEOPARDS_API_KEY",     default="")
LEOPARDS_API_BASE_URL = env("LEOPARDS_API_BASE_URL", default="")


# Payment gateway settings — loaded from environment
JAZZCASH_MERCHANT_ID    = env("JAZZCASH_MERCHANT_ID",    default="")
JAZZCASH_PASSWORD       = env("JAZZCASH_PASSWORD",       default="")
JAZZCASH_INTEGRITY_SALT = env("JAZZCASH_INTEGRITY_SALT", default="")

EASYPAISA_STORE_ID      = env("EASYPAISA_STORE_ID",      default="")
EASYPAISA_HASH_KEY      = env("EASYPAISA_HASH_KEY",      default="")

SAFEPAY_API_KEY         = env("SAFEPAY_API_KEY",         default="")
SAFEPAY_WEBHOOK_SECRET  = env("SAFEPAY_WEBHOOK_SECRET",  default="")

# Payment redirect/webhook base URLs
PAYMENT_RETURN_URL       = env("PAYMENT_RETURN_URL",      default="")
PAYMENT_WEBHOOK_BASE_URL = env("PAYMENT_WEBHOOK_BASE_URL", default="")
# ─── Internationalisation ─────────────────────────────

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = "accounts.User"
# ─── Static & Media ───────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {
            "location": MEDIA_ROOT,
            "base_url": MEDIA_URL,
        },
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}





# ─── Redis Cache ──────────────────────────────────────
CACHES = {
    # L2 — Redis (shared, persistent across processes)
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': env('REDIS_URL', default='redis://127.0.0.1:6380/0'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'TIMEOUT': 300,
    },
    # L1 — In-memory (per process, ultra fast, small)
    'local': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'mbp-l1-cache',
        'TIMEOUT': 60,   # shorter — memory is limited
        'OPTIONS': {
            'MAX_ENTRIES': 500   # max keys before eviction
        }
    }
}

# ─── Celery ───────────────────────────────────────────
CELERY_BROKER_URL = env('REDIS_URL', default='redis://127.0.0.1:6380/0')
CELERY_RESULT_BACKEND = env('REDIS_URL', default='redis://127.0.0.1:6380/0')

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_TIMEZONE = 'Asia/Karachi'



# ─── Email Service Configuration ──────────────────────────────────────────
#! this line of help to configore the default base email request sending 
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST =env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT =env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS =env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER =env('EMAIL_HOST_USER', default="test@example.com")
EMAIL_HOST_PASSWORD =env('EMAIL_HOST_PASSWORD',default='dummy')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

FRONTEND_URL = env('FRONTEND_URL', default='https://localhost:5173')
# ─── Sentry ───────────────────────────────────────────
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration

SENTRY_DSN = env('SENTRY_DSN', default='')

if SENTRY_DSN:
    print(SENTRY_DSN,env('SENTRY_ENVIRONMENT', default='local'))
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=env('SENTRY_ENVIRONMENT', default='local'),
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        traces_sample_rate=1.0,
        send_default_pii=False,  # don't send personal data
    )
# ─── Storage ──────────────────────────────────────────
# Production: uncomment and configure S3
# DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
# AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME')
# AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID')
# AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY')
# ─── Logging ──────────────────────────────────────────

LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'sensitive_data': {
            '()': 'apps.core.logging.SensitiveDataFilter',
        }
    },
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'integration_test_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': str(LOGS_DIR / 'integration_test.log'),
            'formatter': 'verbose',
        },
        'core_file':{
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': str(LOGS_DIR / 'core.log'),
            'formatter': 'verbose',

        },
        'accounts_file':{
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': str(LOGS_DIR / 'accounts.log'),
            'formatter': 'verbose',

        },
        'products_file': {
    'level': 'INFO',
    'class': 'logging.FileHandler',
    'filename': str(LOGS_DIR / 'products.log'),
    'formatter': 'verbose',
},
'orders_file': {
    'level': 'INFO',
    'class': 'logging.FileHandler',
    'filename': str(LOGS_DIR / 'orders.log'),
    'formatter': 'verbose',
},
'cart_file': {
    'level': 'INFO',
    'class': 'logging.FileHandler',
    'filename': str(LOGS_DIR / 'cart.log'),
    'formatter': 'verbose',
},
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'level': 'DEBUG',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': str(LOGS_DIR / 'django.log'),
            'formatter': 'verbose',
            'filters': ['sensitive_data'],
            'level': 'DEBUG',
        },
    },
    'loggers': {
    'apps.accounts': {'handlers': ['console', 'accounts_file'], 'level': 'DEBUG', 'propagate': False},
    'apps.products': {'handlers': ['console', 'products_file'], 'level': 'DEBUG', 'propagate': False},
    'apps.orders':   {'handlers': ['console', 'orders_file'],   'level': 'DEBUG', 'propagate': False},
    'apps.cart':     {'handlers': ['console', 'cart_file'],     'level': 'DEBUG', 'propagate': False},
    'apps.core':     {'handlers': ['console', 'core_file'],     'level': 'DEBUG', 'propagate': False},
    'apps.integration_test': {'handlers': ['console', 'integration_test_file'], 'level': 'DEBUG', 'propagate': False},
    'celery':        {'handlers': ['console', 'file'], 'level': 'INFO',  'propagate': False},
    'django':        {'handlers': ['console', 'file'], 'level': 'INFO',  'propagate': False},
    '':              {'handlers': ['console', 'file'], 'level': 'WARNING'},
},
}