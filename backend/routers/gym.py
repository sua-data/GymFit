import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.gym_service import GymSelection, select_or_create_gym


router = APIRouter(prefix="/api/gyms", tags=["gyms"])
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
KAKAO_LOCAL_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"


def serialize_gym(gym) -> dict:
    return {
        "gym_id": gym.gym_id,
        "provider": gym.provider,
        "external_place_id": gym.external_place_id,
        "gym_name": gym.gym_name,
        "road_address": gym.road_address,
        "address": gym.address,
        "latitude": float(gym.latitude) if gym.latitude is not None else None,
        "longitude": float(gym.longitude) if gym.longitude is not None else None,
    }


@router.get("/search")
def search_gyms(query: str = Query(min_length=2, max_length=100)) -> dict:
    api_key = os.getenv("KAKAO_REST_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="장소 검색 API 키가 설정되지 않았습니다.",
        )
    try:
        response = requests.get(
            KAKAO_LOCAL_URL,
            headers={"Authorization": f"KakaoAK {api_key}"},
            params={"query": query.strip(), "size": 15},
            timeout=5,
        )
        response.raise_for_status()
        documents = response.json().get("documents", [])
    except (requests.RequestException, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="외부 장소 검색 서비스에 연결하지 못했습니다.",
        ) from error

    items = []
    for item in documents:
        place_id = str(item.get("id") or "").strip()
        name = str(item.get("place_name") or "").strip()
        road_address = str(item.get("road_address_name") or "").strip()
        address = str(item.get("address_name") or "").strip()
        if not place_id or not name or not (road_address or address):
            continue
        items.append({
            "provider": "KAKAO",
            "external_place_id": place_id,
            "gym_name": name,
            "road_address": road_address or address,
            "address": address or None,
            "latitude": float(item["y"]) if item.get("y") else None,
            "longitude": float(item["x"]) if item.get("x") else None,
        })
    return {"items": items}


@router.post("/select")
def select_gym(payload: GymSelection, db: Session = Depends(get_db)) -> dict:
    try:
        gym = select_or_create_gym(db, payload)
        db.commit()
        db.refresh(gym)
        return serialize_gym(gym)
    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="헬스장 정보를 저장하지 못했습니다.",
        ) from error
