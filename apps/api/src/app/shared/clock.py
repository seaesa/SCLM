"""The calendar the business runs on. Contract dates are Vietnamese calendar days: a contract that
ends on the 30th is over at midnight in Vietnam, not at midnight UTC (07:00 local)."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

BUSINESS_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")


def business_today() -> date:
    return datetime.now(BUSINESS_TIMEZONE).date()
