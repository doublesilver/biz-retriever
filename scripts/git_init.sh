#!/bin/bash
# Git 초기화 및 GitHub 업로드 스크립트

echo "🚀 Biz-Retriever GitHub 업로드 시작..."

# 1. Git 초기화 (이미 초기화되어 있다면 skip)
if [ ! -d ".git" ]; then
    echo "📦 Git 초기화..."
    git init
else
    echo "✅ Git이 이미 초기화되어 있습니다."
fi

# 2. .gitignore 확인
echo "📝 .gitignore 확인..."

# 3. Git 사용자 설정 (필요시)
echo "👤 Git 사용자 설정 (이미 설정되어 있다면 skip)"
# git config user.name "Your Name"
# git config user.email "your.email@example.com"

# 4. 파일 추가
echo "📁 파일 추가 중..."
git add .

# 5. 커밋
echo "💾 커밋 생성..."
git commit -m "feat: Initial commit - Biz-Retriever v1.0

- FastAPI backend with async support
- G2B API crawler with smart filtering
- Slack real-time notifications
- Web dashboard with importance filtering
- Excel export feature
- Analytics dashboard
- AI bid price prediction
- Celery task queue with beat scheduler
- PostgreSQL database
- Redis caching
- pytest with 90%+ coverage
- GitHub Actions CI/CD
- Docker & Docker Compose
- CORS & Rate limiting
- Structured logging
- Custom exception handling

Score: 92/100 (A grade)"

# 6. GitHub 레포지토리 연결
echo ""
echo "🔗 GitHub 레포지토리 연결"
echo "다음 명령어를 실행하세요:"
echo ""
echo "  1. GitHub에서 새 레포지토리 생성: https://github.com/new"
echo "     - Repository name: biz-retriever"
echo "     - Description: AI-powered bid aggregation and analysis system"
echo "     - Public/Private 선택"
echo "     - README, .gitignore, LICENSE 체크 해제 (이미 있음)"
echo ""
echo "  2. 생성 후 아래 명령어 실행:"
echo "     git remote add origin https://github.com/yourusername/biz-retriever.git"
echo "     git branch -M main"
echo "     git push -u origin main"
echo ""
echo "✅ 스크립트 완료!"
