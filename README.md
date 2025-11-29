# vihorki_aviahack
Репозиторий команды Вихорьки

# Настройка pre-commit

Настройка прекоммит 
```shell
uv add pre-commit
pre-commit install
```

для проверки
```shell
pre-commit run --all-files
```

# Безопасность

Для SAST используется:

<a>bandit</a>  — утилита для проверки Python-кода на наличие распространенных уязвимостей.

<a>trivy</a> — швейцарский нож, который подходит для проверки Docker-контейнеров, git-репозиториев, операционных систем и исходного кода. 

<a>gitleaks</a> — утилита для поиска паролей, хешей и других забытых чувствительных данных в коде.

Все зашито в пре-коммит хуки


# Форматирование, линтер, codestyle

Используем ruff

# Запуск приложения

## С Docker Compose

```shell
# При первом запуске данные загружаются автоматически из CSV
docker-compose up --build

# Для принудительной перезагрузки данных
RELOAD_DATA=true docker-compose up --build
```

## Локально

```shell
# Установка зависимостей
uv sync

# Запуск (RELOAD_DATA=true для загрузки данных из CSV)
RELOAD_DATA=true uv run python main.py
```

# API Эндпоинты

## Frontend API

### POST /api/v1/frontend-analyze

Основной эндпоинт для фронтенда. Агрегирует метрики из БД за два периода, отправляет в LLM и возвращает человекочитаемый анализ.

**Запрос:**
```json
{
  "period1": {
    "start": "2022-01-20T00:00:00Z",
    "end": "2022-01-24T23:59:59Z",
    "version": "v1.0.0"
  },
  "period2": {
    "start": "2022-01-25T00:00:00Z",
    "end": "2022-01-28T23:59:59Z",
    "version": "v2.0.0"
  },
  "project_name": "MAI Analytics",
  "target_urls": ["/home", "/products"],
  "reasoning_effort": "medium"
}
```

**Ответ:**
```json
{
  "success": true,
  "timestamp": "2024-01-31T12:00:00Z",
  "project": "MAI Analytics",
  "releases": ["v1.0.0", "v2.0.0"],
  "summary": "Краткое описание анализа...",
  "analysis": {
    "text": "Полный текст анализа от LLM...",
    "sections": {
      "summary": "...",
      "problems": "...",
      "recommendations": "..."
    },
    "model_info": {...}
  },
  "metrics_summary": {
    "period1": {
      "version": "v1.0.0",
      "total_visits": 1500,
      "total_hits": 4500,
      "unique_clients": 1200
    },
    "period2": {...}
  },
  "validation": {"passed": true},
  "error": null
}
```

### GET /api/v1/available-dates

Получить доступный диапазон дат в БД.

**Ответ:**
```json
{
  "min_date": "2022-01-20T00:00:00",
  "max_date": "2022-01-28T23:59:59",
  "total_visits": 5000
}
```

### GET /api/v1/top-urls?limit=20

Получить топ URL по количеству визитов (для фильтров).

**Ответ:**
```json
{
  "urls": [
    {"url": "https://priem.mai.ru/", "visits": 1500},
    {"url": "https://priem.mai.ru/bachelor/programs/", "visits": 800}
  ]
}
```

## LLM API

### POST /api/v1/analyze-metrics

Прямой анализ метрик (формат из OpenAPI спецификации).

### POST /api/v1/compare-releases

Сравнение двух релизов.

### GET /api/v1/llm-health

Проверка состояния LLM сервиса.

## Другие эндпоинты

### GET /health

Healthcheck приложения.

### POST /api/v1/ux-metrics

Получение UX метрик с фильтрацией.

# Переменные окружения

| Переменная | Описание | Default |
|-----------|----------|---------|
| `RELOAD_DATA` | Перезагрузить данные из CSV при старте | `false` |
| `YANDEX_FOLDER_ID` | ID папки Yandex Cloud | - |
| `YANDEX_API_KEY` | API ключ Yandex Cloud | - |
| `YANDEX_LLM_MODEL` | Модель LLM | `qwen3-235b-a22b-fp8` |
| `LOG_LEVEL` | Уровень логирования | `INFO` |

# Структура данных

## visits (таблица визитов)

- `visitId` - ID визита
- `watchIDs` - список ID хитов через запятую
- `dateTime` - время визита
- `isNewUser` - новый пользователь
- `startURL`, `endURL` - точки входа/выхода
- `pageViews` - количество просмотров
- `visitDuration` - длительность в секундах
- `regionCity` - город
- `deviceCategory` - 1=desktop, 2=mobile
- `operatingSystem`, `browser` - ОС и браузер
- `screenOrientationName` - landscape/portrait

## hits (таблица хитов)

- `watchID` - ID хита (связь с visits.watchIDs)
- `clientID` - ID клиента
- `URL` - URL страницы
- `dateTime` - время хита
- `title` - заголовок страницы
