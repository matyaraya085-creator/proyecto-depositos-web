"""
Django settings for configuracion project.
"""

import os
import dj_database_url
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ==============================================================================
# CONFIGURACIÓN DE SEGURIDAD
# ==============================================================================

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-wen=v2c$auxqc%spa_!8)fpxq!nlud0wo&4@f%-7+*-c00y1cq"

# SECURITY WARNING: don't run with debug turned on in production!
# En tu PC será True. En Render debes configurar la variable DEBUG = 'False'
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = [
    '127.0.0.1',  # Localhost
    'localhost',  # Localhost
]

# Configuración automática para Render.com
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)


# ==============================================================================
# APLICACIONES INSTALADAS
# ==============================================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    
    # Tus aplicaciones
    'gestion',
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # <--- OBLIGATORIO PARA RENDER
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "configuracion.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "configuracion.wsgi.application"


# ==============================================================================
# BASE DE DATOS (MEJORADO)
# ==============================================================================
# Esta configuración detecta automáticamente si estás en Render (PostgreSQL)
# o en tu computador (SQLite). No fallará si no tienes internet o variables definidas.

DATABASES = {
    'default': dj_database_url.config(
        # Si no encuentra una base de datos externa, usa este archivo local:
        default='sqlite:///' + os.path.join(BASE_DIR, 'db.sqlite3'),
        conn_max_age=600
    )
}


# ==============================================================================
# VALIDACIÓN DE CONTRASEÑAS
# ==============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# ==============================================================================
# IDIOMA Y ZONA HORARIA (CHILE)
# ==============================================================================

LANGUAGE_CODE = "es-cl"        # Español de Chile

TIME_ZONE = "America/Santiago" # Hora de Chile (Importante para los registros)

USE_I18N = True

USE_TZ = True


# ==============================================================================
# ARCHIVOS ESTÁTICOS (CSS, JS, IMÁGENES)
# ==============================================================================

STATIC_URL = '/static/'

# 1. Carpeta donde tú pones los archivos mientras desarrollas
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# 2. Carpeta donde Render reunirá todos los archivos (no tocar)
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# 3. Motor de almacenamiento para producción (WhiteNoise)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ==============================================================================
# REDIRECCIONES DE LOGIN / LOGOUT
# ==============================================================================

# Al iniciar sesión correctamente, ir al Dashboard Principal
LOGIN_REDIRECT_URL = 'home'

# Al cerrar sesión, volver al formulario de Login
LOGOUT_REDIRECT_URL = 'login'

# Si intenta entrar sin permiso, mandar al Login
LOGIN_URL = 'login'