from enum import Enum


class RegionStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
