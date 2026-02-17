.PHONY: install dev

# Установка зависимостей
install:
	pip install -r requirements.txt

# Запуск бота
dev:
	export $$(grep -v '^\#' .env | xargs) && python3 -m src.main
