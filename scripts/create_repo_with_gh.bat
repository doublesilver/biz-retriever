@echo off
REM GitHub CLI로 레포지토리 생성

echo ============================================================
echo GitHub CLI로 biz-retriever 레포지토리 생성
echo ============================================================
echo.

REM gh 경로 설정
set GH="C:\Program Files\GitHub CLI\gh.exe"

REM 1. 버전 확인
echo [1/4] GitHub CLI 버전 확인...
%GH% --version
echo.

REM 2. 인증 상태 확인
echo [2/4] 인증 상태 확인...
%GH% auth status
if errorlevel 1 (
    echo.
    echo ⚠️  로그인이 필요합니다!
    echo.
    echo [3/4] GitHub 로그인 시작...
    %GH% auth login --web
    
    if errorlevel 1 (
        echo ❌ 로그인 실패!
        pause
        exit /b 1
    )
)

echo.
echo ✅ 로그인 완료!
echo.

REM 3. 레포지토리 생성 및 푸시
echo [4/4] 레포지토리 생성 및 푸시...
echo.

%GH% repo create biz-retriever --public --description "🐕 AI-powered bid aggregation and analysis system" --source=. --remote=origin --push

if errorlevel 1 (
    echo.
    echo ❌ 레포지토리 생성 실패!
    echo.
    echo 수동 명령어:
    echo %GH% repo create biz-retriever --public --description "AI-powered bid aggregation system"
    echo git remote add origin https://github.com/doublesilver/biz-retriever.git
    echo git branch -M main
    echo git push -u origin main
    pause
    exit /b 1
)

echo.
echo ============================================================
echo ✅ 완료!
echo ============================================================
echo.
echo 레포지토리: https://github.com/doublesilver/biz-retriever
echo.
echo 다음 단계:
echo 1. GitHub 프로필 확인: https://github.com/doublesilver
echo 2. 프로필 README 업데이트
echo.
pause
