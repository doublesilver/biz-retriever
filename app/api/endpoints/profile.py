from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db.models import User
from app.services.profile_service import profile_service
from app.db.session import get_db
from app.core.logging import logger

router = APIRouter()

@router.get("/", response_model=dict)
async def get_my_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    현재 로그인한 사용자의 프로필 조회
    """
    profile = await profile_service.get_profile(db, current_user.id)
    if not profile:
        # 빈 프로필 초기화 가능성 고려
        return {"id": None, "company_name": None, "user_id": current_user.id}
    
    # 관계형 데이터(License, Performance) 포함
    return {
        "id": profile.id,
        "company_name": profile.company_name,
        "brn": profile.brn,
        "representative": profile.representative,
        "address": profile.address,
        "location_code": profile.location_code,
        "company_type": profile.company_type,
        "licenses": [{"name": l.license_name, "number": l.license_number} for l in profile.licenses],
        "performances": [{"project": p.project_name, "amount": p.amount} for p in profile.performances]
    }

@router.post("/upload-certificate", response_model=dict)
async def upload_business_certificate(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    사업자등록증 이미지 업로드 및 AI 파싱 실행
    """
    if not (file.content_type.startswith("image/") or file.content_type == "application/pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미지 또는 PDF 파일만 업로드 가능합니다."
        )

    try:
        content = await file.read()
        # AI 파싱 실행
        extracted_data = await profile_service.parse_business_certificate(
            content, 
            mime_type=file.content_type
        )
        
        # 추출된 데이터로 프로필 업데이트 (기본 정보 자동 채우기)
        profile = await profile_service.create_or_update_profile(
            db, 
            current_user.id, 
            extracted_data
        )
        
        return {
            "message": "사업자등록증 파싱 및 프로필 업데이트 완료",
            "data": extracted_data,
            "profile_id": profile.id
        }
    except Exception as e:
        logger.error(f"Profile upload error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.put("/", response_model=dict)
async def update_profile(
    profile_in: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    프로필 정보 수동 수정
    """
    profile = await profile_service.create_or_update_profile(
        db, 
        current_user.id, 
        profile_in
    )
    return {"message": "프로필 수정 완료", "id": profile.id}
