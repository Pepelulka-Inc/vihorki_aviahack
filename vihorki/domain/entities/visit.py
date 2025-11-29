from datetime import datetime

from attr import dataclass


@dataclass(slots=True, frozen=True)
class Visit:
    visit_id: int
    watch_ids: str
    date_time: datetime
    is_new_user: bool
    start_url: str
    end_url: str
    page_views: int
    visit_duration: int
    region_city: str
    client_id: str
    last_search_engine_root: str
    device_category: int
    mobile_phone: str
    mobile_phone_model: str
    operating_system: str
    browser: str
    screen_format: str
    screen_orientation_name: str
