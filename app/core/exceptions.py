"""
Custom Exception 계층
개선사항: Generic Exception → 의미 있는 Exception 클래스
"""

class BizRetrieverException(Exception):
    """Base Exception for Biz-Retriever"""
    pass


# 크롤러 관련 예외
class CrawlerException(BizRetrieverException):
    """크롤러 관련 에러"""
    pass


class APIKeyInvalidError(CrawlerException):
    """API 키가 유효하지 않음"""
    pass


class CrawlerTimeoutError(CrawlerException):
    """크롤링 타임아웃"""
    pass


class ParsingError(CrawlerException):
    """데이터 파싱 에러"""
    pass


# 알림 관련 예외
class NotificationException(BizRetrieverException):
    """알림 관련 에러"""
    pass


class SlackWebhookError(NotificationException):
    """Slack Webhook 전송 실패"""
    pass


# 보안 관련 예외
class SecurityException(BizRetrieverException):
    """보안 관련 에러"""
    pass


class WeakPasswordError(SecurityException):
    """약한 비밀번호"""
    pass


class RateLimitExceededError(SecurityException):
    """Rate Limit 초과"""
    pass
