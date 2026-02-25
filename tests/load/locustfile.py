"""
Locust 부하 테스트 설정
API 성능 및 동시 접속 테스트

사용법:
    # 기본 실행 (Web UI)
    locust -f tests/load/locustfile.py --host=http://localhost:8000

    # 헤드리스 모드
    locust -f tests/load/locustfile.py --host=http://localhost:8000 \
        --headless --users 100 --spawn-rate 10 --run-time 60s

    # 특정 사용자 클래스만 실행
    locust -f tests/load/locustfile.py --host=http://localhost:8000 \
        BidBrowserUser
"""

import random
import string

from locust import HttpUser, between, events, task
from locust.runners import MasterRunner


def random_email():
    """랜덤 이메일 생성"""
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"loadtest_{suffix}@example.com"


def random_password():
    """유효한 랜덤 비밀번호 생성"""
    return f"LoadTest{random.randint(100, 999)}!"


class BizRetrieverUser(HttpUser):
    """
    기본 사용자 행동 시뮬레이션
    - 공고 목록 조회
    - 공고 상세 조회
    - 검색
    """

    wait_time = between(1, 3)  # 요청 간 1~3초 대기

    def on_start(self):
        """테스트 시작 시 회원가입 및 로그인"""
        self.email = random_email()
        self.password = random_password()
        self.token = None

        # 회원가입
        response = self.client.post(
            "/api/v1/auth/register",
            json={"email": self.email, "password": self.password},
            name="회원가입",
        )

        if response.status_code == 201:
            # 로그인
            response = self.client.post(
                "/api/v1/auth/login/access-token",
                data={"username": self.email, "password": self.password},
                name="로그인",
            )
            if response.status_code == 200:
                self.token = response.json()["access_token"]

    @property
    def auth_headers(self):
        """인증 헤더"""
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    @task(10)
    def browse_bids(self):
        """공고 목록 조회 (가장 빈번한 작업)"""
        self.client.get(
            "/api/v1/bids/",
            params={"skip": 0, "limit": 20},
            headers=self.auth_headers,
            name="공고 목록 조회",
        )

    @task(5)
    def search_bids(self):
        """키워드 검색"""
        keywords = ["식당", "카페", "위탁", "운영", "화환"]
        keyword = random.choice(keywords)
        self.client.get(
            "/api/v1/bids/",
            params={"keyword": keyword, "skip": 0, "limit": 20},
            headers=self.auth_headers,
            name="키워드 검색",
        )

    @task(3)
    def view_bid_detail(self):
        """공고 상세 조회"""
        bid_id = random.randint(1, 100)
        with self.client.get(
            f"/api/v1/bids/{bid_id}",
            headers=self.auth_headers,
            name="공고 상세 조회",
            catch_response=True,
        ) as response:
            if response.status_code == 404:
                response.success()  # 404는 정상으로 처리

    @task(2)
    def view_analytics(self):
        """통계 조회"""
        self.client.get("/api/v1/analytics/summary", headers=self.auth_headers, name="대시보드 요약")

    @task(1)
    def health_check(self):
        """헬스체크"""
        self.client.get("/health", name="헬스체크")


class HeavyUser(HttpUser):
    """
    고부하 사용자 시뮬레이션
    - 빠른 요청
    - 대량 데이터 조회
    """

    wait_time = between(0.1, 0.5)  # 빠른 요청

    def on_start(self):
        """로그인"""
        self.email = random_email()
        self.password = random_password()
        self.token = None

        # 회원가입 및 로그인
        self.client.post(
            "/api/v1/auth/register",
            json={"email": self.email, "password": self.password},
        )
        response = self.client.post(
            "/api/v1/auth/login/access-token",
            data={"username": self.email, "password": self.password},
        )
        if response.status_code == 200:
            self.token = response.json()["access_token"]

    @property
    def auth_headers(self):
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    @task(5)
    def bulk_read(self):
        """대량 조회"""
        self.client.get(
            "/api/v1/bids/",
            params={"skip": 0, "limit": 100},
            headers=self.auth_headers,
            name="대량 공고 조회 (100건)",
        )

    @task(3)
    def rapid_search(self):
        """빠른 연속 검색"""
        for keyword in ["식당", "카페", "위탁"]:
            self.client.get(
                "/api/v1/bids/",
                params={"keyword": keyword},
                headers=self.auth_headers,
                name="연속 검색",
            )

    @task(2)
    def analytics_heavy(self):
        """분석 API 호출"""
        self.client.get(
            "/api/v1/analytics/trends",
            params={"days": 30},
            headers=self.auth_headers,
            name="30일 트렌드",
        )


class AnonymousUser(HttpUser):
    """
    비인증 사용자 시뮬레이션
    - 헬스체크
    - 메트릭 조회
    - 공개 API
    """

    wait_time = between(2, 5)

    @task(5)
    def health_check(self):
        """헬스체크"""
        self.client.get("/health", name="[Anonymous] 헬스체크")

    @task(3)
    def metrics(self):
        """메트릭 조회"""
        self.client.get("/metrics", name="[Anonymous] 메트릭")

    @task(2)
    def openapi_docs(self):
        """API 문서 조회"""
        self.client.get("/api/v1/openapi.json", name="[Anonymous] OpenAPI")


class AdminUser(HttpUser):
    """
    관리자 사용자 시뮬레이션
    - 크롤러 상태 확인
    - 필터 관리
    - 엑셀 내보내기
    """

    wait_time = between(3, 10)

    def on_start(self):
        """관리자 로그인"""
        self.email = random_email()
        self.password = random_password()
        self.token = None

        # 회원가입 및 로그인
        self.client.post(
            "/api/v1/auth/register",
            json={"email": self.email, "password": self.password},
        )
        response = self.client.post(
            "/api/v1/auth/login/access-token",
            data={"username": self.email, "password": self.password},
        )
        if response.status_code == 200:
            self.token = response.json()["access_token"]

    @property
    def auth_headers(self):
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    @task(3)
    def check_crawler_status(self):
        """크롤러 상태 확인"""
        self.client.get(
            "/api/v1/crawler/status",
            headers=self.auth_headers,
            name="[Admin] 크롤러 상태",
        )

    @task(2)
    def view_filters(self):
        """필터 목록 조회"""
        self.client.get(
            "/api/v1/filters/exclusions",
            headers=self.auth_headers,
            name="[Admin] 필터 목록",
        )

    @task(1)
    def export_excel(self):
        """엑셀 내보내기"""
        self.client.get(
            "/api/v1/export/excel",
            headers=self.auth_headers,
            name="[Admin] 엑셀 내보내기",
        )

    @task(1)
    def view_websocket_stats(self):
        """WebSocket 통계"""
        self.client.get(
            "/api/v1/realtime/ws/stats",
            headers=self.auth_headers,
            name="[Admin] WebSocket 통계",
        )


# 테스트 결과 리포팅
@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """테스트 종료 시 결과 출력"""
    if isinstance(environment.runner, MasterRunner):
        print("\n" + "=" * 50)
        print("부하 테스트 완료")
        print("=" * 50)

        stats = environment.runner.stats
        print(f"총 요청 수: {stats.total.num_requests}")
        print(f"실패 요청 수: {stats.total.num_failures}")
        print(f"평균 응답 시간: {stats.total.avg_response_time:.2f}ms")
        print(f"최대 응답 시간: {stats.total.max_response_time:.2f}ms")
        print(f"요청/초: {stats.total.current_rps:.2f}")

        if stats.total.num_failures > 0:
            failure_rate = (stats.total.num_failures / stats.total.num_requests) * 100
            print(f"실패율: {failure_rate:.2f}%")
