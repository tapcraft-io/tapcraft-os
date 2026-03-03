COMPOSE := docker compose -f services.yml -p tapcraft-dev

.PHONY: up down ps logs clean

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

ps:
	$(COMPOSE) ps

logs:
	$(COMPOSE) logs -f

clean:
	$(COMPOSE) down -v
