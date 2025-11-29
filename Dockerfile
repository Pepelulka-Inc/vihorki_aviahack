FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /uvx /bin/

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy source code 
COPY . .

# Run using uv 
CMD ["uv", "run", "python", "main.py"]