# auto_nomera_v2

Telegram-бот для размещения объявлений о продаже/покупке автомобильных номеров.

## Стек

- Python 3.12, aiogram 3, aiogram-dialog
- SQLAlchemy 2.0 async + PostgreSQL
- Redis (холд слотов, FSM-хранилище диалогов, кэш блокировок)
- Taskiq (воркер + планировщик)
- dishka (dependency injection)
- uv (управление зависимостями)

## Архитектура

Clean Architecture + DDD: `domain → application → infrastructure → presentation`

Все диалоги используют `aiogram-dialog` с Redis-safe `dialog_data` (только примитивы — id, строки, числа; доменные объекты не хранятся напрямую).

Взаимодействие слоёв построено вокруг медиатора: презентация вызывает use cases через `Mediator.handle(Request)`, а не обращается к репозиториям напрямую. Фоновые задачи (публикация, откреп, рассылка, подтверждение оплаты) также резолвят use cases через медиатор внутри Taskiq-воркера.

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
APP_CONFIG__APP__APP_NAME=AutoNomera_V2
APP_CONFIG__APP__DEBUG=False
APP_CONFIG__APP__PRE_PUBLICATION_WINDOW_HOURS=2
APP_CONFIG__APP__HOLD_SLOTS_TIME=300

APP_CONFIG__TELEGRAM__BOT_TOKEN=12345
APP_CONFIG__TELEGRAM__ADMIN_IDS=[1234]
APP_CONFIG__TELEGRAM__BOT_URL=https://t.me/qwert
APP_CONFIG__TELEGRAM__BUYOUT_URL=https://t.me/qwert

APP_CONFIG__DB__POSTGRES__NAME=db
APP_CONFIG__DB__POSTGRES__PASSWORD=12345
APP_CONFIG__DB__POSTGRES__USER=user
APP_CONFIG__DB__POSTGRES__HOST=localhost
APP_CONFIG__DB__POSTGRES__PORT=5432
APP_CONFIG__DB__POSTGRES__ECHO=False

APP_CONFIG__DB__REDIS__HOST=localhost
APP_CONFIG__DB__REDIS__PORT=6379
APP_CONFIG__DB__REDIS__DB=0
APP_CONFIG__DB__REDIS__TASKIQ_DB=1

APP_CONFIG__PAYMENT__MANUAL_CARD__CARD_NUMBER=1234 5678 9012 3456
APP_CONFIG__PAYMENT__TELEGRAM_STARS__XTR_TO_RUB_RATE=1.67
APP_CONFIG__PAYMENT__YOOKASSA__ACCOUNT_ID=1111
APP_CONFIG__PAYMENT__YOOKASSA__SECRET_KEY=test_4dawSDas
APP_CONFIG__PAYMENT__YOOKASSA__RETURN_URL=https://test.ru
APP_CONFIG__PAYMENT__CRYPTOMUS__MERCHANT_ID=1231412
APP_CONFIG__PAYMENT__CRYPTOMUS__API_KEY=dwqedd2da
```

Ключевые параметры:

- `PRE_PUBLICATION_WINDOW_HOURS` — за сколько часов до публикации объявление появляется в каталоге раннего доступа.
- `HOLD_SLOTS_TIME` — время холда слота в секундах (Redis TTL).
- `ADMIN_IDS` — список Telegram ID супер-администраторов (задаётся только через конфиг, не меняется через бота).

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
- Объединяет одобренные заявки на срочный выкуп и публикации, выходящие в ближайшие N часов (`PRE_PUBLICATION_WINDOW_HOURS`)
- Скользящее окно по UTC: объявление появляется, когда до публикации остаётся ≤ N часов, и исчезает сразу после выхода в канал (смена статуса на `PUBLISHED`)
- Кастомная пагинация по одной карточке с кольцевой навигацией (`CatalogScroll`)
- Текст карточки идентичен тому, что увидят в канале (`AdTextRenderer`)
- Поддержка обычных объявлений и магазинов в одном каталоге
- Фильтрация по региону

### Слоты и календарь

- Календарь слотов с холдом (Redis TTL, `HOLD_SLOTS_TIME`)
- Системные платные слоты (первые N — настраивается per-region)
- Конвертируемые слоты — бесплатно только первый раз; после подтверждения публикации слот навсегда помечается платным
- При отказе от слота ("Назад") холд снимается явно; если слот был оплачен с баланса — деньги не возвращаются, converted-запись очищается
- Перед финальным подтверждением повторно проверяется актуальность холда; при истечении — пользователь возвращается на календарь
- Локальное время региона для выбора и отображения, UTC для хранения и планирования (`PublishTimeResolver` через `ZoneInfo`)

### Платные услуги (паттерн Стратегия)

- **HIGHLIGHT** — красная рамка на фото (наложение через Pillow)
- **PIN** — закрепление в канале на N дней с автоматическим откреплением по таймеру
- **AUTOPUBLISH** — публикация N дней подряд; дочерние публикации создаются после первой и помечаются флагом `is_child` (в списках и каталогах показывается только родительская)
- **PRIORITY_PUBLISH** — немедленная публикация вне очереди
- **PRE_PUBLICATION** — подписка на каталог раннего доступа

Покупка услуг: с баланса (мгновенно) или через платёжный провайдер с возвратом в диалог через `DialogTeleporter` после подтверждения.

### Оплата

- Поддержка ЮKassa, Telegram Stars, Cryptomus, ручная оплата картой
- Идемпотентный `ConfirmPaymentUseCase` — безопасная повторная обработка
- Телепорт пользователя обратно в нужный экран диалога после подтверждения оплаты (`BgManager` + `RESET_STACK`)
- Покрыты все виды покупок: пополнение баланса, услуги публикации, подписка, платные слоты
- Блокировка платежей на уровне пользователя (`is_payment_blocked`) — заблокированный не может создать платёж

### Регионы

- Мультирегиональность с отдельными каналами
- Таймзоны, настройки слотов, лимиты публикаций — per-region
- Ссылки на чат, VK-группу, канал в MAX подключаются индивидуально
- Статус региона (`ACTIVE / DISABLED`) — отключённый регион недоступен для новых объявлений; активные пользователи отключённого региона перенаправляются на выбор нового региона

## Админ-панель

Доступ по команде `/admin`. Разграничение прав:

- **Супер-администратор** — Telegram ID из конфига (`ADMIN_IDS`). Полный доступ, включая регионы, услуги, баланс, блокировки, назначение админов.
- **Администратор** (`UserRole.ADMIN`, назначается через бота) — операционные разделы: рассылки, статистика.

### Модули

- **Регионы** — создание, редактирование настроек слотов (времена, горизонт календаря, платные слоты, цена, лимит публикаций), соцсети/каналы, включение/отключение региона. Изменения сохраняются мгновенно.
- **Платные услуги** — редактирование прайса (цена, длительность, описание, название), включение/снятие с продажи, сброс к стандартным значениям из сидов.
- **Баланс пользователей** — поиск по Telegram ID, ручная корректировка баланса со знаком (`+500` / `-200`) через доменные методы `top_up` / `charge`.
- **Блокировка пользователей** — полная блокировка (`is_blocked`) и блокировка платежей (`is_payment_blocked`), поиск по ID и по пересланному контакту. Блокировки кэшируются в Redis (TTL) поверх БД; проверка полной блокировки в middleware на каждом апдейте.
- **Управление администраторами** — назначение/снятие роли `UserRole.ADMIN`. Супер-админы из конфига защищены от снятия через бота.
- **Рассылки** — трём типам получателей (всем пользователям / по региону / во все каналы регионов) с предпросмотром перед отправкой; выполняется асинхронно через Taskiq (`NotificationService.broadcast_copy`), с троттлингом и ретраем на flood-wait.
- **Статистика пополнений** — SQL-агрегация по методам оплаты, разбивка по регионам, топ-метод и топ-регион; фильтр по периоду (сегодня / неделя / месяц / всё время).
- **Статистика публикаций** — разбивка по статусам и типам объявлений, топ-регион, срочные выкупы учитываются отдельно (не публикуются, живут в `Ad`); расписание по датам с кликабельными ссылками на владельцев; каталог отложенных публикаций с возможностью отмены (отменяет всю серию автопубликации и снимает job из планировщика, уведомляет пользователя).

## Структура проекта

```
src/
  domain/               # сущности, value objects, доменные сервисы
    entities/           # Ad, Publication, Payment, User, Region, PublicationService, ServiceDefinition
    services/           # SlotReservationService, AdTextRenderer, RegionGuard, PublishTimeResolver
    value_objects/      # Price, SlotKey, Contacts, StoreContent, StoreItem, RegionSettings, RegionMetadata
  application/          # use cases, порты, медиатор, DTO
    use_cases/          # сгруппированы по контексту (ad, publication, store, payment, slots, stats, user, mailing...)
    dtos/               # AdDTO, PublicationDTO, PaymentStatsDTO, PublicationStatsDTO, RegionScheduleDTO...
    ports/              # RegionRepository, PaymentRepository, BlockCache, NotificationService, TaskQueue...
    mediator.py
  infrastructure/       # БД, Redis, Telegram, Taskiq, seeds
    repositories/       # SQLAlchemy-реализации
    cache/              # RedisBlockCache
    payment/providers/  # ЮKassa, Stars, Cryptomus, manual_card
    tasks/              # Taskiq-очередь и планировщик
    seeds/              # начальные данные (ServiceDefinition)
  presentation/
    telegram/
      features/
        user/
          modules/      # ad, store, paid_services, payment, balance, menu, catalog_deferred_publication...
          shared/       # общие хендлеры (on_pick_slot, on_service_paid_selected)
        admin/
          modules/      # menu, region, paid_services, balance, blocking, admin_management, mailing, stats
      middlewares/      # проверка блокировки пользователя
      widgets/          # CatalogScroll и другие кастомные виджеты
      utils/            # валидаторы цен и номеров
  core/                 # конфиг, DI-провайдеры
```

## Docker

```bash
docker compose up -d postgres redis
```