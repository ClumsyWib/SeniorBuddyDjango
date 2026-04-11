"""
# ==============================================================================
# FILE: settings.py
# PURPOSE: Global Configuration for the Django Backend.
#
# This file controls how the entire Django project behaves. It defines what apps 
# are installed, how to connect to the database, security settings, and CORS 
# (allowing the Flutter app to talk to the backend).
#
# KEY EXAM CONCEPTS:
# 1. INSTALLED_APPS: Lists all the modules running in this project, including 
#    our own 'senior_care' app and 'rest_framework' for building APIs.
# 2. DATABASES: Currently using SQLite3 for development. In a real-world scenario, 
#    this would be changed to PostgreSQL or MySQL.
# 3. CORS_ALLOWED_ORIGINS: Security feature that specifies which domains or 
#    apps are allowed to make requests to this backend.
# ==============================================================================

Django settings for Senior Care Backend
"""

import os
from pathlib import Path

# --------------------------------------------------
# Base Directory
# --------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent


# --------------------------------------------------
# Security Settings
# --------------------------------------------------
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-change-this-in-production-xyz123',
)

# Default to dev-friendly behavior, but allow overrides for deployments.
DEBUG = os.environ.get('DJANGO_DEBUG', '1').lower() in {'1', 'true', 'yes'}

# ALLOW ALL HOSTS for development so phone/emulator can connect
ALLOWED_HOSTS = ['*']


# --------------------------------------------------
# Installed Applications
# --------------------------------------------------
INSTALLED_APPS = [
    # Django default apps
    'unfold',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'django_filters',

    # Your apps
    'senior_care',
]


# --------------------------------------------------
# Middleware
# --------------------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


ROOT_URLCONF = 'backend.urls'

WSGI_APPLICATION = 'backend.wsgi.application'


# --------------------------------------------------
# Templates
# --------------------------------------------------
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


# --------------------------------------------------
# Database (SQLite for Development) -> Changed to MySQL
# --------------------------------------------------
from decouple import config

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('DB_NAME', default='my_django_db'),
        'USER': config('DB_USER', default='django_user'),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='3306'),
    }
}

# Production Example (PostgreSQL)
"""
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'senior_care_db',
        'USER': 'your_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
"""


# --------------------------------------------------
# Custom User Model
# --------------------------------------------------
AUTH_USER_MODEL = 'senior_care.User'


# --------------------------------------------------
# Password Validation
# --------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 6}
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# --------------------------------------------------
# Internationalization
# --------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True


# --------------------------------------------------
# Static & Media Files
# --------------------------------------------------
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# --------------------------------------------------
# Default Primary Key
# --------------------------------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# --------------------------------------------------
# Django REST Framework
# --------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
}


# --------------------------------------------------
# CORS Settings (For Flutter / React Frontend)
# --------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = True  # Disable in production

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8080",
]


# --------------------------------------------------
# Email (Development)
# --------------------------------------------------
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('EMAIL_HOST_USER', default='')


# --------------------------------------------------
# Unfold Admin Theme Settings
# --------------------------------------------------
UNFOLD = {
    "SITE_TITLE": "Senior Buddy",
    "SITE_HEADER": "Senior Buddy Admin",
    "SITE_URL": "/",
    "SITE_ICON": {
        "light": "https://img.icons8.com/color/48/000000/elderly-person.png",
        "dark": "https://img.icons8.com/color/48/000000/elderly-person.png",
    },
    "COLORS": {
        "primary": {
            "50": "250 253 255",
            "100": "240 249 255",
            "200": "224 242 254",
            "300": "186 230 253",
            "400": "125 211 252",
            "500": "56 189 248",
            "600": "14 165 233",
            "700": "2 132 199",
            "800": "3 105 161",
            "900": "12 74 110",
        },
    },
}
