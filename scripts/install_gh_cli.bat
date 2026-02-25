@echo off
echo ============================================================
echo GitHub CLI 다운로드 및 설치
echo ============================================================
echo.

REM GitHub CLI 최신 버전 다운로드
echo [1/3] GitHub CLI 다운로드 중...
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://github.com/cli/cli/releases/download/v2.63.2/gh_2.63.2_windows_amd64.msi' -OutFile '%TEMP%\gh_installer.msi' -UseBasicParsing}"

if errorlevel 1 (
    echo ❌ 다운로드 실패!
    echo.
    echo 수동 다운로드:
    echo https://github.com/cli/cli/releases/latest
    pause
    exit /b 1
)

echo ✅ 다운로드 완료!
echo.

REM 설치 파일 실행
echo [2/3] GitHub CLI 설치 중...
echo (관리자 권한이 필요합니다)
echo.

REM 자동 설치 (quiet mode)
msiexec.exe /i "%TEMP%\gh_installer.msi" /qn /norestart

if errorlevel 1 (
    echo.
    echo ⚠️  자동 설치 실패, 수동 설치 실행...
   start "" "%TEMP%\gh_installer.msi"
)

echo.
echo ✅ 설치 완료!
echo.

echo [3/3] 다음 단계
echo.
echo 1. 새 PowerShell 터미널 열기
echo 2. 다음 명령어 실행:
echo.
echo    gh --version
echo    gh auth login
echo    gh repo create biz-retriever --public --description "🐕 AI-powered bid aggregation and analysis system" --source=. --remote=origin --push
echo.
pause
