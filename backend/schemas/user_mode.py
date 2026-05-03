"""User mode + tier enums."""
from enum import Enum


class UserMode(str, Enum):
    junior = "junior"
    professional = "professional"

    @classmethod
    def coerce(cls, value: str | None) -> "UserMode":
        if not value:
            return cls.professional
        v = value.strip().lower()
        if v in {"junior", "jr", "entry", "student"}:
            return cls.junior
        return cls.professional


class UserTier(str, Enum):
    FREE = "FREE"
    PRO = "PRO"

    @classmethod
    def coerce(cls, value: str | None) -> "UserTier":
        if not value:
            return cls.FREE
        v = value.strip().upper()
        return cls.PRO if v == "PRO" else cls.FREE
