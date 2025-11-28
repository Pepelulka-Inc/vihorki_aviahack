from attr import dataclass


@dataclass(slots=True, frozen=True)
class Metric:
    name: str
