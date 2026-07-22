from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Notification, User


def create_notification(
    db: Session,
    *,
    user_id: int,
    title: str,
    message: str,
    notification_type: str,
    target_url: str | None = None,
    reference_id: int | None = None,
) -> Notification:
    user_exists = db.scalar(
        select(User.user_id).where(
            User.user_id == user_id,
            User.is_active.is_(True),
        )
    )
    if user_exists is None:
        raise ValueError("활성 사용자에게만 알림을 생성할 수 있습니다.")
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        target_url=target_url,
        reference_id=reference_id,
        is_read=False,
    )
    db.add(notification)
    return notification


def create_welcome_notification(
    db: Session,
    user_id: int,
    user_name: str,
) -> Notification:
    return create_notification(
        db,
        user_id=user_id,
        title="GYMFIT 가입을 환영합니다",
        message=f"{user_name}님의 회원가입이 완료되었습니다. 오늘부터 운동 기록을 시작해 보세요.",
        notification_type="WELCOME",
        target_url="/dashboard",
    )
