@echo off
REM GitHub 프로필 및 Biz-Retriever 레포 생성 스크립트

echo ============================================================
echo 🚀 Biz-Retriever GitHub 업로드 가이드
echo ============================================================
echo.

REM 현재 디렉토리 확인
echo 📍 현재 위치: %CD%
echo.

REM Step 1: 프로필 README 업데이트
echo ============================================================
echo Step 1: GitHub 프로필 README 업데이트
echo ============================================================
echo.
echo 1-1. 프로필 레포지토리 이동/생성
echo    레포: https://github.com/doublesilver/doublesilver
echo.
echo 1-2. UPDATED_GITHUB_PROFILE_README.md 내용을 복사하여
echo      doublesilver/README.md 파일에 붙여넣기
echo.
echo 1-3. 커밋 및 푸시
echo      cd path/to/doublesilver
echo      git add README.md
echo      git commit -m "feat: Add Biz-Retriever project to profile"
echo      git push origin main
echo.
pause

REM Step 2: Biz-Retriever 레포지토리 생성
echo ============================================================
echo Step 2: Biz-Retriever 레포지토리 생성
echo ============================================================
echo.
echo 2-1. GitHub에서 새 레포 생성
echo    URL: https://github.com/new
echo    - Repository name: biz-retriever
echo    - Description: 🐕 AI-powered bid aggregation and analysis system
echo    - Public 선택
echo    - Initialize 옵션 모두 체크 해제 (이미 파일 있음)
echo.
pause

REM Step 3: Git 초기화 및 푸시
echo ============================================================
echo Step 3: Git 초기화 및 푸시
echo ============================================================
echo.

REM Git 초기화
if not exist ".git" (
    echo 3-1. Git 초기화...
    git init
    echo ✅ Git 초기화 완료
) else (
    echo ✅ Git이 이미 초기화되어 있습니다.
)
echo.

REM .gitignore 확인
if not exist ".gitignore" (
    echo ⚠️  .gitignore 파일이 없습니다!
    pause
) else (
    echo ✅ .gitignore 확인 완료
)
echo.

REM 파일 추가
echo 3-2. 파일 스테이징...
git add .
echo ✅ 파일 추가 완료
echo.

REM 커밋
echo 3-3. 커밋 생성...
git commit -m "feat: Initial commit - Biz-Retriever v1.0" -m "- FastAPI backend with async support" -m "- G2B API crawler + Slack notifications" -m "- Excel export + Analytics dashboard" -m "- AI bid price prediction (ML)" -m "- pytest 90%%+ coverage + GitHub Actions CI" -m "- Docker + Celery + Redis + PostgreSQL" -m "Score: 98/100 (A+ grade)"

if errorlevel 1 (
    echo ❌ 커밋 실패! 변경사항을 확인하세요.
    pause
    exit /b 1
)

echo ✅ 커밋 완료
echo.

REM Remote 추가 및 푸시
echo 3-4. Remote 추가 및 푸시
echo.
echo 다음 명령어를 실행하세요:
echo.
echo    git remote add origin https://github.com/doublesilver/biz-retriever.git
echo    git branch -M main
echo    git push -u origin main
echo.

REM Step 4: 완료 안내
echo ============================================================
echo ✅ 스크립트 실행 완료!
echo ============================================================
echo.
echo 📌 다음 단계:
echo    1. 위의 git 명령어 실행
echo    2. GitHub 프로필 확인: https://github.com/doublesilver
echo    3. 레포지토리 확인: https://github.com/doublesilver/biz-retriever
echo.
echo 🎉 축하합니다! A+ 프로젝트 완성!
echo.
pause
