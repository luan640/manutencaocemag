from pathlib import Path
import os
import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = env('SECRET_KEY')

AUTH_USER_MODEL = 'funcionario.Funcionario'
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]
ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'manutencaocemag.onrender.com','projeto-exec.onrender.com','manutencaocemag-4fu7.onrender.com']
LOGOUT_REDIRECT_URL = 'login'  # Redireciona para a página de login

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'cadastro',
    'execucao',
    'solicitacao',
    'funcionario',
    'home',
    'wpp',
    'preventiva',
    'dashboard',
    'storages'

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

ROOT_URLCONF = 'manutencao_project.urls'

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

WSGI_APPLICATION = 'manutencao_project.wsgi.application'

AUTH_PASSWORD_VALIDATORS = [
    # {
    #     'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    # },
    # {
    #     'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    # },
    # {
    #     'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    # },
    # {
    #     'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    # },
]

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = False
LOGIN_URL = '/login/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Static files
STATIC_URL = 'static/'  # Inclua a barra inicial para garantir que funcione bem em URLs
# STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')  # Diretório para coleta de arquivos estáticos

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static/'),   # Diretório estático principal
    os.path.join(BASE_DIR, 'home/static'),
    os.path.join(BASE_DIR, 'cadastro/static'),
    os.path.join(BASE_DIR, 'execucao/static'),
    os.path.join(BASE_DIR, 'preventiva/static'),
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Define a base URL para servir arquivos de mídia
# MEDIA_URL = '/media/'

# Define o diretório onde os arquivos de mídia serão armazenados
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        # Root logger
        '': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        # Your specific logger
        'yourapp.backends': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = env('AWS_S3_REGION_NAME')

DEFAULT_FILE_STORAGE = env('DEFAULT_FILE_STORAGE')

AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'

# Define a base URL para servir arquivos de mídia
MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/'