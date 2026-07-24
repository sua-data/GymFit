from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, or_, select, update
from sqlalchemy.orm import Session, joinedload

from backend.database import get_db
from backend.models import Notification, TrainerMember, User
from backend.pt_schemas import (
    PTListResponse,
    PTMemberSearchResponse,
    PTMyTrainerResponse,
    PTRequestCreate,
    PTRelationshipResponse,
    ReceivedPtRequestListResponse,
    SentPtRequestListResponse,
)
from backend.services.pt_service import (
    lock_users,
    serialize_received_request,
    serialize_relationship,
    serialize_sent_request,
)
from backend.services.notification_service import create_notification
from backend.security import get_current_user


router = APIRouter(prefix="/api/pt", tags=["pt"])


def require_role(user: User, account_type: str) -> None:
    if user.account_type != account_type:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="접근 권한이 없습니다.")
    if (
        account_type == "TRAINER"
        and (
            user.trainer_profile is None
            or user.trainer_profile.approval_status != "APPROVED"
            or user.trainer_profile.employment_status != "APPROVED"
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="트레이너 자격과 헬스장 소속이 모두 승인되어야 이 기능을 사용할 수 있습니다.",
        )


def relationship_query():
    return select(TrainerMember).options(
        joinedload(TrainerMember.trainer).selectinload(User.trainer_profile),
        joinedload(TrainerMember.member),
    )


@router.get("/members/search", response_model=PTMemberSearchResponse)
def search_members(
    email: str = Query(min_length=2, max_length=255),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_role(current_user, "TRAINER")
    keyword = email.strip().lower()
    members = db.scalars(
        select(User).where(
            User.account_type == "MEMBER",
            User.is_active.is_(True),
            User.user_id != current_user.user_id,
            User.email.ilike(f"%{keyword}%"),
        ).order_by(User.email).limit(30)
    ).all()
    relationship_rows = db.scalars(
        select(TrainerMember).where(
            TrainerMember.trainer_id == current_user.user_id,
            TrainerMember.member_id.in_([item.user_id for item in members] or [-1]),
            TrainerMember.status.in_(("PENDING", "ACTIVE")),
        )
    ).all()
    relationships = {item.member_id: item for item in relationship_rows}
    return {
        "items": [
            {
                "user_id": member.user_id,
                "name": member.name,
                "email": member.email,
                "relationship_status": relationships.get(member.user_id).status
                if relationships.get(member.user_id) else None,
                "trainer_member_id": relationships.get(member.user_id).trainer_member_id
                if relationships.get(member.user_id) else None,
            }
            for member in members
        ]
    }


@router.post("/requests", response_model=PTRelationshipResponse, status_code=status.HTTP_201_CREATED)
def create_request(
    payload: PTRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_role(current_user, "TRAINER")
    try:
        users = lock_users(db, current_user.user_id, payload.member_id)
        member = users.get(payload.member_id)
        if member is None or not member.is_active:
            raise HTTPException(status_code=404, detail="회원을 찾을 수 없습니다.")
        if member.user_id == current_user.user_id:
            raise HTTPException(status_code=400, detail="자기 자신에게 요청할 수 없습니다.")
        if member.account_type != "MEMBER":
            raise HTTPException(status_code=400, detail="일반 회원에게만 요청할 수 있습니다.")
        duplicate = db.scalar(
            select(TrainerMember).where(
                TrainerMember.trainer_id == current_user.user_id,
                TrainerMember.member_id == member.user_id,
                TrainerMember.status.in_(("PENDING", "ACTIVE")),
            ).with_for_update()
        )
        if duplicate:
            raise HTTPException(status_code=409, detail="이미 요청 중이거나 연결된 회원입니다.")
        relationship = TrainerMember(trainer_id=current_user.user_id, member_id=member.user_id)
        db.add(relationship)
        db.flush()
        create_notification(
            db,
            user_id=member.user_id,
            title="새로운 PT 연결 요청",
            message=f"{current_user.name} 트레이너님이 PT 연결을 요청했습니다.",
            notification_type="PT_REQUEST",
            target_url="/pt/requests",
            reference_id=relationship.trainer_member_id,
        )
        relationship = db.scalar(relationship_query().where(TrainerMember.trainer_member_id == relationship.trainer_member_id))
        result = serialize_relationship(db, relationship)
        db.commit()
        return result
    except HTTPException:
        db.rollback()
        raise
    except Exception as error:
        db.rollback()
        raise HTTPException(status_code=500, detail="PT 연결 요청을 저장하지 못했습니다.") from error


def list_relationships(db: Session, *conditions) -> dict:
    items = db.scalars(relationship_query().where(*conditions).order_by(TrainerMember.created_at.desc())).unique().all()
    return {"items": [serialize_relationship(db, item) for item in items]}


@router.get("/requests/sent", response_model=SentPtRequestListResponse)
def sent_requests(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(current_user, "TRAINER")
    items = db.scalars(
        relationship_query().where(
            TrainerMember.trainer_id == current_user.user_id,
            TrainerMember.status == "PENDING",
        ).order_by(TrainerMember.created_at.desc())
    ).unique().all()
    return {"items": [serialize_sent_request(db, item) for item in items]}


@router.get("/my-members", response_model=PTListResponse)
def my_members(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(current_user, "TRAINER")
    return list_relationships(db, TrainerMember.trainer_id == current_user.user_id, TrainerMember.status == "ACTIVE")


@router.get("/requests/received", response_model=ReceivedPtRequestListResponse)
def received_requests(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(current_user, "MEMBER")
    items = db.scalars(
        relationship_query().where(
            TrainerMember.member_id == current_user.user_id,
            TrainerMember.status == "PENDING",
        ).order_by(TrainerMember.created_at.desc())
    ).unique().all()
    return {"items": [serialize_received_request(db, item) for item in items]}


def get_owned_pending(db: Session, relationship_id: int, member_id: int) -> TrainerMember:
    relationship = db.scalar(
        relationship_query().where(
            TrainerMember.trainer_member_id == relationship_id,
            TrainerMember.member_id == member_id,
            TrainerMember.status == "PENDING",
        ).with_for_update()
    )
    if relationship is None:
        raise HTTPException(status_code=404, detail="처리할 PT 요청을 찾을 수 없습니다.")
    return relationship


@router.delete("/requests/{trainer_member_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_request(
    trainer_member_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_role(current_user, "TRAINER")
    try:
        relationship = db.scalar(
            relationship_query().where(
                TrainerMember.trainer_member_id == trainer_member_id
            ).with_for_update()
        )
        if relationship is None:
            raise HTTPException(status_code=404, detail="취소할 PT 요청을 찾을 수 없습니다.")
        if relationship.trainer_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="다른 트레이너의 요청은 취소할 수 없습니다.")
        if relationship.status != "PENDING":
            raise HTTPException(
                status_code=409,
                detail="PENDING 상태의 요청만 취소할 수 있습니다.",
            )

        member_id = relationship.member_id
        relationship_id = relationship.trainer_member_id
        db.execute(
            delete(Notification).where(
                Notification.user_id == member_id,
                Notification.notification_type == "PT_REQUEST",
                Notification.reference_id == relationship_id,
                Notification.is_read.is_(False),
            )
        )
        db.execute(
            update(Notification)
            .where(
                Notification.user_id == member_id,
                Notification.notification_type == "PT_REQUEST",
                Notification.reference_id == relationship_id,
                Notification.is_read.is_(True),
            )
            .values(target_url=None, reference_id=None)
        )
        db.delete(relationship)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as error:
        db.rollback()
        raise HTTPException(status_code=500, detail="PT 연결 요청을 취소하지 못했습니다.") from error


@router.patch("/requests/{trainer_member_id}/accept", response_model=PTRelationshipResponse)
def accept_request(trainer_member_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(current_user, "MEMBER")
    try:
        lock_users(db, current_user.user_id)
        relationship = get_owned_pending(db, trainer_member_id, current_user.user_id)
        active = db.scalar(
            select(TrainerMember).where(
                TrainerMember.member_id == current_user.user_id,
                TrainerMember.status == "ACTIVE",
            ).with_for_update()
        )
        if active:
            raise HTTPException(status_code=409, detail="이미 연결된 트레이너가 있습니다.")
        relationship.status = "ACTIVE"
        relationship.started_at = date.today()
        relationship.ended_at = None
        create_notification(
            db,
            user_id=relationship.trainer_id,
            title="PT 연결 요청이 수락되었습니다",
            message=f"{current_user.name}님과 PT 연결이 완료되었습니다.",
            notification_type="PT_REQUEST_ACCEPTED",
            target_url="/trainer/members",
            reference_id=relationship.trainer_member_id,
        )
        db.execute(
            update(Notification)
            .where(
                Notification.user_id == current_user.user_id,
                Notification.notification_type == "PT_REQUEST",
                Notification.reference_id == relationship.trainer_member_id,
            )
            .values(is_read=True)
        )
        db.flush()
        result = serialize_relationship(db, relationship)
        db.commit()
        return result
    except HTTPException:
        db.rollback()
        raise
    except Exception as error:
        db.rollback()
        raise HTTPException(status_code=500, detail="PT 요청을 수락하지 못했습니다.") from error


@router.patch("/requests/{trainer_member_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
def reject_request(trainer_member_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(current_user, "MEMBER")
    try:
        relationship = get_owned_pending(db, trainer_member_id, current_user.user_id)
        relationship_id = relationship.trainer_member_id
        trainer_id = relationship.trainer_id
        member_name = current_user.name
        db.delete(relationship)
        create_notification(
            db,
            user_id=trainer_id,
            title="PT 연결 요청이 거절되었습니다",
            message=f"{member_name}님이 PT 연결 요청을 거절했습니다.",
            notification_type="PT_REQUEST_REJECTED",
            target_url="/trainer/members",
            reference_id=relationship_id,
        )
        db.execute(
            update(Notification)
            .where(
                Notification.user_id == current_user.user_id,
                Notification.notification_type == "PT_REQUEST",
                Notification.reference_id == relationship_id,
            )
            .values(is_read=True)
        )
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as error:
        db.rollback()
        raise HTTPException(status_code=500, detail="PT 요청을 거절하지 못했습니다.") from error


@router.patch("/relationships/{trainer_member_id}/end", response_model=PTRelationshipResponse)
def end_relationship(trainer_member_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        relationship = db.scalar(
            relationship_query().where(
                TrainerMember.trainer_member_id == trainer_member_id,
                TrainerMember.status == "ACTIVE",
                or_(TrainerMember.trainer_id == current_user.user_id, TrainerMember.member_id == current_user.user_id),
            ).with_for_update()
        )
        if relationship is None:
            raise HTTPException(status_code=404, detail="종료할 PT 관계를 찾을 수 없습니다.")
        lock_users(db, relationship.member_id)
        other_user_id = (
            relationship.member_id
            if current_user.user_id == relationship.trainer_id
            else relationship.trainer_id
        )
        other_target_url = (
            "/pt/requests"
            if other_user_id == relationship.member_id
            else "/trainer/members"
        )
        relationship.status = "ENDED"
        relationship.ended_at = date.today()
        create_notification(
            db,
            user_id=other_user_id,
            title="PT 연결이 종료되었습니다",
            message=f"{current_user.name}님과의 PT 연결이 종료되었습니다.",
            notification_type="PT_RELATION_ENDED",
            target_url=other_target_url,
            reference_id=relationship.trainer_member_id,
        )
        db.flush()
        result = serialize_relationship(db, relationship)
        db.commit()
        return result
    except HTTPException:
        db.rollback()
        raise
    except Exception as error:
        db.rollback()
        raise HTTPException(status_code=500, detail="PT 연결을 종료하지 못했습니다.") from error


@router.get("/my-trainer", response_model=PTMyTrainerResponse)
def my_trainer(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(current_user, "MEMBER")
    relationship = db.scalar(
        relationship_query().where(
            TrainerMember.member_id == current_user.user_id,
            TrainerMember.status == "ACTIVE",
        ).order_by(TrainerMember.started_at.desc(), TrainerMember.trainer_member_id.desc())
    )
    return {"item": serialize_relationship(db, relationship) if relationship else None}
