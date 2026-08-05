from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable, Iterator
from uuid import uuid4

from fastapi import HTTPException

from backend.pose_factory import create_pose_analyzer


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def default_analyzer_factory(exercise_code: str):
    return create_pose_analyzer(exercise_code)


@dataclass
class CoachingSession:
    session_id: str
    user_id: int
    exercise_code: str
    analyzer: object
    target_reps: int
    target_sets: int
    workout_plan_id: int | None
    created_at: datetime
    last_accessed_at: datetime
    lock: threading.RLock = field(default_factory=threading.RLock, repr=False)


class CoachingSessionStore:
    def __init__(
        self,
        *,
        ttl: timedelta | None = None,
        analyzer_factory: Callable[[str], object] = default_analyzer_factory,
        clock: Callable[[], datetime] = utc_now,
    ):
        self.ttl = ttl or timedelta(
            minutes=int(os.getenv("COACHING_SESSION_TTL_MINUTES", "30"))
        )
        self.analyzer_factory = analyzer_factory
        self.clock = clock
        self._sessions: dict[str, CoachingSession] = {}
        self._store_lock = threading.RLock()

    def create(
        self,
        *,
        user_id: int,
        exercise_code: str,
        target_reps: int,
        target_sets: int,
        workout_plan_id: int | None,
    ) -> CoachingSession:
        normalized_code = exercise_code.strip().upper()
        try:
            analyzer = self.analyzer_factory(normalized_code)
        except KeyError as exc:
            raise HTTPException(
                status_code=400, detail="지원하지 않는 코칭 운동입니다."
            ) from exc
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=500, detail="코칭 분석기를 생성하지 못했습니다."
            ) from exc

        now = self.clock()
        session = CoachingSession(
            session_id=str(uuid4()),
            user_id=user_id,
            exercise_code=normalized_code,
            analyzer=analyzer,
            target_reps=target_reps,
            target_sets=target_sets,
            workout_plan_id=workout_plan_id,
            created_at=now,
            last_accessed_at=now,
        )
        with self._store_lock:
            stale_sessions = [
                item
                for item in self._sessions.values()
                if item.user_id == user_id
                and item.exercise_code == normalized_code
            ]
        for stale in stale_sessions:
            with stale.lock:
                with self._store_lock:
                    if self._sessions.get(stale.session_id) is stale:
                        self._sessions.pop(stale.session_id, None)
        with self._store_lock:
            self._sessions[session.session_id] = session
        return session

    def _expired(self, session: CoachingSession, now: datetime) -> bool:
        return now - session.last_accessed_at >= self.ttl

    @contextmanager
    def locked(
        self, session_id: str, *, user_id: int
    ) -> Iterator[CoachingSession]:
        now = self.clock()
        with self._store_lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise HTTPException(
                    status_code=404, detail="분석 세션을 찾을 수 없습니다."
                )
            if session.user_id != user_id:
                raise HTTPException(
                    status_code=403, detail="코칭 세션에 접근할 권한이 없습니다."
                )
            if self._expired(session, now):
                self._sessions.pop(session_id, None)
                raise HTTPException(
                    status_code=410,
                    detail="코칭 세션이 만료되었습니다. 다시 시작해주세요.",
                )

        with session.lock:
            with self._store_lock:
                if self._sessions.get(session_id) is not session:
                    raise HTTPException(
                        status_code=404, detail="분석 세션을 찾을 수 없습니다."
                    )
                session.last_accessed_at = self.clock()
            yield session

    def reset(self, session_id: str, *, user_id: int) -> CoachingSession:
        with self.locked(session_id, user_id=user_id) as session:
            session.analyzer.reset()
            return session

    def delete(self, session_id: str, *, user_id: int) -> bool:
        with self._store_lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            if session.user_id != user_id:
                raise HTTPException(
                    status_code=403, detail="코칭 세션에 접근할 권한이 없습니다."
                )
        with session.lock:
            with self._store_lock:
                return self._sessions.pop(session_id, None) is not None

    def cleanup_expired(self) -> int:
        now = self.clock()
        removed = 0
        with self._store_lock:
            candidates = [
                item
                for item in self._sessions.values()
                if self._expired(item, now)
            ]
        for session in candidates:
            if not session.lock.acquire(blocking=False):
                continue
            try:
                with self._store_lock:
                    current = self._sessions.get(session.session_id)
                    if current is session and self._expired(session, self.clock()):
                        self._sessions.pop(session.session_id, None)
                        removed += 1
            finally:
                session.lock.release()
        return removed


coaching_session_store = CoachingSessionStore()
