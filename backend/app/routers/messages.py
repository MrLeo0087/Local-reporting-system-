"""
The message thread attached to a single report — lets the reporting citizen
and the assigned staff member talk directly (e.g. citizen asking for a
progress update, staff asking a clarifying question). Private to those two
parties; nobody else (including admin, and other staff) can read or post.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.report import Report
from app.models.message import Message
from app.schemas.message import MessageIn, MessageOut
from app.auth.dependencies import get_current_citizen_or_staff

router = APIRouter(tags=["messages"])


def _authorize(kind: str, user, report: Report) -> None:
    if kind == "citizen":
        if report.citizen_id != user.id:
            raise HTTPException(status_code=403, detail="This isn't your report.")
    else:
        if user.role != "staff":
            raise HTTPException(
                status_code=403, detail="Admins don't message on individual reports."
            )
        if report.category != user.category or report.ward_no != user.ward_no:
            raise HTTPException(
                status_code=403, detail="This report is outside your assigned category/ward."
            )


def _to_message_out(m: Message) -> MessageOut:
    if m.citizen_id:
        sender_role, sender_name = "citizen", m.citizen.full_name
    else:
        sender_role, sender_name = "staff", m.staff.full_name
    return MessageOut(
        id=m.id, body=m.body, created_at=m.created_at,
        sender_role=sender_role, sender_name=sender_name,
    )


def _get_report_or_404(report_id: uuid.UUID, db: Session) -> Report:
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    return report


@router.get("/reports/{report_id}/messages", response_model=list[MessageOut])
def list_messages(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: tuple = Depends(get_current_citizen_or_staff),
):
    kind, user = actor
    report = _get_report_or_404(report_id, db)
    _authorize(kind, user, report)

    messages = (
        db.query(Message)
        .options(joinedload(Message.citizen), joinedload(Message.staff))
        .filter(Message.report_id == report_id)
        .order_by(Message.created_at)
        .all()
    )
    return [_to_message_out(m) for m in messages]


@router.post("/reports/{report_id}/messages", response_model=MessageOut, status_code=201)
def post_message(
    report_id: uuid.UUID,
    payload: MessageIn,
    db: Session = Depends(get_db),
    actor: tuple = Depends(get_current_citizen_or_staff),
):
    kind, user = actor
    report = _get_report_or_404(report_id, db)
    _authorize(kind, user, report)

    body = payload.body.strip()
    if not body:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    message = Message(
        report_id=report.id,
        citizen_id=user.id if kind == "citizen" else None,
        staff_id=user.id if kind == "staff" else None,
        body=body,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    # re-load with the relationship so _to_message_out can read sender_name
    message = (
        db.query(Message)
        .options(joinedload(Message.citizen), joinedload(Message.staff))
        .filter(Message.id == message.id)
        .first()
    )
    return _to_message_out(message)
