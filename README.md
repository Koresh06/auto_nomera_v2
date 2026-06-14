# auto_nomera_v2

Telegram-бот для размещения объявлений о продаже/покупке автомобильных номеров.

## Стек

- Python 3.12, aiogram 3, aiogram-dialog
- SQLAlchemy 2.0 async + PostgreSQL
- Redis (холд слотов, очередь задач)
- Taskiq (воркер + планировщик)
- dishka (dependency injection)
- uv (управление зависимостями)

## Архитектура

Clean Architecture + DDD: `domain → application → infrastructure → presentation`

## Запуск

```bash
# зависимости
uv sync

# миграции
alembic upgrade head

# бот
python -m src.presentation.telegram.app

# воркер (в отдельном терминале)
taskiq worker src.worker:broker

# планировщик (в отдельном терминале)
taskiq scheduler src.scheduler:scheduler
```

## Переменные окружения

```dotenv
APP_CONFIG__TELEGRAM__BOT_TOKEN=
APP_CONFIG__TELEGRAM__BOT_URL=https://t.me/your_bot
APP_CONFIG__TELEGRAM__BUYOUT_URL=https://t.me/your_buyout

APP_CONFIG__DB__POSTGRES__DSN=postgresql+asyncpg://user:pass@localhost:5432/db
APP_CONFIG__DB__REDIS__URL=redis://localhost:6379/0
APP_CONFIG__DB__REDIS__TASKIQ_URL=redis://localhost:6379/1
```

## Функциональность

**Объявления**
- Продажа, покупка, срочный выкуп, магазин номеров
- Повторная публикация без повторного ввода данных
- Редактирование до и после публикации
- Лимиты: 5 публикаций за 7 дней, интервал 7 дней для одного номера

**Слоты**
- Календарь слотов с холдом на 15 минут
- Платные и бесплатные слоты
- Системные платные слоты (настраиваются по региону)

**Платные услуги**
- HIGHLIGHT — красная рамка на фото
- PIN — закрепление в канале на N дней
- AUTOPUBLISH — автопубликация N дней подряд
- PRIORITY_PUBLISH — опубликовать прямо сейчас
- PRE_PUBLICATION — подписка на доступ к каталогу до публикации

**Регионы**
- Мультирегиональность с отдельными каналами
- Таймзоны, настройки слотов, лимиты — всё per-region

## Структура проекта

```
src/
  domain/               # сущности, value objects, доменные сервисы
  application/          # use cases, порты, медиатор, DTO
  infrastructure/       # БД, Redis, Telegram, Taskiq, seeds
  presentation/         # диалоги aiogram-dialog, хендлеры
  core/                 # конфиг, DI-провайдеры
```

## Docker

```bash
docker compose up -d postgres redis
```