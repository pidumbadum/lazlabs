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

docs: ## собрать документацию
	@echo "Сборка документации..."
	cd docs && sphinx-build -b html . _build/html
	@echo "Документация собрана в docs/_build/html"
	@echo "Откройте docs/_build/html/index.html в браузере"

docs-serve: ## Запустить документацию локально (автообновление)
	cd docs && sphinx-autobuild . _build/html --host 0.0.0.0 --port 8000
	@echo "Документация доступна по адресу: http://localhost:8000"

docs-clean: ## Очистить собранную документацию
	@echo "Очистка документации..."
	rm -rf docs/_build
	@echo "Документация очищена"

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