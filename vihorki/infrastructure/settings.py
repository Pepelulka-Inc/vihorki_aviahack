import os


DB_USER = str(os.getenv('POSTGRES_USER'))
DB_PASSWORD = str(os.getenv('POSTGRES_PASSWORD'))
DB_HOST = str(os.getenv('POSTGRES_HOST'))
DB_NAME = str(os.getenv('POSTGRES_DB'))
DB_PORT = os.getenv('POSTGRES_PORT')

DB_URL = f'postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
