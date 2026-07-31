#!/usr/bin/env bash
#
# Полный перенос auto_nomera со старого сервера на новый.
# Запускать НА НОВОМ сервере, из папки проекта (~/auto_nomera_v2).
#
# Перед запуском: САМ останови старого бота на старом сервере,
# чтобы данные не менялись во время дампа.
#
# Скрипт:
#   1. по ssh снимает свежие дампы БД и Redis со старого сервера
#   2. поднимает временные legacy_db / legacy_redis из этих дампов
#   3. пересоздаёт чистую новую базу + миграции
#   4. прогоняет ETL (данные) и ресинхронизатор (расписание)
#   5. проверяет целостность
#
# Перед разрушительными шагами (down -v) спрашивает подтверждение.

set -euo pipefail

# ==================== НАСТРОЙКИ ====================
# Старый сервер (source)
OLD_HOST="${OLD_HOST:-82.97.252.159}"          # ssh-хост или IP старого сервера
OLD_SSH_USER="${OLD_SSH_USER:-root}"
OLD_PROJECT_DIR="${OLD_PROJECT_DIR:-~/bots/AutoNomeraBot}"
OLD_DB_CONTAINER="${OLD_DB_CONTAINER:-auto_nomera_db}"
OLD_REDIS_CONTAINER="${OLD_REDIS_CONTAINER:-auto_nomera_redis}"
OLD_DB_USER="${OLD_DB_USER:-my_user}"
OLD_DB_NAME="${OLD_DB_NAME:-auto_db}"
OLD_REDIS_PASSWORD="${OLD_REDIS_PASSWORD:-54321}"

# Новый сервер (this) — compose-проект
NEW_DB_USER="${NEW_DB_USER:-my_user}"
NEW_DB_NAME="${NEW_DB_NAME:-auto_db_2}"
COMPOSE_NETWORK="${COMPOSE_NETWORK:-auto_nomera_v2_default}"
PROJECT_DIR="${PROJECT_DIR:-$HOME/auto_nomera_v2}"

# Legacy-параметры (внутри новой compose-сети)
LEGACY_DB_PASSWORD="${LEGACY_DB_PASSWORD:-12345}"
LEGACY_DSN="postgresql://${OLD_DB_USER}:${LEGACY_DB_PASSWORD}@legacy_db:5432/${OLD_DB_NAME}"
LEGACY_REDIS="redis://legacy_redis:6379/2"

# ==================== ЦВЕТА / ХЕЛПЕРЫ ====================
RED=$'\e[31m'; GREEN=$'\e[32m'; YELLOW=$'\e[33m'; BLUE=$'\e[34m'; NC=$'\e[0m'

step()  { echo; echo "${BLUE}=== $* ===${NC}"; }
ok()    { echo "${GREEN}✓ $*${NC}"; }
warn()  { echo "${YELLOW}! $*${NC}"; }
die()   { echo "${RED}✗ $*${NC}" >&2; exit 1; }

confirm() {
    local msg="$1"
    echo
    warn "$msg"
    read -r -p "Продолжить? [y/N] " ans
    [[ "$ans" == "y" || "$ans" == "Y" ]] || die "Отменено пользователем"
}

# ==================== ПРОВЕРКИ ОКРУЖЕНИЯ ====================
step "Проверка окружения"

cd "$PROJECT_DIR" || die "Нет папки проекта $PROJECT_DIR"
[[ -f docker-compose.yml ]] || die "Нет docker-compose.yml в $PROJECT_DIR"
[[ -f scripts/migrate_legacy.py ]] || die "Нет scripts/migrate_legacy.py"
[[ -f scripts/resync_schedule.py ]] || die "Нет scripts/resync_schedule.py"
command -v docker >/dev/null || die "docker не установлен"

ok "Папка проекта: $PROJECT_DIR"
ok "Старый сервер: ${OLD_SSH_USER}@${OLD_HOST}"

# Напоминание про остановку старого бота
confirm "Убедись, что СТАРЫЙ БОТ ОСТАНОВЛЕН (данные не должны меняться во время дампа)."

# ==================== 1. ДАМПЫ СО СТАРОГО СЕРВЕРА ====================
step "1/6 Снятие свежих дампов со старого сервера"

echo "Дамп PostgreSQL..."
ssh "${OLD_SSH_USER}@${OLD_HOST}" \
    "docker exec ${OLD_DB_CONTAINER} pg_dump -U ${OLD_DB_USER} -d ${OLD_DB_NAME} --no-owner --no-acl | gzip" \
    > legacy_full.sql.gz
[[ -s legacy_full.sql.gz ]] || die "Дамп БД пустой — проверь параметры старого сервера"
ok "БД: $(du -h legacy_full.sql.gz | cut -f1)"

echo "Дамп Redis..."
ssh "${OLD_SSH_USER}@${OLD_HOST}" \
    "docker exec ${OLD_REDIS_CONTAINER} redis-cli -a ${OLD_REDIS_PASSWORD} --no-auth-warning SAVE >/dev/null 2>&1; \
     docker cp ${OLD_REDIS_CONTAINER}:/data/dump.rdb /tmp/legacy_redis_dump.rdb >/dev/null; \
     cat /tmp/legacy_redis_dump.rdb" \
    > legacy_redis_dump.rdb
[[ -s legacy_redis_dump.rdb ]] || die "Дамп Redis пустой"
ok "Redis: $(du -h legacy_redis_dump.rdb | cut -f1)"

# ==================== 2. LEGACY-КОНТЕЙНЕРЫ ====================
step "2/6 Поднятие временных legacy-контейнеров"

docker rm -f legacy_db legacy_redis >/dev/null 2>&1 || true

echo "legacy_db..."
docker run -d --name legacy_db --network "${COMPOSE_NETWORK}" \
    -e POSTGRES_USER="${OLD_DB_USER}" \
    -e POSTGRES_PASSWORD="${LEGACY_DB_PASSWORD}" \
    -e POSTGRES_DB="${OLD_DB_NAME}" \
    postgres:16 >/dev/null
echo "  ждём готовности postgres..."
for i in $(seq 1 60); do
    if docker exec legacy_db psql -U "${OLD_DB_USER}" -d "${OLD_DB_NAME}" -c "SELECT 1" >/dev/null 2>&1; then
        break
    fi
    sleep 1
done
docker exec legacy_db psql -U "${OLD_DB_USER}" -d "${OLD_DB_NAME}" -c "SELECT 1" >/dev/null 2>&1 \
    || die "legacy_db не поднялся за 60 сек"
gunzip -c legacy_full.sql.gz | docker exec -i legacy_db psql -U "${OLD_DB_USER}" -d "${OLD_DB_NAME}" >/dev/null
LEGACY_USERS=$(docker exec legacy_db psql -U "${OLD_DB_USER}" -d "${OLD_DB_NAME}" -tAc "SELECT count(*) FROM users")
ok "legacy_db поднят, юзеров в дампе: ${LEGACY_USERS}"

echo "legacy_redis..."
docker run -d --name legacy_redis --network "${COMPOSE_NETWORK}" \
    -v "${PROJECT_DIR}/legacy_redis_dump.rdb:/data/dump.rdb" \
    redis:7 redis-server --dbfilename dump.rdb --dir /data >/dev/null
sleep 3
LEGACY_TASKS=$(docker exec legacy_redis redis-cli -n 2 ZCARD aps_run_times 2>/dev/null || echo "?")
ok "legacy_redis поднят, задач в расписании: ${LEGACY_TASKS}"

# ==================== 3. ЧИСТАЯ НОВАЯ БАЗА ====================
step "3/6 Пересоздание чистой новой базы"

confirm "Сейчас будет docker compose down -v — новая база будет ПОЛНОСТЬЮ ОЧИЩЕНА."

docker compose down -v
docker compose up -d db redis
echo "  ждём healthy..."
for i in $(seq 1 30); do
    if docker compose ps db 2>/dev/null | grep -q healthy; then break; fi
    sleep 1
done
docker compose run --rm bot alembic upgrade head
ok "База пересоздана, миграции применены"

# legacy-контейнеры могли отвалиться при down -v? проверим
docker ps --format '{{.Names}}' | grep -q '^legacy_db$'    || die "legacy_db пропал после down -v"
docker ps --format '{{.Names}}' | grep -q '^legacy_redis$' || die "legacy_redis пропал после down -v"

# ==================== 4. ETL ====================
step "4/6 Перенос данных (ETL)"

docker compose run --rm \
    -v "${PROJECT_DIR}/scripts:/app/scripts" -e PYTHONPATH=/app \
    -e LEGACY_DSN="${LEGACY_DSN}" \
    bot python scripts/migrate_legacy.py

LEGACY_ID_CNT=$(docker compose exec -T db psql -U "${NEW_DB_USER}" -d "${NEW_DB_NAME}" -tAc \
    "SELECT count(*) FROM ads WHERE legacy_id IS NOT NULL")
ok "ETL завершён, объявлений с legacy_id: ${LEGACY_ID_CNT}"

# ==================== 5. РЕСИНХРОНИЗАТОР ====================
step "5/6 Пересоздание расписания (ресинхронизатор)"

docker compose run --rm \
    -v "${PROJECT_DIR}/scripts:/app/scripts" -e PYTHONPATH=/app \
    -e LEGACY_DSN="${LEGACY_DSN}" \
    -e LEGACY_REDIS="${LEGACY_REDIS}" \
    bot python scripts/resync_schedule.py

SCHED_CNT=$(docker compose exec -T redis redis-cli -n 1 KEYS 'schedule:*' 2>/dev/null | wc -l)
ok "Ресинхронизатор завершён, задач в планировщике: ${SCHED_CNT}"

# ==================== 6. ПРОВЕРКА ЦЕЛОСТНОСТИ ====================
step "6/6 Проверка целостности"

echo "Счётчики:"
docker compose exec -T db psql -U "${NEW_DB_USER}" -d "${NEW_DB_NAME}" -c "
SELECT 'users' t, count(*) FROM users
UNION ALL SELECT 'regions', count(*) FROM regions
UNION ALL SELECT 'ads', count(*) FROM ads
UNION ALL SELECT 'publications', count(*) FROM publications
UNION ALL SELECT 'payments', count(*) FROM payments
UNION ALL SELECT 'services', count(*) FROM publication_services
ORDER BY 1;"

echo "Осиротевшие связи (должны быть 0):"
docker compose exec -T db psql -U "${NEW_DB_USER}" -d "${NEW_DB_NAME}" -c "
SELECT 'ads_no_user' t, count(*) FROM ads a LEFT JOIN users u ON u.id=a.user_id WHERE u.id IS NULL
UNION ALL SELECT 'pubs_no_ad', count(*) FROM publications p LEFT JOIN ads a ON a.id=p.ad_id WHERE a.id IS NULL
UNION ALL SELECT 'pay_no_user', count(*) FROM payments p LEFT JOIN users u ON u.id=p.user_id WHERE u.id IS NULL
UNION ALL SELECT 'services_no_pub', count(*) FROM publication_services s LEFT JOIN publications p ON p.id=s.publication_id WHERE p.id IS NULL;"

echo "Запланированные публикации:"
docker compose exec -T db psql -U "${NEW_DB_USER}" -d "${NEW_DB_NAME}" -c "
SELECT status, count(*), count(scheduler_job_id) with_job FROM publications GROUP BY status ORDER BY status;"

# ==================== ИТОГ ====================
echo
echo "${GREEN}════════════════════════════════════════════${NC}"
echo "${GREEN}  ПЕРЕНОС ЗАВЕРШЁН${NC}"
echo "${GREEN}════════════════════════════════════════════${NC}"
echo
echo "Проверь вывод выше:"
echo "  • счётчики сходятся с ожиданием"
echo "  • осиротевшие связи = 0"
echo "  • SCHEDULED-публикации имеют with_job"
echo
echo "Дальше вручную:"
echo "  1. Раскомментируй resolve_publish_at_utc в SelectSlotForPublicationUseCase"
echo "     (сейчас там тестовая заглушка now+1мин)"
echo "  2. Запусти нового бота:   docker compose up -d"
echo "  3. Проверь бота в Telegram"
echo "  4. Убери legacy-контейнеры: docker rm -f legacy_db legacy_redis"
echo
warn "Нового бота НЕ запускай, пока не проверил данные выше и заглушку времени!"