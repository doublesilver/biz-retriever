# GitHub Secrets 설정 가이드

## 필요한 Secrets

GitHub 저장소의 **Settings > Secrets and variables > Actions**에서 다음 Secrets를 추가하세요:

### 1. GEMINI_API_KEY
- **설명**: Google Gemini AI API 키
- **값**: `YOUR_GEMINI_API_KEY`
- **용도**: AI 분석 기능, Integration Tests

### 2. G2B_API_KEY
- **설명**: 나라장터(G2B) 공공데이터 API 키
- **값**: `YOUR_G2B_API_KEY`
- **용도**: 입찰 공고 크롤링, Integration Tests

### 3. SLACK_WEBHOOK_URL (선택)
- **설명**: Slack Webhook URL
- **값**: `https://hooks.slack.com/services/YOUR/WEBHOOK/URL`
- **용도**: 알림 기능 테스트

---

## Secrets 추가 방법

### 방법 1: GitHub 웹 UI
1. GitHub 저장소 페이지 접속
2. **Settings** 탭 클릭
3. 왼쪽 메뉴에서 **Secrets and variables** > **Actions** 클릭
4. **New repository secret** 버튼 클릭
5. Name과 Value 입력 후 **Add secret** 클릭

### 방법 2: GitHub CLI
```bash
# GitHub CLI 설치 확인
gh --version

# 로그인
gh auth login

# Secret 추가
gh secret set GEMINI_API_KEY -b "YOUR_GEMINI_API_KEY"
gh secret set G2B_API_KEY -b "YOUR_G2B_API_KEY"

# Secret 목록 확인
gh secret list
```

---

## Workflow에서 사용하는 방법

```yaml
- name: Run tests
  env:
    GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
    G2B_API_KEY: ${{ secrets.G2B_API_KEY }}
  run: |
    pytest tests/
```

---

## 보안 주의사항

1. **절대 코드에 직접 입력하지 마세요**
   - ❌ `GEMINI_API_KEY = "AIzaSy..."`
   - ✅ `GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")`

2. **로그에 출력되지 않도록 주의**
   - GitHub Actions는 자동으로 Secret 값을 `***`로 마스킹합니다

3. **주기적으로 키 갱신**
   - API 키가 노출되었다면 즉시 재발급

---

## 현재 Workflow 상태

### ✅ CI/CD Pipeline (`.github/workflows/ci.yml`)
- Unit 테스트만 실행 (Mock API 키 사용)
- Secrets 불필요

### ⚠️ Integration Tests (`.github/workflows/integration-tests.yml`)
- 실제 API 호출 테스트
- **Secrets 필요**: GEMINI_API_KEY, G2B_API_KEY
- 수동 실행 또는 주간 자동 실행

### ✅ Auto Format (`.github/workflows/auto-format.yml`)
- 코드 자동 포맷팅
- Secrets 불필요 (GITHUB_TOKEN 자동 제공)

---

## 문제 해결

### Secret이 작동하지 않을 때
1. Secret 이름이 정확한지 확인 (대소문자 구분)
2. Workflow 파일에서 `${{ secrets.SECRET_NAME }}` 형식 확인
3. 저장소 Settings에서 Secret이 추가되었는지 확인

### Integration Tests 실패 시
1. GitHub Secrets에 API 키가 추가되었는지 확인
2. API 키가 유효한지 확인 (만료되지 않았는지)
3. API 할당량이 남아있는지 확인
