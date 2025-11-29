from sqlalchemy import Column, Integer, String, Boolean, DateTime, BigInteger
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class VisitTable(Base):
    __tablename__ = 'visits'

    visit_id = Column(BigInteger, primary_key=True, name='visitId')
    watch_ids = Column(String, name='watchIDs')
    date_time = Column(DateTime, name='dateTime')
    is_new_user = Column(Boolean, name='isNewUser')
    start_url = Column(String, name='startURL')
    end_url = Column(String, name='endURL')
    page_views = Column(Integer, name='pageViews')
    visit_duration = Column(Integer, name='visitDuration')
    region_city = Column(String, name='regionCity')
    client_id = Column(String, name='clientID')
    last_search_engine_root = Column(String, name='lastSearchEngineRoot')
    device_category = Column(Integer, name='deviceCategory')
    mobile_phone = Column(String, name='mobilePhone')
    mobile_phone_model = Column(String, name='mobilePhoneModel')
    operating_system = Column(String, name='operatingSystem')
    browser = Column(String, name='browser')
    screen_format = Column(String, name='screenFormat')
    screen_orientation_name = Column(String, name='screenOrientationName')


class HitTable(Base):
    __tablename__ = 'hits'

    watch_id = Column(String, primary_key=True, name='watch_id')
    client_id = Column(String, name='client_id')
    url = Column(String, name='url')
    datetime_hit = Column(DateTime, name='datetime_hit')
    title = Column(String, name='title')
