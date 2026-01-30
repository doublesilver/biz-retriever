import asyncio
import json
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.db.models import UserLicense, UserPerformance, UserProfile


class ProfileService:
    """
    User Profile Service
    Phase 2: AI 기반 사업자 정보 추출 및 프로필 관리
    """

    def __init__(self):
        # Gemini API 설정 (google.genai 사용 - RPi 최적화)
        self.client = None
        if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.startswith("AIza"):
            try:
                from google import genai

                self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
                logger.info("ProfileService: Google Gemini API 초기화 완료")
            except ImportError:
                logger.warning("google-genai 패키지가 설치되지 않았습니다.")
            except Exception as e:
                logger.error(f"Gemini 초기화 실패: {e}")
        else:
            logger.warning(
                "GEMINI_API_KEY가 설정되지 않아 OCR 기능을 사용할 수 없습니다."
            )

    async def get_profile(
        self, session: AsyncSession, user_id: int
    ) -> Optional[UserProfile]:
        """사용자 프로필 조회"""
        stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_or_update_profile(
        self, session: AsyncSession, user_id: int, profile_data: Dict[str, Any]
    ) -> UserProfile:
        """사용자 프로필 생성 또는 수정"""
        profile = await self.get_profile(session, user_id)

        if profile:
            for key, value in profile_data.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)
        else:
            profile = UserProfile(user_id=user_id, **profile_data)
            session.add(profile)

        await session.commit()
        await session.refresh(profile)
        return profile

    async def parse_business_certificate(
        self, file_content: bytes, mime_type: str = "image/jpeg"
    ) -> Dict[str, Any]:
        """
        Gemini AI를 사용하여 사업자등록증 이미지/PDF에서 정보 추출
        """
        if not self.client:
            raise ValueError("Gemini API가 구성되지 않았습니다.")

        prompt = """
        이 이미지는 대한민국의 사업자등록증입니다. 다음 정보를 JSON 형식으로 추출해주세요:
        - company_name: 상호(법인명)
        - brn: 사업자등록번호 (숫자만)
        - representative: 대표자 성명
        - address: 사업장 소재지 (전체 주소)
        - company_type: 기업 구분 (예: 법인사업자, 개인사업자, 중소기업 등)
        - location_code: 주소의 시/도 코드 (서울: 11, 부산: 26, 대구: 27, 인천: 28, 광주: 29, 대전: 30, 울산: 31, 세종: 36, 경기: 41, 강원: 42, 충북: 43, 충남: 44, 전북: 45, 전남: 46, 경북: 47, 경남: 48, 제주: 49)

        JSON 결과만 출력하세요.
        """

        try:
            import base64

            # Gemini 멀티모달 호출 (google.genai 방식)
            image_data = base64.standard_b64encode(file_content).decode("utf-8")

            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model="gemini-2.5-flash",
                contents=[
                    prompt,
                    {"inline_data": {"mime_type": mime_type, "data": image_data}},
                ],
            )

            # JSON 파싱
            text_response = response.text
            # Markdown code block 제거 (있을 경우)
            if "```json" in text_response:
                text_response = text_response.split("```json")[1].split("```")[0]
            elif "```" in text_response:
                text_response = text_response.split("```")[1].split("```")[0]

            return json.loads(text_response.strip())

        except Exception as e:
            logger.error(f"사업자등록증 분석 실패: {e}", exc_info=True)
            raise Exception(f"AI 분석 중 오류가 발생했습니다: {str(e)}")

    def match_location_code(self, address: str) -> str:
        """주소 기반 지역 코드 매칭 (Fallback용)"""
        location_map = {
            "서울": "11",
            "부산": "26",
            "대구": "27",
            "인천": "28",
            "광주": "29",
            "대전": "30",
            "울산": "31",
            "세종": "36",
            "경기": "41",
            "강원": "42",
            "충북": "43",
            "충남": "44",
            "전북": "45",
            "전남": "46",
            "경북": "47",
            "경남": "48",
            "제주": "49",
        }
        for city, code in location_map.items():
            if city in address:
                return code
        return "99"  # 기타/미분류

    async def get_or_create_profile(
        self, session: AsyncSession, user_id: int
    ) -> UserProfile:
        """사용자 프로필 조회 또는 생성"""
        profile = await self.get_profile(session, user_id)
        if not profile:
            profile = UserProfile(user_id=user_id)
            session.add(profile)
            await session.commit()
            await session.refresh(profile)
        return profile

    # License Management

    async def add_license(
        self, session: AsyncSession, profile_id: int, license_data: Dict[str, Any]
    ) -> UserLicense:
        """사용자 면허 추가"""
        license = UserLicense(profile_id=profile_id, **license_data)
        session.add(license)
        await session.commit()
        await session.refresh(license)
        return license

    async def delete_license(
        self, session: AsyncSession, profile_id: int, license_id: int
    ) -> bool:
        """사용자 면허 삭제"""
        stmt = select(UserLicense).where(
            UserLicense.id == license_id, UserLicense.profile_id == profile_id
        )
        result = await session.execute(stmt)
        license = result.scalar_one_or_none()

        if license:
            await session.delete(license)
            await session.commit()
            return True
        return False

    # Performance Management

    async def add_performance(
        self, session: AsyncSession, profile_id: int, performance_data: Dict[str, Any]
    ) -> UserPerformance:
        """사용자 실적 추가"""
        performance = UserPerformance(profile_id=profile_id, **performance_data)
        session.add(performance)
        await session.commit()
        await session.refresh(performance)
        return performance

    async def delete_performance(
        self, session: AsyncSession, profile_id: int, performance_id: int
    ) -> bool:
        """사용자 실적 삭제"""
        stmt = select(UserPerformance).where(
            UserPerformance.id == performance_id,
            UserPerformance.profile_id == profile_id,
        )
        result = await session.execute(stmt)
        performance = result.scalar_one_or_none()

        if performance:
            await session.delete(performance)
            await session.commit()
            return True
        return False


profile_service = ProfileService()
