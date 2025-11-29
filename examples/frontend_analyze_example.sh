#!/bin/bash
# Пример вызова API для фронтенда

# Получить доступные даты в БД
echo "=== Available dates ==="
curl -s http://localhost:9002/api/v1/available-dates | python3 -m json.tool

echo ""
echo "=== Top URLs ==="
# Получить топ URL
curl -s "http://localhost:9002/api/v1/top-urls?limit=10" | python3 -m json.tool

echo ""
echo "=== Frontend Analysis ==="
# Основной запрос анализа
curl -X POST "http://localhost:9002/api/v1/frontend-analyze" \
  -H "Content-Type: application/json" \
  -d '{
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
    "project_name": "MAI Priem Analytics",
    "reasoning_effort": "medium"
  }' | python3 -m json.tool --no-ensure-ascii

