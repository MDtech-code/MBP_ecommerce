# config/logging.py

from settings import BASE_DIR

LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

APPS = [
    'accounts', 'analytics', 'cart', 'common', 'contact', 'core',
    'coupons', 'logistics', 'notifications', 'orders', 'payments',
    'products', 'recommendations', 'returns', 'reviews', 'tax', 'wishlist',
]

# Shared formatter
FORMATTERS = {
    'verbose': {
        'format': '[{asctime}] {levelname} {name} {message}',
        'style': '{',
        'datefmt': '%Y-%m-%d %H:%M:%S',
    },
}

# Base handlers
HANDLERS = {
    'console': {
        'class': 'logging.StreamHandler',
        'formatter': 'verbose',
        'level': 'DEBUG',
    },
    'file': {
        'class': 'logging.FileHandler',
        'filename': str(LOGS_DIR / 'django.log'),
        'formatter': 'verbose',
        'level': 'DEBUG',
    },
}

for app in APPS:
    HANDLERS[f'{app}_file'] = {
        'level': 'INFO',
        'class': 'logging.FileHandler',
        'filename': str(LOGS_DIR / f'{app}.log'),
        'formatter': 'verbose',
    }


LOGGERS = {
    f'apps.{app}': {
        'handlers': ['console', f'{app}_file'],
        'level': 'DEBUG',
        'propagate': False,
    }
    for app in APPS
}


LOGGERS.update({
    'celery': {'handlers': ['console', 'file'], 'level': 'INFO', 'propagate': False},
    'django': {'handlers': ['console', 'file'], 'level': 'INFO', 'propagate': False},
    '':       {'handlers': ['console', 'file'], 'level': 'WARNING'},
})

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': FORMATTERS,
    'handlers': HANDLERS,
    'loggers': LOGGERS,
}
