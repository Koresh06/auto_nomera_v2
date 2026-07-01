# auto_nomera_v2

Telegram-бот для размещения объявлений о продаже/покупке автомобильных номеров.

## Стек

- Python 3.12, aiogram 3, aiogram-dialog
- SQLAlchemy 2.0 async + PostgreSQL
- Redis (холд слотов, FSM-хранилище диалогов)
- Taskiq (воркер + планировщик)
- dishka (dependency injection)
- uv (управление зависимостями)

## Архитектура

Clean Architecture + DDD: `domain → application → infrastructure → presentation`

Все диалоги используют `aiogram-dialog` с Redis-safe `dialog_data` (только примитивы — id, строки, числа; доменные объекты не хранятся напрямую).

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
APP_CONFIG__TELEGRAM__ADMIN_IDS=123456789,987654321

APP_CONFIG__DB__POSTGRES__DSN=postgresql+asyncpg://user:pass@localhost:5432/db
APP_CONFIG__DB__REDIS__URL=redis://localhost:6379/0
APP_CONFIG__DB__REDIS__TASKIQ_URL=redis://localhost:6379/1

APP_CONFIG__PAYMENT__YOOKASSA__SHOP_ID=
APP_CONFIG__PAYMENT__YOOKASSA__SECRET_KEY=
```

## Функциональность

### Объявления

- Продажа, покупка, срочный выкуп, магазин номеров (`AdType.SALE / BUY / URGENT_BUYOUT / STORE`)
- Повторная публикация без повторного ввода данных (`reuse_ad`)
- Редактирование до и после публикации (номер, город, цена, телефон)
- При смене номера автоматически перегенерируется изображение и обновляется в канале
- Лимиты: 5 публикаций за 7 дней, интервал 7 дней для одного номера (настраивается per-region)

### Магазин номеров (STORE)

- Один `Ad` с `ad_type=STORE` — постоянный магазин пользователя в регионе
- Создание магазина: название, город, телефон
- Массовое добавление номеров в формате `номер-цена` (построчно), лимит ~83 шт. на пост Telegram
- Редактирование данных магазина (название / город / телефон)
- Редактирование отдельных номеров: изменение номера, цены, удаление
- Публикация магазина через тот же механизм слотов и платных услуг, что и обычные объявления
- Многократные публикации одного магазина — каждая независима, все видны в "Мои объявления"

### Срочный выкуп (URGENT_BUYOUT)

- Укороченный флоу без выбора слота и города: номер → фото → цена → подтверждение
- Заявка уходит на модерацию администраторам с фото и кнопками "Одобрить" / "Отклонить"
- Защита от race condition: если заявку уже обработал другой админ, второй получает уведомление
- После одобрения объявление становится доступно в каталоге раннего доступа
- Рассылка подписчикам выполняется асинхронно через Taskiq

### Каталог раннего доступа (PRE_PUBLICATION)

- Доступен пользователям с активной подпиской `pre_publication_expires_at`
- Объединяет одобренные заявки на срочный выкуп и публикации, выходящие в ближайшие N часов
- Кастомная пагинация по одной карточке с кольцевой навигацией
- Текст карточки идентичен тому, что увидят в канале (`AdTextRenderer`)
- Фильтрация по региону

### Слоты и календарь

- Календарь слотов с холдом на 15 минут (Redis TTL)
- Системные платные слоты (первые N — настраивается per-region)
- Конвертируемые слоты — бесплатно только первый раз; после подтверждения публикации слот навсегда помечается платным
- При отказе от слота ("Назад") холд снимается явно; если слот был оплачен с баланса — деньги не возвращаются, converted-запись очищается
- Перед финальным подтверждением повторно проверяется актуальность холда; при истечении — пользователь возвращается на календарь
- Дедупликация: для серии автопубликации в "Мои объявления" показывается одна карточка (по первой публикации с AUTOPUBLISH)

### Платные услуги (паттерн Стратегия)

- **HIGHLIGHT** — красная рамка на фото (наложение через Pillow)
- **PIN** — закрепление в канале на N дней с автоматическим откреплением по таймеру
- **AUTOPUBLISH** — публикация N дней подряд; дочерние публикации создаются после первой
- **PRIORITY_PUBLISH** — немедленная публикация вне очереди
- **PRE_PUBLICATION** — подписка на каталог раннего доступа

Покупка услуг: с баланса (мгновенно) или через платёжный провайдер с возвратом в диалог через `DialogTeleporter` после подтверждения.

### Оплата

- Поддержка ЮKassa, Telegram Stars, Cryptomus, ручная оплата картой
- Идемпотентный `ConfirmPaymentUseCase` — безопасная повторная обработка
- Телепорт пользователя обратно в нужный экран диалога после подтверждения оплаты (`BgManager` + `RESET_STACK`)
- Покрыты все виды покупок: пополнение баланса, услуги публикации, подписка, платные слоты

### Регионы

- Мультирегиональность с отдельными каналами
- Таймзоны, настройки слотов, лимиты публикаций — per-region
- Ссылки на чат, VK-группу, канал в MAX подключаются индивидуально

## Структура проекта

```
src/
  domain/               # сущности, value objects, доменные сервисы
    entities/           # Ad, Publication, Payment, User, Region, PublicationService
    services/           # SlotReservationService, AdTextRenderer
    value_objects/      # Price, SlotKey, Contacts, StoreContent, StoreItem
  application/          # use cases, порты, медиатор, DTO
    use_cases/          # сгруппированы по контексту (ad, publication, store, payment, slots...)
    dtos/               # AdDTO, PublicationDTO, PublicationServiceDTO
    mediator.py
  infrastructure/       # БД, Redis, Telegram, Taskiq, seeds
    repositories/       # SQLAlchemy-реализации
    payment/providers/  # ЮKassa, Stars, Cryptomus, manual_card
    tasks/              # Taskiq-очередь и планировщик
  presentation/
    telegram/
      features/
        user/
          modules/      # ad, store, paid_services, payment, balance, menu...
          shared/       # общие хендлеры (on_pick_slot, on_service_paid_selected)
        admin/          # модерация срочного выкупа, управление регионами
      utils/            # валидаторы цен и номеров
  core/                 # конфиг, DI-провайдеры
```

## Docker

```bash
docker compose up -d postgres redis
```