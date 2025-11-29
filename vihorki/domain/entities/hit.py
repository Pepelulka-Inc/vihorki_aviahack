from datetime import datetime

from attr import dataclass


@dataclass(slots=True, frozen=True)
class Hit:
    watch_id: str
    client_id: str
    url: str
    datetime_hit: datetime
    title: str
