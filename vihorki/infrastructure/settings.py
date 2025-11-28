import os


# Имя хоста — это имя сервиса в docker-compose
DB_HOST = os.getenv("DB_HOST", "postgres")  # ← не "localhost"!
DB_PORT = os.getenv("DB_PORT", "5432")      # ← внутри сети Docker — стандартный порт 5432

DB_USER = os.getenv("POSTGRES_USER", "habrpguser")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "pgpwd4habr")
DB_NAME = os.getenv("POSTGRES_DB", "habrdb")
DB_URL = f'postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

REDIS_HOST = os.getenv('REDIS_HOST')
REDIS_PORT = os.getenv('REDIS_PORT')
REDIS_USER = os.getenv('REDIS_USER')
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')
REDIS_IS_CLUSTER = os.getenv('REDIS_IS_CLUSTER')
