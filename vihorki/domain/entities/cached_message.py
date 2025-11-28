from pydantic import BaseModel


class CachedMetric(BaseModel):
    key: str
    value: dict
