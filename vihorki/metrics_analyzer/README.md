# Metrics Analyzer Service

Сервис для анализа UX-метрик с использованием двух клиентов:
1. **Metrics Contract Client** - отправка метрик по OpenAPI контракту
2. **LLM Agent Client** - анализ метрик с помощью Yandex Cloud AI

## 📋 Структура проекта

```
vihorki/metrics_analyzer/
├── __init__.py              # Экспорт основных классов
├── models.py                # Pydantic модели данных (OpenAPI контракт)
├── metrics_client.py        # Клиент для отправки метрик в API
├── llm_client.py           # Клиент для работы с Yandex Cloud AI
├── orchestrator.py         # Оркестратор для координации клиентов
├── config.py               # Конфигурация сервиса
├── example_usage.py        # Примеры использования
└── README.md               # Документация
```

## 🚀 Быстрый старт

### 1. Установка зависимостей

Добавьте в `pyproject.toml`:

```toml
[project]
dependencies = [
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "httpx>=0.24.0",
    "openai>=1.0.0",
    "python-dotenv>=1.0.0",
]
```

Установите:
```bash
uv sync
```

### 2. Настройка окружения

Создайте файл `.env` в корне проекта:

```env
# Metrics API Configuration
METRICS_API_URL=http://localhost:8000
METRICS_API_KEY=your_api_key_here

# Yandex Cloud Configuration
YANDEX_FOLDER_ID=your_folder_id
YANDEX_API_KEY=your_api_key
YANDEX_LLM_MODEL=qwen3-235b-a22b-fp8

# Service Configuration
LOG_LEVEL=INFO
DEFAULT_REASONING_EFFORT=medium
ENABLE_API_SUBMISSION=true
ENABLE_LLM_ANALYSIS=true
```

### 3. Базовое использование

```python
import asyncio
from vihorki.metrics_analyzer import AnalysisOrchestrator
from vihorki.metrics_analyzer.config import load_config
from vihorki.metrics_analyzer.models import MetricsPayload

async def main():
    # Загрузка конфигурации
    config = load_config()
    
    # Создание оркестратора
    async with AnalysisOrchestrator(
        metrics_api_url=config.metrics_api_url,
        metrics_api_key=config.metrics_api_key,
        yandex_folder_id=config.yandex_folder_id,
        yandex_api_key=config.yandex_api_key
    ) as orchestrator:
        
        # Загрузка данных метрик
        payload = MetricsPayload(...)  # Ваши данные
        
        # Полный анализ
        results = await orchestrator.analyze_and_submit(
            payload=payload,
            focus_areas=["Блуждающие сессии", "Обратная навигация"]
        )
        
        print(results['llm_analysis']['analysis'])

asyncio.run(main())
```

## 📊 Компоненты сервиса

### 1. Metrics Contract Client

Клиент для отправки метрик в API согласно OpenAPI контракту.

```python
from vihorki.metrics_analyzer import MetricsContractClient

async with MetricsContractClient(
    base_url="http://api.example.com",
    api_key="your_key"
) as client:
    
    # Отправка метрик
    response = await client.send_metrics(payload)
    
    # Валидация перед отправкой
    is_valid, error = client.validate_payload(payload)
    
    # Проверка здоровья API
    is_healthy = await client.health_check()
```

**Основные методы:**
- `send_metrics(payload)` - отправка метрик
- `send_metrics_dict(dict)` - отправка из словаря
- `validate_payload(payload)` - валидация данных
- `health_check()` - проверка доступности API

### 2. LLM Agent Client

Клиент для анализа метрик с помощью Yandex Cloud AI.

```python
from vihorki.metrics_analyzer import LLMAgentClient

client = LLMAgentClient(
    folder_id="your_folder_id",
    api_key="your_api_key"
)

# Анализ метрик
result = await client.analyze_metrics(
    payload=payload,
    focus_areas=["Блуждающие сессии"],
    reasoning_effort="high"
)

# Продолжение анализа
follow_up = await client.continue_analysis(
    previous_response_id=result['response_id'],
    follow_up_question="Какие конкретные рекомендации?"
)

# Получение рекомендаций
recommendations = await client.get_recommendations(
    result,
    priority="high"
)
```

**Основные методы:**
- `analyze_metrics(payload, focus_areas, reasoning_effort)` - анализ метрик
- `continue_analysis(response_id, question)` - продолжение диалога
- `get_recommendations(analysis, priority)` - получение рекомендаций
- `explain_metric(metric_name, context)` - объяснение метрики

### 3. Analysis Orchestrator

Оркестратор координирует работу обоих клиентов.

```python
from vihorki.metrics_analyzer import AnalysisOrchestrator

async with AnalysisOrchestrator(
    metrics_api_url="http://api.example.com",
    yandex_folder_id="folder_id",
    yandex_api_key="api_key"
) as orchestrator:
    
    # Полный анализ
    results = await orchestrator.analyze_and_submit(
        payload=payload,
        submit_to_api=True,
        analyze_with_llm=True
    )
    
    # Сравнение релизов
    comparison = await orchestrator.compare_releases(payload)
    
    # Детальные рекомендации
    recommendations = await orchestrator.get_detailed_recommendations(
        results,
        priority="high"
    )
    
    # Проверка здоровья
    health = await orchestrator.health_check()
```

**Основные методы:**
- `analyze_and_submit()` - полный цикл анализа
- `compare_releases()` - сравнение двух релизов
- `get_detailed_recommendations()` - получение рекомендаций
- `health_check()` - проверка всех компонентов

## 📝 Модели данных

Все модели данных соответствуют OpenAPI контракту:

```python
from vihorki.metrics_analyzer.models import (
    MetricsPayload,      # Основной payload
    Release,             # Данные релиза
    AggregateMetrics,    # Агрегированные метрики
    NavigationPatterns,  # Паттерны навигации
    SessionComplexityMetrics,  # Метрики сложности сессий
    # ... и другие
)
```

## 🔍 Примеры использования

### Пример 1: Полный анализ

```python
from vihorki.metrics_analyzer.example_usage import example_full_analysis

# Запуск полного анализа с примерными данными
await example_full_analysis()
```

### Пример 2: Быстрое сравнение

```python
from vihorki.metrics_analyzer.example_usage import example_comparison_only

# Быстрое сравнение без LLM
await example_comparison_only()
```

### Пример 3: Проверка здоровья

```python
from vihorki.metrics_analyzer.example_usage import example_health_check

# Проверка всех компонентов
await example_health_check()
```

## 🎯 Фокусные области анализа

При анализе можно указать конкретные области для фокуса:

```python
focus_areas = [
    "Блуждающие сессии",
    "Обратная навигация",
    "Петли в навигации",
    "Конверсия в воронках",
    "Сложность сессий",
    "Поведение на мобильных устройствах"
]

results = await orchestrator.analyze_and_submit(
    payload=payload,
    focus_areas=focus_areas
)
```

## 🔧 Конфигурация

### Переменные окружения

| Переменная | Описание | Значение по умолчанию |
|-----------|----------|----------------------|
| `METRICS_API_URL` | URL метрик API | `http://localhost:8000` |
| `METRICS_API_KEY` | API ключ для метрик | - |
| `YANDEX_FOLDER_ID` | Yandex Cloud folder ID | - |
| `YANDEX_API_KEY` | Yandex Cloud API key | - |
| `YANDEX_LLM_MODEL` | Модель LLM | `qwen3-235b-a22b-fp8` |
| `LOG_LEVEL` | Уровень логирования | `INFO` |
| `DEFAULT_REASONING_EFFORT` | Уровень рассуждений | `medium` |

### Программная конфигурация

```python
from vihorki.metrics_analyzer.config import MetricsAnalyzerConfig

config = MetricsAnalyzerConfig(
    metrics_api_url="http://custom-api.com",
    yandex_folder_id="custom_folder",
    yandex_api_key="custom_key",
    default_reasoning_effort="high"
)
```

## 📚 Документация API

### OpenAPI контракт

Сервис реализует следующий контракт:

- **POST /metrics** - отправка метрик для анализа
  - Request: `MetricsPayload` (2 релиза для сравнения)
  - Response: 200 OK / 400 Bad Request

Полная спецификация в файле `/Users/nyamerka/Desktop/contract.txt`

## 🧪 Тестирование

Запуск примеров:

```bash
# Все примеры
python -m vihorki.metrics_analyzer.example_usage

# Или через uv
uv run python -m vihorki.metrics_analyzer.example_usage
```

## 🔐 Безопасность

- API ключи хранятся в переменных окружения
- Используется HTTPS для всех внешних запросов
- Валидация всех входных данных через Pydantic

## 📖 Дополнительная информация

### Блуждающие сессии (Wandering Sessions)

Сервис специализируется на выявлении "блуждающих сессий", которые характеризуются:

- Высоким количеством просмотров страниц без достижения цели
- Возвратами на ранее посещенные страницы
- Петлями в навигации
- Низкой конверсией в воронках
- Высокой сложностью сессий

### Yandex Cloud AI Integration

Сервис использует Yandex Cloud Responses API для:

- Анализа метрик с помощью LLM
- Выявления UX-проблем
- Генерации рекомендаций
- Объяснения метрик

## 🤝 Поддержка

Для вопросов и предложений создавайте issues в репозитории проекта.

## 📄 Лицензия

См. файл LICENSE в корне проекта.