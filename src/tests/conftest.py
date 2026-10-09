"""Общие настройки для всех тестов.

Настройки приложения читаются из .env разработчика — там боевые секреты.
Тесты не должны отправлять события в реальный Sentry: переменная окружения
приоритетнее .env, поэтому выставляем её ДО первого импорта настроек.
"""

import os

os.environ["APP_CONFIG__APP__SENTRY_DSN"] = ""

from src.core.config import settings  # noqa: E402

settings.app.sentry_dsn = None
assert not settings.app.sentry_dsn
