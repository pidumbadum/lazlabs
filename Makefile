.PHONY: help setup test run docs docker-up docker-down clean

help: ## Показать справку
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

setup: ## Установить зависимости
	pip install -e packages/core
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

test: ## Запустить тесты
	pytest tests/ packages/core/tests/ -v

coverage: ## Отчёт о покрытии
	pytest --cov=packages/core --cov=app --cov-report=term-missing

run: ## Запустить приложение
	cd app && python app/main.py

docs: ## Собрать документацию
	@echo "Документация в docs/"

docker-build: ## Собрать Docker-образ
	docker build -t lazlabs-school -f app/Dockerfile .

docker-up: ## Запустить в Docker
	docker compose -f infra/compose.yaml up -d

docker-down: ## Остановить Docker
	docker compose -f infra/compose.yaml down

clean: ## Очистить временные файлы
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	rm -rf .coverage htmlcov/