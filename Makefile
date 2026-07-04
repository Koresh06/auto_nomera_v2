.DEFAULT_GOAL := help

COMPOSE := docker compose

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

.PHONY: deploy
deploy: ## Миграции + сборка + запуск
	$(COMPOSE) run --rm bot alembic upgrade head
	$(COMPOSE) up -d --build

.PHONY: up
up: ## Поднять сервисы
	$(COMPOSE) up -d --build

.PHONY: down
down: ## Остановить сервисы
	$(COMPOSE) down

.PHONY: restart
restart: ## Перезапустить
	$(COMPOSE) restart

.PHONY: migrate
migrate: ## Применить миграции
	$(COMPOSE) run --rm bot alembic upgrade head

.PHONY: ps
ps: ## Статус сервисов
	$(COMPOSE) ps

.PHONY: logs
logs: ## Логи всех сервисов
	$(COMPOSE) logs -f

.PHONY: logs-bot
logs-bot: ## Логи бота
	$(COMPOSE) logs -f bot