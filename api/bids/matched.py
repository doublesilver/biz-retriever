"""
GET /api/bids/matched
Hard Match 입찰 공고 조회 (3단계 검증: 지역, 면허, 실적)

Performance Optimized:
- Lazy imports for heavy libraries (SQLAlchemy, services)
- Reduced cold start time
"""
from http.server import BaseHTTPRequestHandler
import sys
from pathlib import Path
import asyncio
import json
from urllib.parse import parse_qs, urlparse
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Essential imports only (lightweight)
from lib.utils import send_json, send_error, handle_cors_preflight
from lib.auth import require_auth
from lib.db import get_db


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """CORS preflight 처리"""
        if handle_cors_preflight(self):
            return
    
    def do_GET(self):
        """Hard Match 입찰 공고 조회"""
        try:
            # 1. JWT 인증
            user_payload = require_auth(self)
            if not user_payload:
                return  # 이미 401 응답 전송됨
            
            # 2. 쿼리 파라미터 파싱
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            
            page = int(query_params.get('page', ['1'])[0])
            limit = int(query_params.get('limit', ['20'])[0])
            sort_by = query_params.get('sort_by', ['deadline'])[0]
            
            # 검증
            if page < 1:
                page = 1
            if limit < 1 or limit > 100:
                limit = 20
            if sort_by not in ['deadline', 'price', 'importance_score']:
                sort_by = 'deadline'
            
            # 3. 비동기 처리
            result = asyncio.run(self.get_matched_bids(
                user_payload,
                page,
                limit,
                sort_by
            ))
            
            # 4. 응답
            send_json(self, 200, result)
            
        except ValueError as e:
            send_error(self, 400, str(e))
        except Exception as e:
            send_error(self, 500, f"Internal server error: {str(e)}")
    
    async def get_matched_bids(
        self,
        user_payload: dict,
        page: int,
        limit: int,
        sort_by: str
    ) -> dict:
        """Hard Match 입찰 공고 조회 비즈니스 로직"""
        # Lazy imports (performance optimization)
        from sqlalchemy import select, and_
        from sqlalchemy.orm import selectinload
        from app.db.models import User, UserProfile, BidAnnouncement
        from app.services.match_service import hard_match_engine
        from app.services.subscription_service import subscription_service
        from app.core.cache import get_cached, set_cached
        from datetime import datetime
        
        async for db in get_db():
            # 1. 사용자 ID 추출
            user_id = user_payload.get("user_id")
            if not user_id:
                # 이메일로 조회 (하위 호환성)
                email = user_payload.get("sub")
                user_result = await db.execute(
                    select(User).where(User.email == email)
                )
                user = user_result.scalar_one_or_none()
            else:
                user_result = await db.execute(
                    select(User).where(User.id == user_id)
                )
                user = user_result.scalar_one_or_none()
            
            if not user:
                raise ValueError("User not found")
            
            # 2. 사용자 플랜 확인
            plan = await subscription_service.get_user_plan(user)
            plan_limits = await subscription_service.get_plan_limits(plan)
            hard_match_limit = plan_limits["hard_match_limit"]
            
            # 3. Redis 캐시 확인 (bid IDs만 캐싱)
            cache_key = f"matched_bids:user_{user.id}:sort_{sort_by}"
            cached_data = await get_cached(cache_key)
            
            if cached_data:
                # 캐시 히트: bid IDs로 DB 조회
                matched_bid_ids = cached_data.get("bid_ids", [])
            else:
                # 캐시 미스: Hard Match 실행
                matched_bid_ids = await self._perform_hard_match(db, user)
                
                # Redis에 캐싱 (3분 TTL)
                await set_cached(
                    cache_key,
                    {"bid_ids": matched_bid_ids, "timestamp": datetime.utcnow().isoformat()},
                    expire=180  # 3분
                )
            
            # 4. 플랜 제한 적용
            total_matched = len(matched_bid_ids)
            limited_bid_ids = matched_bid_ids[:hard_match_limit]
            
            # 5. 페이지네이션 적용
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            page_bid_ids = limited_bid_ids[start_idx:end_idx]
            
            # 6. DB에서 bid 객체 조회 및 정렬
            if not page_bid_ids:
                items = []
            else:
                query = select(BidAnnouncement).where(
                    BidAnnouncement.id.in_(page_bid_ids)
                )
                
                # 정렬 적용
                if sort_by == 'deadline':
                    query = query.order_by(BidAnnouncement.deadline.asc())
                elif sort_by == 'price':
                    query = query.order_by(BidAnnouncement.estimated_price.desc())
                elif sort_by == 'importance_score':
                    query = query.order_by(BidAnnouncement.importance_score.desc())
                
                result = await db.execute(query)
                bids = result.scalars().all()
                
                # 응답 형식 변환
                items = []
                for bid in bids:
                    items.append({
                        "id": bid.id,
                        "title": bid.title,
                        "content": bid.content[:200] + "..." if len(bid.content) > 200 else bid.content,
                        "agency": bid.agency,
                        "posted_at": bid.posted_at.isoformat() if bid.posted_at else None,
                        "url": bid.url,
                        "source": bid.source,
                        "deadline": bid.deadline.isoformat() if bid.deadline else None,
                        "estimated_price": bid.estimated_price,
                        "importance_score": bid.importance_score,
                        "status": bid.status,
                        "region_code": bid.region_code,
                        "license_requirements": bid.license_requirements,
                        "min_performance": bid.min_performance,
                        "created_at": bid.created_at.isoformat() if bid.created_at else None,
                        "updated_at": bid.updated_at.isoformat() if bid.updated_at else None
                    })
            
            # 7. 응답 생성
            return {
                "items": items,
                "total": total_matched,
                "limit": hard_match_limit,
                "plan": plan,
                "page": page,
                "page_size": limit,
                "total_pages": (len(limited_bid_ids) + limit - 1) // limit if limit > 0 else 0
            }
    
    async def _perform_hard_match(self, db, user) -> list[int]:
        """
        Hard Match 실행
        
        Returns:
            매칭된 bid ID 리스트
        """
        # 1. 사용자 프로필 조회 (licenses, performances eager loading)
        profile_query = select(UserProfile).where(
            UserProfile.user_id == user.id
        ).options(
            selectinload(UserProfile.licenses),
            selectinload(UserProfile.performances)
        )
        profile_result = await db.execute(profile_query)
        profile = profile_result.scalar_one_or_none()
        
        if not profile:
            # 프로필이 없으면 빈 리스트 반환
            return []
        
        # 2. 모든 활성 입찰 공고 조회
        bids_query = select(BidAnnouncement).where(
            and_(
                BidAnnouncement.status.in_(['new', 'reviewing']),  # 활성 상태만
                BidAnnouncement.deadline >= datetime.utcnow()  # 마감 안 된 것만
            )
        )
        bids_result = await db.execute(bids_query)
        bids = bids_result.scalars().all()
        
        # 3. Hard Match Engine으로 필터링
        matched_bid_ids = []
        for bid in bids:
            is_match, reasons, details = hard_match_engine.evaluate(bid, profile)
            if is_match:
                matched_bid_ids.append(bid.id)
        
        return matched_bid_ids
