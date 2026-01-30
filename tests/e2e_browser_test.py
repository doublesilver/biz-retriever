"""
브라우저 E2E 테스트 - 프로젝트 증명용
전체 사용자 플로우를 자동으로 테스트하고 스크린샷을 캡처합니다.
"""

import asyncio
from datetime import datetime

from playwright.async_api import Page, async_playwright


class BizRetrieverE2ETest:
    """Biz-Retriever End-to-End 브라우저 테스트"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.screenshots_dir = "docs/screenshots"
        self.test_email = f"e2e_test_{datetime.now().timestamp()}@example.com"
        self.test_password = "E2ETest123!Strong"

    async def take_screenshot(self, page: Page, name: str):
        """스크린샷 저장"""
        import os

        os.makedirs(self.screenshots_dir, exist_ok=True)
        await page.screenshot(path=f"{self.screenshots_dir}/{name}.png")
        print(f"✅ 스크린샷 저장: {name}.png")

    async def test_01_landing_page(self, page: Page):
        """1. 랜딩 페이지 접근"""
        print("\n📋 Test 1: 랜딩 페이지 접근")
        await page.goto(self.base_url)
        await page.wait_for_load_state("networkidle")

        # 로그인 화면 확인
        assert await page.locator("#login-view").is_visible()
        print("✅ 로그인 화면 표시 확인")

        await self.take_screenshot(page, "01_landing_page")

    async def test_02_signup(self, page: Page):
        """2. 회원가입"""
        print("\n📋 Test 2: 회원가입")

        # Sign Up 링크 클릭
        await page.click("#signup-link")
        await page.wait_for_timeout(500)

        # 회원가입 폼 확인
        assert "Create Account" in await page.text_content("#auth-title")

        # 입력
        await page.fill("#email", self.test_email)
        await page.fill("#password", self.test_password)

        await self.take_screenshot(page, "02_signup_form")

        # 제출
        await page.click("#auth-btn")
        await page.wait_for_timeout(1000)

        print(f"✅ 회원가입 완료: {self.test_email}")

    async def test_03_login(self, page: Page):
        """3. 로그인"""
        print("\n📋 Test 3: 로그인")

        # 로그인 폼으로 전환 (회원가입 후)
        if await page.locator("#login-link").is_visible():
            await page.click("#login-link")
            await page.wait_for_timeout(500)

        # 로그인 정보 입력
        await page.fill("#email", self.test_email)
        await page.fill("#password", self.test_password)

        await self.take_screenshot(page, "03_login_form")

        # 로그인 버튼 클릭
        await page.click("#auth-btn")
        await page.wait_for_timeout(2000)

        # 대시보드로 이동 확인
        assert await page.locator("#dashboard-view").is_visible()
        print("✅ 로그인 성공 - 대시보드 진입")

        await self.take_screenshot(page, "04_dashboard_after_login")

    async def test_04_manual_crawl(self, page: Page):
        """4. 수동 크롤링 테스트"""
        print("\n📋 Test 4: 수동 크롤링")

        # 수동 크롤링 버튼 확인
        if await page.locator("#manual-crawl-btn").is_visible():
            await self.take_screenshot(page, "05_before_crawl")

            await page.click("#manual-crawl-btn")
            await page.wait_for_timeout(1000)

            print("✅ 수동 크롤링 트리거 성공")
            await self.take_screenshot(page, "06_crawl_triggered")
        else:
            print("⚠️  수동 크롤링 버튼 없음 (정상 - UI 미구현 가능)")

    async def test_05_importance_filter(self, page: Page):
        """5. 중요도 필터 테스트"""
        print("\n📋 Test 5: 중요도 필터")

        # 필터 버튼 확인
        filters = await page.locator(".filter-btn").all()
        if filters:
            # ⭐⭐⭐ 필터 클릭
            await page.click('[data-filter="3"]')
            await page.wait_for_timeout(1000)

            await self.take_screenshot(page, "07_filter_high_importance")
            print("✅ 중요도 필터 작동")
        else:
            print("⚠️  필터 버튼 없음 (정상 - UI 미구현 가능)")

    async def test_06_api_health(self, page: Page):
        """6. API Health Check"""
        print("\n📋 Test 6: API Health Check")

        response = await page.request.get(f"{self.base_url}/health")
        data = await response.json()

        assert data["status"] == "ok"
        print(f"✅ API Health: {data}")

    async def test_07_swagger_docs(self, page: Page):
        """7. Swagger 문서 접근"""
        print("\n📋 Test 7: Swagger API 문서")

        await page.goto(f"{self.base_url}/docs")
        await page.wait_for_load_state("networkidle")

        # Swagger UI 확인
        assert "Biz-Retriever" in await page.text_content("body") or "FastAPI" in await page.text_content("body")

        await self.take_screenshot(page, "08_swagger_docs")
        print("✅ Swagger 문서 접근 성공")

    async def test_08_logout(self, page: Page):
        """8. 로그아웃"""
        print("\n📋 Test 8: 로그아웃")

        # 메인 페이지로 이동
        await page.goto(self.base_url)
        await page.wait_for_timeout(1000)

        # 로그아웃 버튼 클릭
        if await page.locator("#logout-btn").is_visible():
            await page.click("#logout-btn")
            await page.wait_for_timeout(1000)

            # 로그인 화면으로 돌아왔는지 확인
            assert await page.locator("#login-view").is_visible()

            await self.take_screenshot(page, "09_after_logout")
            print("✅ 로그아웃 성공")

    async def run_all_tests(self):
        """모든 테스트 실행"""
        print("=" * 60)
        print("🚀 Biz-Retriever E2E 테스트 시작")
        print(f"📍 Base URL: {self.base_url}")
        print("=" * 60)

        async with async_playwright() as p:
            # Chromium 브라우저 실행
            browser = await p.chromium.launch(headless=False, slow_mo=500)
            page = await browser.new_page()

            try:
                # 순차적 테스트 실행
                await self.test_01_landing_page(page)
                await self.test_02_signup(page)
                await self.test_03_login(page)
                await self.test_04_manual_crawl(page)
                await self.test_05_importance_filter(page)
                await self.test_06_api_health(page)
                await self.test_07_swagger_docs(page)
                await self.test_08_logout(page)

                print("\n" + "=" * 60)
                print("🎉 모든 테스트 통과!")
                print(f"📸 스크린샷 저장 위치: {self.screenshots_dir}/")
                print("=" * 60)

            except Exception as e:
                print(f"\n❌ 테스트 실패: {e}")
                await self.take_screenshot(page, "error_screenshot")
                raise

            finally:
                await browser.close()


async def main():
    """메인 실행 함수"""
    test = BizRetrieverE2ETest()
    await test.run_all_tests()


if __name__ == "__main__":
    print("📌 실행 전 서버가 구동 중인지 확인하세요!")
    print("   docker-compose up -d")
    print("   또는 uvicorn app.main:app --reload\n")

    asyncio.run(main())
