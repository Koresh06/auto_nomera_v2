.DEFAULT_GOAL := help
SHELL := /bin/bash

COMPOSE := docker compose

DB_SERVICE      := db
REDIS_SERVICE   := redis
DB_USER         := my_user
DB_NAME         := auto_db_2
REDIS_TASKIQ_DB := 1

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

# ==================== ДЕПЛОЙ / ЖИЗНЕННЫЙ ЦИКЛ ====================

.PHONY: deploy
deploy: ## Миграции + сборка + запуск
	$(COMPOSE) run --rm bot alembic upgrade head
	$(COMPOSE) up -d --build

.PHONY: up
up: ## Поднять сервисы
	$(COMPOSE) up -d

.PHONY: down
down: ## Остановить сервисы
	$(COMPOSE) down

.PHONY: restart
restart: ## Перезапустить все сервисы
	$(COMPOSE) restart

.PHONY: migrate
migrate: ## Применить миграции
	$(COMPOSE) run --rm bot alembic upgrade head

.PHONY: ps
ps: ## Статус сервисов
	$(COMPOSE) ps

# ==================== ЛОГИ ====================

.PHONY: logs
logs: ## Логи всех сервисов
	$(COMPOSE) logs -f

.PHONY: logs-bot
logs-bot: ## Логи бота
	$(COMPOSE) logs -f bot

.PHONY: logs-worker
logs-worker: ## Логи воркера (taskiq)
	$(COMPOSE) logs -f worker

.PHONY: logs-web
logs-webhook: ## Логи веб-сервиса (вебхуки ЮKassa)
	$(COMPOSE) logs -f webhook

.PHONY: logs-errors
logs-errors: ## Только ошибки за последний час, по всем сервисам
	$(COMPOSE) logs | grep -iE "error|exception|traceback"

# ==================== БАЗА ДАННЫХ ====================

.PHONY: db-shell
db-shell: ## Зайти в psql
	$(COMPOSE) exec $(DB_SERVICE) psql -U $(DB_USER) -d $(DB_NAME)

.PHONY: db-stats
db-stats: ## Публикации по статусам + осиротевшие связи
	@$(COMPOSE) exec -T $(DB_SERVICE) psql -U $(DB_USER) -d $(DB_NAME) -c "\
	SELECT status, count(*) FROM publications GROUP BY status ORDER BY status;"

.PHONY: db-overdue
db-overdue: ## Публикации, которые должны были опубликоваться, но всё ещё SCHEDULED
	@$(COMPOSE) exec -T $(DB_SERVICE) psql -U $(DB_USER) -d $(DB_NAME) -c "\
	SELECT id, ad_id, slot_day, slot_time, publish_at_utc, scheduler_job_id \
	FROM publications \
	WHERE status = 'SCHEDULED' AND publish_at_utc < now() \
	ORDER BY publish_at_utc;"

.PHONY: db-scheduled
db-scheduled: ## Все запланированные публикации, ближайшие сверху
	@$(COMPOSE) exec -T $(DB_SERVICE) psql -U $(DB_USER) -d $(DB_NAME) -c "\
	SELECT id, ad_id, slot_day, slot_time, publish_at_utc, scheduler_job_id \
	FROM publications \
	WHERE status = 'SCHEDULED' \
	ORDER BY publish_at_utc LIMIT 30;"

# ==================== REDIS / ПЛАНИРОВЩИК (taskiq) ====================

.PHONY: redis-shell
redis-shell: ## Зайти в redis-cli (база taskiq)
	$(COMPOSE) exec $(REDIS_SERVICE) redis-cli -n $(REDIS_TASKIQ_DB)

.PHONY: tasks-count
tasks-count: ## Сколько задач сейчас в очереди taskiq
	@echo "Всего schedule:* ключей в Redis:"
	@$(COMPOSE) exec -T $(REDIS_SERVICE) redis-cli -n $(REDIS_TASKIQ_DB) KEYS 'schedule:*' | wc -l

.PHONY: tasks-vs-db
tasks-vs-db: ## Сверка: Redis job_id vs записи в БД (расхождения = проблема)
	@echo "=== job_id в Redis, но нет в БД (осиротевшие задачи) ==="
	@comm -23 \
		<($(COMPOSE) exec -T $(REDIS_SERVICE) redis-cli -n $(REDIS_TASKIQ_DB) KEYS 'schedule:*' | sed 's/^schedule://' | sort) \
		<($(COMPOSE) exec -T $(DB_SERVICE) psql -U $(DB_USER) -d $(DB_NAME) -tAc \
			"SELECT scheduler_job_id FROM publications WHERE status='SCHEDULED' AND scheduler_job_id IS NOT NULL" | sort)
	@echo "=== job_id в БД, но нет в Redis (никогда не выполнятся) ==="
	@comm -13 \
		<($(COMPOSE) exec -T $(REDIS_SERVICE) redis-cli -n $(REDIS_TASKIQ_DB) KEYS 'schedule:*' | sed 's/^schedule://' | sort) \
		<($(COMPOSE) exec -T $(DB_SERVICE) psql -U $(DB_USER) -d $(DB_NAME) -tAc \
			"SELECT scheduler_job_id FROM publications WHERE status='SCHEDULED' AND scheduler_job_id IS NOT NULL" | sort)

.PHONY: tasks-summary
tasks-summary: ## Сводка: сколько задач и записей БД, совпадают ли числа
	@echo "Redis schedule:* -----------------"
	@$(COMPOSE) exec -T $(REDIS_SERVICE) redis-cli -n $(REDIS_TASKIQ_DB) KEYS 'schedule:*' | wc -l
	@echo "БД publications SCHEDULED --------"
	@$(COMPOSE) exec -T $(DB_SERVICE) psql -U $(DB_USER) -d $(DB_NAME) -tAc \
		"SELECT count(*) FROM publications WHERE status='SCHEDULED'"
	@echo "БД SCHEDULED без scheduler_job_id -"
	@$(COMPOSE) exec -T $(DB_SERVICE) psql -U $(DB_USER) -d $(DB_NAME) -tAc \
		"SELECT count(*) FROM publications WHERE status='SCHEDULED' AND scheduler_job_id IS NULL"

.PHONY: tz-drift
tz-drift:
	@$(COMPOSE) exec -T db psql -U my_user -d auto_db_2 -c "\
	SELECT p.id, r.timezone, p.slot_day, p.slot_time, p.publish_at_utc, \
	       ((p.slot_day + p.slot_time) AT TIME ZONE r.timezone) AS expected_utc \
	FROM publications p JOIN regions r ON r.id = p.region_id \
	WHERE p.status = 'SCHEDULED' AND p.slot_day IS NOT NULL \
	  AND p.publish_at_utc <> ((p.slot_day + p.slot_time) AT TIME ZONE r.timezone) \
	ORDER BY p.publish_at_utc;"

# ==================== МОНИТОРИНГ ХОСТИНГА ====================

.PHONY: top
top: ## Снимок CPU/RAM по контейнерам прямо сейчас
	docker stats --no-stream

.PHONY: disk
disk: ## Место на диске (система + докер)
	@df -h /
	@echo
	docker system df

.PHONY: health
health: ## Быстрый общий статус: контейнеры + очередь + просроченные публикации
	@echo "=== Контейнеры ==="
	@$(COMPOSE) ps
	@echo
	@echo "=== Очередь задач ==="
	@$(MAKE) tasks-summary
	@echo
	@echo "=== Просроченные публикации ==="
	@$(MAKE) db-overdue