from pathlib import Path
import os
import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# تحميل .env محليًا فقط (لو موجود)
load_dotenv(BASE_DIR / ".env")

# -------------------------
# Security & Debug
# -------------------------
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

# Fallback local
if not ALLOWED_HOSTS and DEBUG:
    ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# -------------------------
# CSRF Settings
# (الأفضل تخليها من ENV)
# -------------------------
raw_csrf = os.getenv("CSRF_TRUSTED_ORIGINS", "")
if raw_csrf.strip():
    CSRF_TRUSTED_ORIGINS = [
        o.strip().strip('"').strip("'")
        for o in raw_csrf.replace("\n", ",").split(",")
        if o.strip()
    ]
else:
    CSRF_TRUSTED_ORIGINS = []

# -------------------------
# Application Definition
# -------------------------
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
    "whitenoise.middleware.WhiteNoiseMiddleware",
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
# Database Configuration (Railway-safe)
# IMPORTANT:
# استخدم MYSQL_URL أولًا (الـ internal داخل Railway)
# -------------------------
DATABASE_URL = os.getenv("MYSQL_URL") or os.getenv("DATABASE_URL")

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=60,  # ✅ أفضل من 0
        )
    }

    # ✅ خيارات مهمة لاستقرار الاتصال
    DATABASES["default"]["OPTIONS"] = {
        "charset": "utf8mb4",
        "connect_timeout": 60,
        "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
    }
else:
    # Local fallback
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": os.getenv("DB_NAME", "supervision_db"),
            "USER": os.getenv("DB_USER", "root"),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", "127.0.0.1"),
            "PORT": os.getenv("DB_PORT", "3306"),
            "OPTIONS": {"charset": "utf8mb4"},
        }
    }

# -------------------------
# Authentication & Localization
# -------------------------
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

# -------------------------
# Static Files (WhiteNoise)
# -------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# -------------------------
# URLs & Auth Redirects
# -------------------------
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"