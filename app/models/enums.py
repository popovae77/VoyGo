import sys

if sys.version_info >= (3, 11):
    from enum import StrEnum
else:
    from enum import Enum

    class StrEnum(str, Enum):
        pass


class TravelType(StrEnum):
    beach = "beach"
    active = "active"
    excursion = "excursion"
    city = "city"
    family = "family"
    cruise = "cruise"
    other = "other"


class ComfortLevel(StrEnum):
    economy = "economy"
    standard = "standard"
    comfort = "comfort"
