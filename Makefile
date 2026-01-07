.PHONY: help install run test lint format clean docker-build docker-up docker-down docker-logs

help:
	@echo "Available commands:"
	@echo "  make install     - Install dependencies"
	@echo "  make run         - Run the development server"
	@echo "  make test        - Run tests"
	@echo "  make lint        - Run linter"
	@echo "  make format      - Format code"
	@echo "  make clean       - Clean up generated files"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-up   - Start services with Docker Compose"
	@echo "  make docker-down - Stop services"
	@echo "  make docker-logs - View Docker logs"

install:
	pip install -r requirements.txt

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v

lint:
	# TODO: Add linter (flake8, pylint, etc.)
	@echo "Linting not configured yet"

format:
	# TODO: Add formatter (black, autopep8, etc.)
	@echo "Formatting not configured yet"

clean:
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.db" -delete
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

