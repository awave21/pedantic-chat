# 🤖 Pydantic AI Chat

AI-чат на базе Pydantic AI и OpenAI GPT с веб-интерфейсом.

## Возможности

- 💬 Streaming ответы (как в ChatGPT)
- 🛠 Встроенные инструменты (время, калькулятор, заметки)
- 🎨 Современный UI на Tailwind CSS
- 🐳 Docker-ready для Coolify

## Быстрый старт

### Локально

```bash
# Клонировать репозиторий
git clone <your-repo>
cd pydantic-ai-chat

# Создать .env файл
cp .env.example .env
# Отредактировать .env и добавить OPENAI_API_KEY

# Установить зависимости
pip install -r requirements.txt

# Запустить
python main.py
```

Открыть http://localhost:8000

### Docker

```bash
# Собрать и запустить
docker compose up -d

# Посмотреть логи
docker compose logs -f
```

### Coolify

1. Создай новый репозиторий на GitHub
2. Загрузи эти файлы в репозиторий
3. В Coolify: **+ Add Resource** → **Docker Compose**
4. Укажи URL репозитория
5. Добавь переменные окружения:
   - `OPENAI_API_KEY` = твой ключ
   - `OPENAI_MODEL` = gpt-4o-mini (или gpt-4o)
6. В настройках укажи домен с `https://`
7. Deploy!

## API Endpoints

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/` | Веб-интерфейс |
| GET | `/health` | Health check |
| POST | `/api/chat` | Обычный чат |
| POST | `/api/chat/stream` | Streaming чат (SSE) |

### Пример запроса

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Привет! Который час?"}'
```

## Добавление инструментов

Добавь новый инструмент в `main.py`:

```python
@agent.tool
async def my_tool(ctx: RunContext[AgentDeps], param: str) -> str:
    """Описание инструмента для AI."""
    # Твоя логика
    return "Результат"
```

## Структура проекта

```
pydantic-ai-chat/
├── docker-compose.yml  # Docker Compose конфиг
├── Dockerfile          # Docker образ
├── main.py             # Приложение (API + UI)
├── requirements.txt    # Python зависимости
├── .env.example        # Пример переменных окружения
└── README.md           # Документация
```

## Лицензия

MIT
