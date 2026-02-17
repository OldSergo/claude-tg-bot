VENV = .venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip

.PHONY: install dev

# Создание venv и установка зависимостей
install:
	python3 -m venv $(VENV)
	$(PIP) install -r requirements.txt

# Запуск бота
dev:
	export $$(grep -v '^\#' .env | xargs) && $(PYTHON) -m src.main
