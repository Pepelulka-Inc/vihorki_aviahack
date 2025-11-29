# Testing Guide

## Running Tests

### Install Dependencies

```bash
uv sync
```

### Run All Tests

```bash
pytest vihorki/metrics_analyzer/tests/ -v
```

### Run Specific Test File

```bash
pytest vihorki/metrics_analyzer/tests/test_clients.py -v
pytest vihorki/metrics_analyzer/tests/test_orchestrator.py -v
```

### Run with Coverage

```bash
pytest vihorki/metrics_analyzer/tests/ --cov=vihorki/metrics_analyzer --cov-report=html
```

## Test Structure

```
tests/
├── __init__.py
├── test_clients.py          # Tests for API and LLM clients
└── test_orchestrator.py     # Tests for orchestrator
```

## What's Tested

### API Client Tests
- Initialization
- Payload validation
- Metrics submission
- Error handling

### LLM Client Tests
- Initialization with/without credentials
- Metrics analysis
- Recommendations generation
- Error handling

### Orchestrator Tests
- Complete workflow (validation → API → LLM)
- Release comparison
- Health checks
- Error scenarios

## Manual Testing

See `example_usage.py` for manual testing examples with real API calls.

## Mocking

Tests use `unittest.mock` and `pytest-asyncio` for async testing without real API calls.