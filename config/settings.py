from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key-change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "0") == "1"

# -------------------------
# Hosts
# -------------------------
raw_hosts = os.getenv("ALLOWED_HOSTS", "")
ALLOWED_HOSTS = [
    h.strip().strip('"').strip("'")
    for h in raw_hosts.replace("\n", ",").split(",")
    if h.strip()
]

# لو نسيت تحط ALLOWED_HOSTS على Railway
if not ALLOWED_HOSTS and DEBUG:
    ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# -------------------------
# CSRF (علشان 403 بتاع الفورمات)
# -------------------------
CSRF_TRUSTED_ORIGINS = [
    "https://supervision-system-production.up.railway.app",
    "https://*.up.railway.app",
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # ✅ لازم تبقى هنا بعد SecurityMiddleware
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",
            BASE_DIR / "core" / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
# -------------------------
# Database Configuration
# -------------------------
import dj_database_url
import os

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=0, # إلغاء الـ persistent connections مؤقتاً لحل مشكلة الـ handshake
        )
    }
    DATABASES['default']['OPTIONS'] = {
        'charset': 'utf8mb4',
        'connect_timeout': 60,  # زودنا الوقت لـ 60 ثانية كاملة
        'ssl': {'ca': None}     # إلغاء فحص الـ SSL اللي ممكن يكون هو السبب
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": "supervision_db",
            "USER": "root",
            "PASSWORD": "",
            "HOST": "127.0.0.1",
            "PORT": "3306",
            "OPTIONS": {"charset": "utf8mb4"},
        }
    }
 
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ar"
TIME_ZONE = "Africa/Cairo"
USE_I18N = True
USE_TZ = True

# =========================
# Static files (WhiteNoise)
# =========================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# ✅ مهم: بلاش STATICFILES_DIRS طالما ملفاتك داخل core/static
# Django هيلمّها تلقائي من app directories

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"

CSRF_TRUSTED_ORIGINS = [
    "https://supervision-system-production.up.railway.app",
    "https://*.up.railway.app" # للسماح بأي رابط فرعي من ريل واي
]