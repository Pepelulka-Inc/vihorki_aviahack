from datetime import datetime

from attr import dataclass


@dataclass(slots=True, frozen=True)
class Visit:
    visitId: int
    watchIDs: str
    dateTime: datetime
    isNewUser: bool
    startURL: str
    endURL: str
    pageViews: int
    visitDuration: int
    regionCity: str
    clientID: str
    lastSearchEngineRoot: str
    deviceCategory: int
    mobilePhone: str
    mobilePhoneModel: str
    operatingSystem: str
    browser: str
    screenFormat: str
    screenOrientationName: str
