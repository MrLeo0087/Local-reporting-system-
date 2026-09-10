"""
Fake-report lockout logic.

Rule: if a citizen has had 3 or more reports rejected with reason
'false_report' within the last 7 days, lock them out of submitting new
reports for 7 days from now.

We check actual status_logs timestamps (not just the raw fake_report_count
counter) so that old false-report flags outside the 7-day window don't count
towards a fresh lock.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.citizen import Citizen
from app.models.status_log import StatusLog
from app.models.report import Report

FALSE_REPORT_THRESHOLD = 3
LOOKBACK_DAYS = 7
LOCK_DURATION_DAYS = 7


def register_false_report(db: Session, citizen: Citizen) -> None:
    """
    Call this right after a report is rejected with reason='false_report'.
    Increments the citizen's counter and, if they've crossed the threshold
    within the lookback window, sets report_locked_until.
    """
    citizen.fake_report_count = (citizen.fake_report_count or 0) + 1

    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)

    recent_false_reports = (
        db.query(StatusLog)
        .join(Report, StatusLog.report_id == Report.id)
        .filter(
            Report.citizen_id == citizen.id,
            StatusLog.action == "rejected",
            Report.rejection_reason == "false_report",
            StatusLog.created_at >= cutoff,
        )
        .count()
    )

    if recent_false_reports >= FALSE_REPORT_THRESHOLD:
        citizen.report_locked_until = datetime.now(timezone.utc) + timedelta(
            days=LOCK_DURATION_DAYS
        )

    db.add(citizen)


def check_not_locked(citizen: Citizen) -> None:
    """
    Raises a ValueError with a citizen-facing message if the citizen is
    currently locked out of submitting new reports. Caller (router) turns
    this into an HTTP error.
    """
    if citizen.report_locked_until is None:
        return

    now = datetime.now(timezone.utc)
    locked_until = citizen.report_locked_until
    if locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=timezone.utc)

    if locked_until > now:
        formatted = locked_until.strftime("%Y-%m-%d %H:%M UTC")
        raise ValueError(
            f"Your account is temporarily restricted from submitting new reports "
            f"due to repeated false reports. You can submit again after {formatted}."
        )
