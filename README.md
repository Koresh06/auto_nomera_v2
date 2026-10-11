# auto_nomera_v2

Telegram-бот для размещения объявлений о продаже/покупке автомобильных номеров.

## Стек

- Python 3.12, aiogram 3, aiogram-dialog
- SQLAlchemy 2.0 async + PostgreSQL 16, Alembic
- Redis (холд слотов, FSM-хранилище диалогов, кэш блокировок, защита от двойного нажатия)
- Taskiq (воркер + планировщик)
- FastAPI + uvicorn (вебхук и страница возврата ЮKassa)
- dishka (dependency injection)
- Sentry (опционально)
- uv (управление зависимостями)

## Архитектура

Clean Architecture + DDD: `domain → application → infrastructure → presentation`

Все диалоги используют `aiogram-dialog` с Redis-safe `dialog_data` (только примитивы — id, строки, числа; доменные объекты не хранятся напрямую).

Взаимодействие слоёв построено вокруг медиатора: презентация вызывает use cases через `Mediator.handle(Request)`, а не обращается к репозиториям напрямую. Фоновые задачи (публикация, откреп, рассылка, подтверждение оплаты) также резолвят use cases через медиатор внутри Taskiq-воркера.

Права проверяются на сервере в каждом обработчике, а не только скрытием кнопок: поддельный callback от обычного пользователя в админ-диалог не пройдёт. Все изменения баланса идут под блокировкой строки пользователя (`SELECT ... FOR UPDATE`), повторное нажатие кнопок оплаты применяется один раз.

### Сервисы

| Сервис      | Команда                                                   | Назначение                                   |
|-------------|-----------------------------------------------------------|----------------------------------------------|
| `bot`       | `python -m src.presentation.telegram.app`                 | Telegram-бот (polling)                       |
| `webhook`   | `uvicorn src.presentation.web.app:create_app --factory`   | `POST /webhook/yookassa`, `GET /payment/return` |
| `worker`    | `taskiq worker src.worker:broker`                         | выполнение фоновых задач                     |
| `scheduler` | `taskiq scheduler src.scheduler:scheduler`                | запуск отложенных задач по времени           |

## Локальный запуск

```bash
uv sync                      # зависимости (с dev-группой)
cp .env.dist .env            # заполнить значения
uv run alembic upgrade head  # миграции

uv run python -m src.presentation.telegram.app
uv run uvicorn src.presentation.web.app:create_app --factory --port 8080
uv run taskiq worker src.worker:broker
uv run taskiq scheduler src.scheduler:scheduler
```

## Переменные окружения

Полный шаблон — в `.env.dist`.

```dotenv
APP_CONFIG__APP__APP_NAME=AutoNomera_V2
APP_CONFIG__APP__DEBUG=False
APP_CONFIG__APP__SENTRY_DSN=
APP_CONFIG__APP__PRE_PUBLICATION_WINDOW_HOURS=2
APP_CONFIG__APP__HOLD_SLOTS_TIME=300

APP_CONFIG__TELEGRAM__BOT_TOKEN=12345
APP_CONFIG__TELEGRAM__BOT_PROXY=
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
APP_CONFIG__PAYMENT__YOOKASSA__PROXY=
APP_CONFIG__PAYMENT__CRYPTOMUS__MERCHANT_ID=1231412
APP_CONFIG__PAYMENT__CRYPTOMUS__API_KEY=dwqedd2da
```

Ключевые параметры:

- `PRE_PUBLICATION_WINDOW_HOURS` — за сколько часов до публикации объявление появляется в каталоге раннего доступа.
- `HOLD_SLOTS_TIME` — время холда слота в секундах (Redis TTL).
- `ADMIN_IDS` — список Telegram ID супер-администраторов (задаётся только через конфиг, не меняется через бота).
- `SENTRY_DSN` — если пусто, Sentry не инициализируется.
- `BOT_PROXY` — прокси для запросов к Telegram Bot API; пусто — напрямую.
- `YOOKASSA__PROXY` — прокси только для API ЮKassa. Пусто — напрямую; системные `HTTP(S)_PROXY` для ЮKassa намеренно игнорируются.
- `RETURN_URL` — куда ЮKassa возвращает пользователя после оплаты (страница `/payment/return` сервиса `webhook`).
- Необязательные: `APP_CONFIG__DB__POSTGRES__POOL_SIZE` (50), `APP_CONFIG__DB__POSTGRES__MAX_OVERFLOW` (10).

## Функциональность

### Объявления

- Продажа, покупка, срочный выкуп, магазин номеров (`AdType.SALE / BUY / URGENT_BUYOUT / STORE`)
- Повторная публикация без повторного ввода данных (`reuse_ad`)
- Редактирование до и после публикации (город, цена, телефон); пост в канале обновляется, в том числе у автопубликаций
- Номер можно сменить только пока публикация не вышла в канал (статусы `DRAFT / SCHEDULED / CANCELED`); при смене перегенерируется изображение
- Цена — только целое положительное число; отрицательные значения, слова и ведущие нули отклоняются
- Лимиты бесплатных публикаций за 7 дней: продажа / покупка / срочный выкуп — 5, магазин — 2; один и тот же номер — не чаще раза в 7 дней. Лимиты включаются per-region (`publication_limit_enabled`); при достижении предлагается платный слот

### Магазин номеров (STORE)

- Один `Ad` с `ad_type=STORE` — постоянный магазин пользователя в регионе
- Создание магазина: название, город, телефон
- Массовое добавление номеров в формате `номер-цена` (построчно), лимит ~83 шт. на пост Telegram
- Редактирование данных магазина (название / город / телефон)
- Редактирование отдельных номеров: изменение номера, цены, удаление
- Публикация магазина через тот же механизм слотов и платных услуг, что и обычные объявления (кроме HIGHLIGHT)
- Многократные публикации одного магазина — каждая независима; публикации магазина живут в отдельном разделе и не попадают в «Мои объявления»

### Срочный выкуп (URGENT_BUYOUT)

- Укороченный флоу без выбора слота и города: номер → фото → цена → подтверждение
- Заявка уходит на модерацию администраторам с фото и кнопками «Одобрить» / «Отклонить»
- Защита от race condition: если заявку уже обработал другой админ, второй получает уведомление
- После одобрения объявление становится доступно в каталоге раннего доступа
- Рассылка подписчикам выполняется асинхронно через Taskiq

### Каталог раннего доступа (PRE_PUBLICATION)

- Раздел виден всем; без активной подписки (`pre_publication_expires_at`) показывается предложение её купить
- Объединяет одобренные заявки на срочный выкуп и публикации, выходящие в ближайшие N часов (`PRE_PUBLICATION_WINDOW_HOURS`)
- Скользящее окно по UTC: объявление появляется, когда до публикации остаётся ≤ N часов, и исчезает сразу после выхода в канал (смена статуса на `PUBLISHED`)
- Кастомная пагинация по одной карточке с кольцевой навигацией (`CatalogScroll`)
- Текст карточки идентичен тому, что увидят в канале (`AdTextRenderer`)
- Поддержка обычных объявлений и магазинов в одном каталоге
- Фильтрация по региону

### Слоты и календарь

- Календарь слотов с холдом (Redis TTL, `HOLD_SLOTS_TIME`)
- Первые N ближайших слотов всегда платные (`system_paid_slots_count`, по умолчанию 3, настраивается per-region)
- Слот бесплатен только один раз: после того как его кто-то занял, он платный для всех
- Платный слот не эксклюзивен: если его уже заняли, его всё равно можно взять за деньги (с баланса или через провайдера). Конфликт «слот только что заняли» возможен только для бесплатного слота
- Отмена после оплаты (с предупреждением) или уход без подтверждения — слот теряется, повторный выбор того же слота снова платный
- Перед финальным подтверждением повторно проверяется актуальность холда; при истечении — пользователь возвращается на календарь (оплаченный слот не требует холда)
- Повторное нажатие «оплатить с баланса» списывает один раз (Redis-guard)
- Локальное время региона для выбора и отображения, UTC для хранения и планирования (`PublishTimeResolver` через `ZoneInfo`)

### Платные услуги (паттерн Стратегия)

- **HIGHLIGHT** — красная рамка на фото (наложение через Pillow); недоступна для магазина
- **PIN** — закрепление в канале на N дней с автоматическим откреплением по таймеру
- **AUTOPUBLISH** — публикация N дней подряд; дочерние публикации создаются после первой и помечаются флагом `is_child` (в списках и каталогах показывается только родительская). Удаление объявления или отмена админом снимает всю серию
- **PRIORITY_PUBLISH** — немедленная публикация вне очереди
- **PRE_PUBLICATION** — подписка на каталог раннего доступа

Покупка услуг: с баланса (мгновенно) или через платёжный провайдер с возвратом в диалог через `DialogTeleporter` после подтверждения.

### Оплата

- ЮKassa (вебхук `POST /webhook/yookassa`, статус перепроверяется через API ЮKassa), Telegram Stars, ручная оплата картой
- Cryptomus — заглушка, провайдер ещё не подключён
- Идемпотентный `ConfirmPaymentUseCase` — безопасная повторная обработка (платёж блокируется `FOR UPDATE`)
- Телепорт пользователя обратно в нужный экран диалога после подтверждения оплаты (`BgManager` + `RESET_STACK`)
- Покрыты все виды покупок: пополнение баланса, услуги публикации, подписка, платные слоты
- Если провайдер недоступен, пользователь видит понятное сообщение, а не общую ошибку
- Блокировка платежей на уровне пользователя (`is_payment_blocked`) — заблокированный не может создать платёж
- Администраторы получают уведомление о каждом пополнении

### Регионы

- Мультирегиональность с отдельными каналами
- Таймзоны, настройки слотов, лимиты публикаций — per-region
- Ссылки на чат, VK-группу, канал в MAX подключаются индивидуально
- Системный порядок: Москва и Санкт-Петербург первыми, остальные по номеру региона
- Статус региона (`ACTIVE / DISABLED`) — отключённый регион недоступен для новых объявлений; активные пользователи отключённого региона перенаправляются на выбор нового региона

## Админ-панель

Доступ по команде `/admin`. Разграничение прав:

- **Супер-администратор** — Telegram ID из конфига (`ADMIN_IDS`). Полный доступ, включая регионы, услуги, баланс, блокировки, назначение админов.
- **Администратор** (`UserRole.ADMIN`, назначается через бота) — операционные разделы: рассылки, статистика.

### Модули

- **Регионы** — создание, редактирование настроек слотов (время, горизонт календаря, платные слоты, цена, лимит публикаций), соцсети/каналы, включение/отключение региона. Изменения сохраняются мгновенно.
- **Платные услуги** — редактирование прайса (цена, длительность, описание, название), включение/снятие с продажи, сброс к стандартным значениям из сидов.
- **Баланс пользователей** — поиск по Telegram ID, ручная корректировка баланса со знаком (`+500` / `-200`) через доменные методы `top_up` / `charge`.
- **Блокировка пользователей** — полная блокировка (`is_blocked`) и блокировка платежей (`is_payment_blocked`), поиск по ID и по пересланному контакту. Блокировки кэшируются в Redis (TTL) поверх БД; проверка полной блокировки в middleware на каждом апдейте.
- **Управление администраторами** — назначение/снятие роли `UserRole.ADMIN`. Супер-админы из конфига защищены от снятия через бота.
- **Рассылки** — трём типам получателей (всем пользователям / по региону / во все каналы регионов) с предпросмотром перед отправкой; заблокированные пользователи исключаются. Выполняется асинхронно через Taskiq (`NotificationService.broadcast_copy`), с троттлингом и ретраем на flood-wait.
- **Срочный выкуп** — модерация заявок (одобрить / отклонить).
- **Неопубликованные публикации** — запланированные публикации с возможностью отмены.
- **Статистика пополнений** — SQL-агрегация по методам оплаты, топ-5 регионов, детальный список пополнений; фильтр по периоду (сегодня / неделя / месяц / всё время).
- **Статистика публикаций** — разбивка по статусам и типам объявлений, срочные выкупы учитываются отдельно (не публикуются, живут в `Ad`); расписание региона по локальной дате с кликабельными ссылками на владельцев; отмена публикации (отменяет всю серию автопубликации, снимает job из планировщика, уведомляет пользователя).

## Структура проекта

```
src/
  domain/               # сущности, value objects, доменные сервисы
    entities/           # Ad, Publication, Payment, User, Region, PublicationService, ServiceDefinition
    services/           # SlotReservationService, AdTextRenderer, RegionGuard, PublishTimeResolver, лимитер
    value_objects/      # Price, SlotKey, Contacts, StoreContent, RegionSettings, RegionMetadata...
  application/          # use cases, порты, медиатор, DTO
    use_cases/          # сгруппированы по контексту (ad, publication, store, payment, slots, stats, user, mailing...)
    dtos/
    ports/              # RegionRepository, PaymentRepository, BlockCache, NotificationService, TaskQueue...
    mediator.py
  infrastructure/       # БД, Redis, Telegram, Taskiq, seeds
    alembic/            # миграции
    repositories/       # SQLAlchemy-реализации
    cache/              # RedisBlockCache
    payment/providers/  # ЮKassa, Stars, manual_card, Cryptomus (заглушка)
    tasks/, broker/, scheduler/   # Taskiq
    seeds/              # начальные данные (ServiceDefinition)
  presentation/
    telegram/
      features/
        user/modules/   # ad, store, paid_services, payment, balance, menu, profile, catalog_deferred_publication
        admin/modules/  # menu, region, paid_services, balance, blocking, admin_management,
                        # mailing, stats, urgent_buyout, unpublished_publications
      middlewares/      # проверка блокировки пользователя
      widgets/          # CatalogScroll и другие кастомные виджеты
    web/                # FastAPI: вебхук и страница возврата ЮKassa
  core/                 # конфиг, DI-провайдеры, Sentry
  tests/                # см. «Тесты»
  worker.py, scheduler.py
scripts/                # разовые скрипты обслуживания и восстановления расписания (запуск вручную)
```

## Тесты

```bash
uv run pytest src/tests -q
uv run pytest src/tests --cov   # с покрытием
```

Docker и внешние сервисы не нужны:

- `src/tests/domain`, `src/tests/use_cases` — юнит-тесты доменной логики и use cases.
- `src/tests/integration` — реальный PostgreSQL 16 (`pgserver`, поднимается из pip) с настоящими миграциями Alembic, Redis через `fakeredis[lua]`, контракт Taskiq.
- `src/tests/integration/telegram` — сквозные сценарии через настоящий Dispatcher и DI с симулятором Telegram (`harness.py`): создание объявлений, магазин, оплаты, админка, гонки и двойные нажатия, поддельные callback'и.
- `src/tests/test_di_wiring.py` — продовые DI-графы бота, веба и воркера собираются и обслуживают все запросы.

Тесты не зависят от локального `.env`; Sentry в тестах отключён. Реальные Telegram, ЮKassa и Sentry не вызываются.

Перед коммитом/пушем pre-commit запускает `ruff`, `ruff format` и все тесты.

## CI/CD

- **CI** (`.github/workflows/ci.yml`) — на каждый push и PR: `ruff check`, `ruff format --check`, `pytest` с покрытием. `mypy` запускается, но пока не блокирует.
- **Build and Deploy** (`.github/workflows/deploy.yml`) — на push в `main`: сначала тот же CI, затем сборка и публикация образа `ghcr.io/koresh06/auto_nomera:latest`. Если тесты упали, образ не собирается.
- На сервер образ сам не выкатывается — обновление вручную, по шагам в [DEPLOY.md](DEPLOY.md).

## Docker / сервер

```bash
docker compose pull                               # скачать образ из ghcr.io
docker compose run --rm bot alembic upgrade head  # миграции
docker compose up -d                              # запустить всё
docker compose logs -f                            # логи
```

⚠️ `make deploy` для обновления не подходит: он делает `up -d --build`, а у сервисов нет секции `build`, поэтому новый образ не скачается.

Полезные команды `Makefile` (`make help` — полный список):

| Команда            | Что делает                                                    |
|--------------------|---------------------------------------------------------------|
| `make ps`          | статус контейнеров                                            |
| `make migrate`     | применить миграции                                            |
| `make logs-errors` | ошибки и traceback из логов всех сервисов                     |
| `make health`      | контейнеры + очередь задач + просроченные публикации          |
| `make tasks-vs-db` | сверка задач в Redis с запланированными публикациями в БД     |
| `make db-overdue`  | публикации, которые должны были выйти, но всё ещё `SCHEDULED` |
| `make db-shell`    | psql                                                          |
