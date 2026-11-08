from enum import Enum


class ReportSection(str, Enum):
    SUMMARY = "summary"
    REGIONS = "regions"
    PAYMENTS = "payments"
    BALANCE = "balance"
    USERS = "users"
    ADS = "ads"
    PUBLICATIONS = "publications"
    SERVICES = "services"
