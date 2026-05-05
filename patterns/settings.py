"""Django settings for the Kafka microservices demo."""

from __future__ import annotations

import os

from common.settings import (
    ALLOWED_HOSTS,
    BASE_DIR,
    DEBUG,
    DATABASE_ENGINE,
    INSTALLED_APPS_COMMON,
    MIDDLEWARE_COMMON,
    SECRET_KEY,
    TEMPLATES_COMMON,
)

SERVICE_NAME = os.getenv("SERVICE_NAME", "ordering")

INSTALLED_APPS = INSTALLED_APPS_COMMON + [
    "common",
    "ordering",
    "billing",
    "inventory",
    "shipping",
    "notification",
]
MIDDLEWARE = MIDDLEWARE_COMMON
ROOT_URLCONF = f"patterns.urls_{SERVICE_NAME}"
TEMPLATES = TEMPLATES_COMMON
WSGI_APPLICATION = "patterns.wsgi.application"

DATABASES = {
    "commercial": {
        "ENGINE": DATABASE_ENGINE,
        "NAME": os.getenv("ORDERING_DB_NAME", "commercial_db"),
        "USER": os.getenv("ORDERING_DB_USER", "postgres"),
        "PASSWORD": os.getenv("ORDERING_DB_PASSWORD", ""),
        "HOST": os.getenv("ORDERING_DB_HOST", "localhost"),
        "PORT": os.getenv("ORDERING_DB_PORT", "5432"),
        "OPTIONS": {
            "use_iam_auth": os.getenv("USE_IAM_AUTH", "False") == "True",
            "aws_region": os.getenv("AWS_REGION", "us-east-2"),
        }
    },
    "logistics": {
        "ENGINE": DATABASE_ENGINE,
        "NAME": os.getenv("LOGISTICS_DB_NAME", "logistics_db"),
        "USER": os.getenv("LOGISTICS_DB_USER", "postgres"),
        "PASSWORD": os.getenv("LOGISTICS_DB_PASSWORD", ""),
        "HOST": os.getenv("LOGISTICS_DB_HOST", "localhost"),
        "PORT": os.getenv("LOGISTICS_DB_PORT", "5432"),
        "OPTIONS": {
            "use_iam_auth": os.getenv("USE_IAM_AUTH", "False") == "True",
            "aws_region": os.getenv("AWS_REGION", "us-east-2"),
        }
    },
    "default": {
        "ENGINE": DATABASE_ENGINE,
        "NAME": os.getenv("ORDERING_DB_NAME", "commercial_db"),
        "USER": os.getenv("ORDERING_DB_USER", "postgres"),
        "PASSWORD": os.getenv("ORDERING_DB_PASSWORD", ""),
        "HOST": os.getenv("ORDERING_DB_HOST", "localhost"),
        "PORT": os.getenv("ORDERING_DB_PORT", "5432"),
        "OPTIONS": {
            "use_iam_auth": os.getenv("USE_IAM_AUTH", "False") == "True",
            "aws_region": os.getenv("AWS_REGION", "us-east-2"),
        }
    },
}

DATABASE_ROUTERS = ["common.db_router.DomainDatabaseRouter"]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "standard"}},
    "root": {"handlers": ["console"], "level": os.getenv("LOG_LEVEL", "INFO")},
}
