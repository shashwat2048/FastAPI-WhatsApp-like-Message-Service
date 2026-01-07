.PHONY: help up down logs test

help:
	@echo "Available commands:"
	@echo "  make up    - Start services with Docker Compose"
	@echo "  make down  - Stop services"
	@echo "  make logs  - View Docker logs"
	@echo "  make test  - Run tests"

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

test:
	pytest tests/ -v

