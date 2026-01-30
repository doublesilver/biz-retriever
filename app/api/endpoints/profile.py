from typing import Any, List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.logging import logger
from app.db.models import User
from app.db.session import get_db
from app.services.profile_service import profile_service

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
    plan = current_user.subscription.plan_name if current_user.subscription else "free"

    return {
        "id": profile.id,
        "company_name": profile.company_name,
        "brn": profile.brn,
        "representative": profile.representative,
        "address": profile.address,
        "location_code": profile.location_code,
        "company_type": profile.company_type,
        "keywords": profile.keywords,
        "credit_rating": profile.credit_rating,
        "employee_count": profile.employee_count,
        "founding_year": profile.founding_year,
        "main_bank": profile.main_bank,
        "standard_industry_codes": profile.standard_industry_codes,
        "slack_webhook_url": profile.slack_webhook_url,
        "is_email_enabled": profile.is_email_enabled,
        "is_slack_enabled": profile.is_slack_enabled,
        "licenses": [{"name": l.license_name, "number": l.license_number} for l in profile.licenses],
        "performances": [{"project": p.project_name, "amount": p.amount} for p in profile.performances],
        "plan_name": plan,
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이미지 또는 PDF 파일만 업로드 가능합니다.")

    try:
        content = await file.read()
        # AI 파싱 실행
        extracted_data = await profile_service.parse_business_certificate(content, mime_type=file.content_type)

        # 추출된 데이터로 프로필 업데이트 (기본 정보 자동 채우기)
        profile = await profile_service.create_or_update_profile(db, current_user.id, extracted_data)

        return {
            "message": "사업자등록증 파싱 및 프로필 업데이트 완료",
            "data": extracted_data,
            "profile_id": profile.id,
        }
    except Exception as e:
        logger.error(f"Profile upload error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


from app.schemas.profile import (UserLicenseCreate, UserLicenseResponse,
                                 UserPerformanceCreate,
                                 UserPerformanceResponse, UserProfileResponse,
                                 UserProfileUpdate)


@router.put("/", response_model=UserProfileResponse)
async def update_profile(
    profile_in: UserProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    프로필 정보 수동 수정 (알림 설정 포함)
    """
    # dict로 변환하여 서비스에 전달
    update_data = profile_in.model_dump(exclude_unset=True)

    profile = await profile_service.create_or_update_profile(db, current_user.id, update_data)
    return profile


# License Management Endpoints


@router.post("/licenses", response_model=UserLicenseResponse, status_code=status.HTTP_201_CREATED)
async def add_license(
    license_in: UserLicenseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Add a new license to user profile
    """
    profile = await profile_service.get_or_create_profile(db, current_user.id)
    license = await profile_service.add_license(db, profile.id, license_in.model_dump())
    return license


@router.get("/licenses", response_model=List[UserLicenseResponse])
async def get_licenses(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get all licenses for current user
    """
    profile = await profile_service.get_profile(db, current_user.id)
    if not profile:
        return []
    return profile.licenses


@router.delete("/licenses/{license_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_license(
    license_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> None:
    """
    Delete a license from user profile
    """
    profile = await profile_service.get_profile(db, current_user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    success = await profile_service.delete_license(db, profile.id, license_id)
    if not success:
        raise HTTPException(status_code=404, detail="License not found")


# Performance Management Endpoints


@router.post("/performances", response_model=UserPerformanceResponse, status_code=status.HTTP_201_CREATED)
async def add_performance(
    performance_in: UserPerformanceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Add a new performance record to user profile
    """
    profile = await profile_service.get_or_create_profile(db, current_user.id)
    performance = await profile_service.add_performance(db, profile.id, performance_in.model_dump())
    return performance


@router.get("/performances", response_model=List[UserPerformanceResponse])
async def get_performances(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get all performance records for current user
    """
    profile = await profile_service.get_profile(db, current_user.id)
    if not profile:
        return []
    return profile.performances


@router.delete("/performances/{performance_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_performance(
    performance_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> None:
    """
    Delete a performance record from user profile
    """
    profile = await profile_service.get_profile(db, current_user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    success = await profile_service.delete_performance(db, profile.id, performance_id)
    if not success:
        raise HTTPException(status_code=404, detail="Performance not found")
