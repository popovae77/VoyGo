from enum import StrEnum


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
