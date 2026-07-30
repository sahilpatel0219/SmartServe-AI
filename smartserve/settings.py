"""
SmartServe AI — Django settings.
Hybrid DB: SQLite/Postgres (auth/users) + MongoDB (operational data).
All secrets via python-decouple (.env file).
"""
import sys
from pathlib import Path
from datetime import timedelta
from decouple import config, Csv

# True while running the test suite — disables side effects like assistant
# gap/security logging so tests never touch (or slow down on) the real database.
TESTING = 'test' in sys.argv

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Security ────────────────────────────────────────────────────────────────────
SECRET_KEY = config('SECRET_KEY', default='dev-secret-key-change-in-production')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# ── Applications ────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    # local
    'core',
    'accounts',
    'onboarding',
    'catalog',
    'inventory',
    'orders',
    'customers',
    'staff',
    'suppliers',
    'analytics',
    'ml_engine',
    'assistant',
    'reports',
    'notifications',
    'api',
]

# ── Middleware ──────────────────────────────────────────────────────────────────
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

# ── CORS (React dev server) ─────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:5173,http://127.0.0.1:5173',
    cast=Csv(),
)
CORS_ALLOW_CREDENTIALS = True
# The React client sends the active-workspace id on every request; it isn't in
# django-cors-headers' default allow-list, so the browser would drop the request
# after preflight if we didn't add it here.
from corsheaders.defaults import default_headers  # noqa: E402
CORS_ALLOW_HEADERS = list(default_headers) + ['x-business-id']

ROOT_URLCONF = 'smartserve.urls'

# ── Templates ───────────────────────────────────────────────────────────────────
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
                'core.context_processors.global_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'smartserve.wsgi.application'

# ── Relational Database (auth, users, roles, subscriptions) ────────────────────
# SQLite for dev; switch to Postgres for prod via env vars.
_db_engine = config('DB_ENGINE', default='django.db.backends.sqlite3')
if _db_engine == 'django.db.backends.sqlite3':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / config('DB_NAME', default='db.sqlite3'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': _db_engine,
            'NAME': config('DB_NAME'),
            'USER': config('DB_USER', default=''),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
        }
    }

# ── MongoDB settings (accessed via mongo/client.py) ────────────────────────────
MONGO_URI = config('MONGO_URI', default='mongodb://localhost:27017')
MONGO_DB_NAME = config('MONGO_DB_NAME', default='smartserve_db')
# Set True in .env only if Atlas certificate validation fails locally (dev only)
MONGO_TLS_ALLOW_INVALID = config('MONGO_TLS_ALLOW_INVALID', default=False, cast=bool)

# ── Password Validation ─────────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── Internationalisation ────────────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# ── Static & Media ──────────────────────────────────────────────────────────────
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = config('MEDIA_URL', default='/media/')
MEDIA_ROOT = BASE_DIR / config('MEDIA_ROOT', default='media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Custom auth model ───────────────────────────────────────────────────────────
AUTH_USER_MODEL = 'accounts.User'

# ── Auth redirect URLs ──────────────────────────────────────────────────────────
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# ── Email ───────────────────────────────────────────────────────────────────────
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('EMAIL_HOST_USER', default='noreply@smartserve.ai')

# ── DRF ─────────────────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    # JWT only. The React app is the sole API client and sends a bearer token;
    # dropping SessionAuthentication means no CSRF coupling and no reliance on
    # cookies for cross-origin calls. Django's own session auth still guards
    # /admin/, which is not a DRF view.
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
    # Turns unhandled exceptions (e.g. a transient MongoDB drop) into a clean
    # JSON error instead of Django's HTML debug page leaking into the SPA.
    'EXCEPTION_HANDLER': 'api.exceptions.api_exception_handler',
}

# ── SimpleJWT ───────────────────────────────────────────────────────────────────
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
}

# ── LLM Assistant (pluggable) ───────────────────────────────────────────────────
LLM_PROVIDER = config('LLM_PROVIDER', default='')
LLM_API_KEY = config('LLM_API_KEY', default='')

# ── Session ─────────────────────────────────────────────────────────────────────
SESSION_COOKIE_AGE = 86400 * 7  # 7 days
SESSION_COOKIE_HTTPONLY = True
