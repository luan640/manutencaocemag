from .base import *

# Configurações específicas de desenvolvimento
DEBUG = env.bool('DEBUG', default=True)
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'b7e0-177-19-132-134.ngrok-free.app']
CSRF_TRUSTED_ORIGINS = [
    'https://b7e0-177-19-132-134.ngrok-free.app',
]

# Banco de dados para desenvolvimento
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST'),
        'PORT': env('DB_PORT'),
        'OPTIONS': {
            'options': '-c search_path=manutencao_v2',
        },
    }
}

# Configurações adicionais para desenvolvimento (opcional)
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
