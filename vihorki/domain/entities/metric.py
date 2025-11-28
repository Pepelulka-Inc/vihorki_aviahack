from attr import dataclass

from vihorki.domain.entities.hit import Hit
from vihorki.domain.entities.visit import Visit


@dataclass
class Metric:
    visit: Visit
    hits: list[Hit]
