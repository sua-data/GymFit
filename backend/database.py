import os
from collections.abc import Generator
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text
from sqlalchemy.orm import (
    DeclarativeBase,
    Session,
    sessionmaker,
)


# =========================================================
# 환경변수 불러오기
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_NAME = os.getenv("DB_NAME", "gymfit")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD")


if not DB_PASSWORD:
    raise RuntimeError(
        "DB_PASSWORD 환경변수가 설정되지 않았습니다."
    )


# =========================================================
# MariaDB 연결 URL
# 비밀번호에 @, / 등 특수문자가 있어도 안전하게 처리
# =========================================================

DATABASE_URL = URL.create(
    drivername="mysql+pymysql",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
    query={
        "charset": "utf8mb4",
    },
)


# =========================================================
# SQLAlchemy Engine
# =========================================================

engine = create_engine(
    DATABASE_URL,

    # 끊어진 커넥션을 사용하기 전에 자동 확인
    pool_pre_ping=True,

    # 일정 시간마다 커넥션 재생성
    pool_recycle=3600,

    # SQL 실행문 출력 여부
    # 개발 중 확인하려면 True로 변경
    echo=False,
)


# =========================================================
# DB 세션 생성기
# =========================================================

SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


# =========================================================
# SQLAlchemy 모델 기본 클래스
# =========================================================

class Base(DeclarativeBase):
    pass


# =========================================================
# FastAPI 의존성
# API 함수에서 db: Session = Depends(get_db) 형태로 사용
# =========================================================

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# =========================================================
# DB 연결 테스트
# =========================================================

def test_database_connection() -> None:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        print("GYMFIT MariaDB 연결 성공")

    except Exception as error:
        print("GYMFIT MariaDB 연결 실패:", error)
        raise