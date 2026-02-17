VENV = .venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip
PID_FILE = .bot.pid

.PHONY: install dev start stop restart status

# Создание venv и установка зависимостей
install:
	python3 -m venv $(VENV)
	$(PIP) install -r requirements.txt

# Запуск в foreground (для разработки)
dev:
	export $$(grep -v '^\#' .env | xargs) && $(PYTHON) -m src.main

# Запуск в фоне (демон)
start:
	@if [ -f $(PID_FILE) ] && kill -0 $$(cat $(PID_FILE)) 2>/dev/null; then \
		echo "Бот уже запущен (PID: $$(cat $(PID_FILE)))"; \
	else \
		export $$(grep -v '^\#' .env | xargs) && \
		nohup $(PYTHON) -m src.main > bot.log 2>&1 & echo $$! > $(PID_FILE); \
		echo "Бот запущен (PID: $$(cat $(PID_FILE))), логи: bot.log"; \
	fi

# Остановка демона
stop:
	@if [ -f $(PID_FILE) ]; then \
		kill $$(cat $(PID_FILE)) 2>/dev/null && \
		rm -f $(PID_FILE) && \
		echo "Бот остановлен"; \
	else \
		echo "PID-файл не найден, бот не запущен"; \
	fi

# Перезапуск
restart: stop start

# Статус
status:
	@if [ -f $(PID_FILE) ] && kill -0 $$(cat $(PID_FILE)) 2>/dev/null; then \
		echo "Бот работает (PID: $$(cat $(PID_FILE)))"; \
	else \
		echo "Бот не запущен"; \
		rm -f $(PID_FILE) 2>/dev/null; \
	fi

# Просмотр логов
logs:
	tail -f bot.log
