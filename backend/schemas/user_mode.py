"""User mode enum (junior vs professional)."""
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
