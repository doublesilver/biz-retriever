from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Subscription, User
from app.core.logging import logger

class SubscriptionService:
    def __init__(self):
        pass

    async def get_user_plan(self, user: User) -> str:
        """
        Get user's current plan name.
        Defaults to 'free' if no active subscription found.
        """
        if not user.subscription:
            return "free"
        
        if not user.subscription.is_active:
            return "free"
            
        return user.subscription.plan_name

    async def get_plan_limits(self, plan_name: str) -> dict:
        """
        Return limits for the given plan.
        """
        limits = {
            "free": {
                "hard_match_limit": 3,
                "ai_analysis_limit": 5,
                "keywords_limit": 5
            },
            "basic": {
                "hard_match_limit": 50,
                "ai_analysis_limit": 100,
                "keywords_limit": 20
            },
            "pro": {
                "hard_match_limit": 9999,
                "ai_analysis_limit": 9999,
                "keywords_limit": 100
            }
        }
        return limits.get(plan_name, limits["free"])

    async def check_hard_match_limit(self, user: User, current_count: int) -> bool:
        """
        Check if user can view more hard matches.
        (Actually, we usually limit the *results returned* or *access*, not strictly 'count' usage unless credit based)
        Requirement says: "Free: 3건 제한".
        This implies we just truncate the list to 3 for Free users.
        """
        plan = await self.get_user_plan(user)
        limits = await self.get_plan_limits(plan)
        limit = limits["hard_match_limit"]
        
        # This method might be utility to get the limit number
        return limit

subscription_service = SubscriptionService()
