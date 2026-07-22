from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from backend.models import Gym, TrainerMember, User, UserGym


def has_active_trainer(db: Session, user_id: int, account_type: str) -> bool:
    if account_type != "MEMBER":
        return False
    return bool(
        db.scalar(
            select(
                exists().where(
                    TrainerMember.member_id == user_id,
                    TrainerMember.status == "ACTIVE",
                )
            )
        )
    )


def get_pending_pt_request_count(
    db: Session,
    user_id: int,
    account_type: str,
) -> int:
    if account_type != "MEMBER":
        return 0
    return int(
        db.scalar(
            select(func.count(TrainerMember.trainer_member_id)).where(
                TrainerMember.member_id == user_id,
                TrainerMember.status == "PENDING",
            )
        )
        or 0
    )


def get_user_gym_name(db: Session, user_id: int) -> str | None:
    return db.scalar(
        select(Gym.gym_name)
        .join(UserGym, UserGym.gym_id == Gym.gym_id)
        .where(UserGym.user_id == user_id, Gym.is_active.is_(True))
    )


def serialize_relationship(db: Session, relationship: TrainerMember) -> dict:
    trainer = relationship.trainer
    member = relationship.member
    trainer_profile = trainer.trainer_profile
    return {
        "trainer_member_id": relationship.trainer_member_id,
        "trainer_id": relationship.trainer_id,
        "member_id": relationship.member_id,
        "status": relationship.status,
        "started_at": relationship.started_at,
        "ended_at": relationship.ended_at,
        "created_at": relationship.created_at,
        "trainer_name": trainer.name,
        "trainer_email": trainer.email,
        "member_name": member.name,
        "member_email": member.email,
        "gym_name": get_user_gym_name(db, trainer.user_id)
        or (trainer_profile.gym_name if trainer_profile else None),
        "career_years": trainer_profile.career_years if trainer_profile else None,
    }


def serialize_sent_request(db: Session, relationship: TrainerMember) -> dict:
    member = relationship.member
    return {
        "trainer_member_id": relationship.trainer_member_id,
        "member_id": relationship.member_id,
        "member_name": member.name,
        "member_email": member.email,
        "member_gym_name": get_user_gym_name(db, member.user_id),
        "status": relationship.status,
        "created_at": relationship.created_at,
    }


def serialize_received_request(db: Session, relationship: TrainerMember) -> dict:
    trainer = relationship.trainer
    trainer_profile = trainer.trainer_profile
    return {
        "trainer_member_id": relationship.trainer_member_id,
        "trainer_id": relationship.trainer_id,
        "trainer_name": trainer.name,
        "trainer_email": trainer.email,
        "trainer_gym_name": get_user_gym_name(db, trainer.user_id)
        or (trainer_profile.gym_name if trainer_profile else None),
        "trainer_career_years": trainer_profile.career_years if trainer_profile else None,
        "status": relationship.status,
        "created_at": relationship.created_at,
    }


def lock_users(db: Session, *user_ids: int) -> dict[int, User]:
    users = db.scalars(
        select(User)
        .where(User.user_id.in_(sorted(set(user_ids))))
        .order_by(User.user_id)
        .with_for_update()
    ).all()
    return {user.user_id: user for user in users}
