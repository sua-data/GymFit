from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Notification, User
from backend.security import get_current_user


router = APIRouter(prefix="/api/notifications", tags=["notifications"])


def serialize_notification(item: Notification) -> dict:
    return {
        "notification_id": item.notification_id,
        "title": item.title,
        "message": item.message,
        "notification_type": item.notification_type or "SYSTEM",
        "target_url": item.target_url,
        "reference_id": item.reference_id,
        "is_read": item.is_read,
        "created_at": item.created_at,
    }


@router.get("")
def list_notifications(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = db.scalars(
        select(Notification)
        .where(Notification.user_id == current_user.user_id)
        .order_by(Notification.created_at.desc(), Notification.notification_id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    total = db.scalar(
        select(func.count(Notification.notification_id)).where(
            Notification.user_id == current_user.user_id
        )
    ) or 0
    return {"items": [serialize_notification(item) for item in items], "total": int(total)}


@router.get("/unread-count")
def unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    count = db.scalar(
        select(func.count(Notification.notification_id)).where(
            Notification.user_id == current_user.user_id,
            Notification.is_read.is_(False),
        )
    ) or 0
    return {"unread_count": int(count)}


@router.patch("/read-all")
def read_all_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        db.execute(
            update(Notification)
            .where(
                Notification.user_id == current_user.user_id,
                Notification.is_read.is_(False),
            )
            .values(is_read=True)
        )
        db.commit()
        return {"success": True, "unread_count": 0}
    except Exception as error:
        db.rollback()
        raise HTTPException(status_code=500, detail="알림을 읽음 처리하지 못했습니다.") from error


@router.patch("/{notification_id}/read")
def read_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.scalar(
        select(Notification).where(
            Notification.notification_id == notification_id,
            Notification.user_id == current_user.user_id,
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다.")
    try:
        item.is_read = True
        db.commit()
        return serialize_notification(item)
    except Exception as error:
        db.rollback()
        raise HTTPException(status_code=500, detail="알림을 읽음 처리하지 못했습니다.") from error
