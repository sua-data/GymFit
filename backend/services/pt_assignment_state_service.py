from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import PtAssignment


def restore_assignments_for_deleted_workout_record(
    db: Session,
    *,
    workout_record_id: int,
) -> list[PtAssignment]:
    assignments = list(
        db.scalars(
            select(PtAssignment)
            .where(PtAssignment.workout_record_id == workout_record_id)
            .with_for_update()
        ).all()
    )
    for assignment in assignments:
        if assignment.status == "COMPLETED":
            assignment.status = "IN_PROGRESS"
        assignment.workout_record_id = None
        assignment.completed_at = None
    return assignments
