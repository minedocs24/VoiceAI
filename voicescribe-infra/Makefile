.PHONY: help up start down stop reset clean migrate ramdisk-setup certs-dev status health logs logs-postgres logs-redis logs-nginx logs-prometheus logs-grafana backup restore chmod-scripts

help: ## Mostra elenco target disponibili
	@awk 'BEGIN {FS = ":.*##"; print "Target disponibili:"} /^[a-zA-Z_-]+:.*?##/ {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

up start: ## Avvia tutta l'infrastruttura
	docker compose up -d

down stop: ## Arresta l'infrastruttura
	docker compose down

reset clean: ## Distrugge stack e volumi (richiede conferma esplicita)
	@if [ "$$CONFIRM" != "yes" ]; then \
		echo "Operazione distruttiva. Rilancia con: make reset CONFIRM=yes"; \
		exit 1; \
	fi
	docker compose down -v --remove-orphans

migrate: ## Esegue migrazioni Alembic sul DB voicescribe
	docker compose exec -T postgres psql -U $$POSTGRES_USER -d $$VOICESCRIBE_DB_NAME -c "SELECT now();" >/dev/null
	alembic -c migrations/alembic.ini upgrade head

ramdisk-setup: ## Configura ramdisk tmpfs su host
	bash scripts/setup-ramdisk.sh

certs-dev: ## Genera certificati self-signed di sviluppo
	bash certs/generate-dev-certs.sh

status: ## Mostra stato container compose
	docker compose ps

health: ## Esegue healthcheck consolidato endpoint
	bash scripts/healthcheck.sh

logs: ## Segue i log di tutti i servizi
	docker compose logs -f --tail=200

logs-postgres: ## Log PostgreSQL
	docker compose logs -f --tail=200 postgres

logs-redis: ## Log Redis
	docker compose logs -f --tail=200 redis

logs-nginx: ## Log Nginx
	docker compose logs -f --tail=200 nginx

logs-prometheus: ## Log Prometheus
	docker compose logs -f --tail=200 prometheus

logs-grafana: ## Log Grafana
	docker compose logs -f --tail=200 grafana

backup: ## Esegue backup PostgreSQL con retention
	bash scripts/db-backup.sh

restore: ## Ripristina PostgreSQL da file backup: make restore FILE=...dump
	@if [ -z "$$FILE" ]; then echo "Specifica FILE=/path/backup.dump"; exit 1; fi
	bash scripts/db-restore.sh "$$FILE"

chmod-scripts: ## Imposta permessi eseguibili sugli script bash
	chmod +x scripts/*.sh certs/*.sh postgres/init/*.sh redis/entrypoint.sh

seed-e2e: ## Seed utenti test per e2e (free@test.local / password)
	docker compose exec -i postgres psql -U $${VOICESCRIBE_DB_USER:-voicescribe_app} -d $${VOICESCRIBE_DB_NAME:-voicescribe} -f - < scripts/seed-e2e-users.sql

e2e: ## Esegue test e2e (richiede stack up e seed)
	E2E_BASE_URL=$${E2E_BASE_URL:-https://localhost} E2E_VERIFY_SSL=$${E2E_VERIFY_SSL:-false} pytest tests/e2e/ -v -m e2e
