from .base import *

# Configurações específicas de desenvolvimento
DEBUG = env.bool('DEBUG', default=True)
SECURE_SSL_REDIRECT = False

ALLOWED_HOSTS = [
    '127.0.0.1',
    'manutencaocemag.com.br',
    'www.manutencaocemag.com.br',
    'manutencaocemag-4fu7.onrender.com',
    'citysearch-revolutionary-noble-reforms.trycloudflare.com',]

CSRF_TRUSTED_ORIGINS = [
    'https://07fd-177-19-132-134.ngrok-free.app'
    'https://automatically-a-homework-applies.trycloudflare.com',
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
            'options': '-c search_path=manutencao_v3',
        },
    }
}

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Configurações adicionais para desenvolvimento (opcional)
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'
