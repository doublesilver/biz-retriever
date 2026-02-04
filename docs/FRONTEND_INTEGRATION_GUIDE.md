# 🎨 Frontend Integration Guide

**프론트엔드 개발자를 위한 Biz-Retriever API 연동 가이드**

이 문서는 Vercel Serverless API를 프론트엔드에서 사용하는 방법을 설명합니다.

---

## 📋 목차

1. [Quick Start](#quick-start)
2. [API Base URL](#api-base-url)
3. [인증 (Authentication)](#인증-authentication)
4. [API 엔드포인트](#api-엔드포인트)
5. [에러 핸들링](#에러-핸들링)
6. [코드 예제](#코드-예제)
7. [Best Practices](#best-practices)

---

## Quick Start

### 1. API 클라이언트 설정

```javascript
// lib/api.js
const API_BASE_URL = 'https://sideproject-one.vercel.app';

class APIClient {
  constructor() {
    this.baseURL = API_BASE_URL;
    this.token = localStorage.getItem('access_token');
  }

  // Helper: Authorization 헤더 생성
  getHeaders() {
    const headers = {
      'Content-Type': 'application/json',
    };
    
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    
    return headers;
  }

  // Helper: Fetch wrapper
  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      ...options,
      headers: {
        ...this.getHeaders(),
        ...options.headers,
      },
    };

    try {
      const response = await fetch(url, config);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'API request failed');
      }

      return data;
    } catch (error) {
      console.error('API Error:', error);
      throw error;
    }
  }

  // GET 요청
  async get(endpoint) {
    return this.request(endpoint, { method: 'GET' });
  }

  // POST 요청
  async post(endpoint, body) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  // PUT 요청
  async put(endpoint, body) {
    return this.request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(body),
    });
  }

  // DELETE 요청
  async delete(endpoint) {
    return this.request(endpoint, { method: 'DELETE' });
  }

  // Token 저장
  setToken(token) {
    this.token = token;
    localStorage.setItem('access_token', token);
  }

  // Token 삭제
  clearToken() {
    this.token = null;
    localStorage.removeItem('access_token');
  }
}

// Singleton instance
const api = new APIClient();
export default api;
```

---

## API Base URL

### Production
```javascript
const API_BASE_URL = 'https://sideproject-one.vercel.app';
```

### Development (Local)
```javascript
const API_BASE_URL = 'http://localhost:8000';
```

### 환경 변수 사용 (권장)
```javascript
// .env
VITE_API_BASE_URL=https://sideproject-one.vercel.app

// lib/api.js
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
```

---

## 인증 (Authentication)

### 1. 회원가입

```javascript
// auth.js
import api from './lib/api.js';

async function register(email, password, name) {
  try {
    const data = await api.post('/api/auth?action=register', {
      email,
      password,
      name,
    });
    
    console.log('Registration successful:', data);
    return data;
  } catch (error) {
    console.error('Registration failed:', error);
    throw error;
  }
}

// 사용 예시
register('user@example.com', 'SecurePass123!', '홍길동');
```

### 2. 로그인

```javascript
async function login(email, password) {
  try {
    const data = await api.post('/api/auth?action=login', {
      email,
      password,
    });
    
    // JWT Token 저장
    api.setToken(data.access_token);
    
    console.log('Login successful:', data);
    return data;
  } catch (error) {
    console.error('Login failed:', error);
    throw error;
  }
}

// 사용 예시
login('user@example.com', 'SecurePass123!');
```

### 3. 현재 사용자 정보 조회

```javascript
async function getCurrentUser() {
  try {
    const data = await api.get('/api/auth?action=me');
    console.log('Current user:', data);
    return data;
  } catch (error) {
    console.error('Failed to get current user:', error);
    throw error;
  }
}

// 사용 예시
getCurrentUser();
```

### 4. 로그아웃

```javascript
function logout() {
  api.clearToken();
  console.log('Logged out successfully');
}
```

---

## API 엔드포인트

### 1. 공고 관리 (Bids)

#### 공고 목록 조회
```javascript
async function getBids(page = 1, pageSize = 20) {
  const data = await api.get(`/api/bids?action=list&page=${page}&page_size=${pageSize}`);
  return data;
}

// 사용 예시
const bids = await getBids(1, 20);
console.log(`Total: ${bids.total}, Items: ${bids.items.length}`);
```

#### 공고 상세 조회
```javascript
async function getBidDetail(bidId) {
  const data = await api.get(`/api/bids?action=detail&id=${bidId}`);
  return data;
}

// 사용 예시
const bid = await getBidDetail(123);
console.log('Bid title:', bid.title);
```

#### 공고 생성 (테스트용)
```javascript
async function createBid(bidData) {
  const data = await api.post('/api/bids?action=create', bidData);
  return data;
}

// 사용 예시
const newBid = await createBid({
  title: '테스트 공고',
  agency: '테스트 기관',
  base_price: 1000000,
  deadline: '2026-12-31',
});
```

#### 공고 삭제
```javascript
async function deleteBid(bidId) {
  const data = await api.delete(`/api/bids?action=delete&id=${bidId}`);
  return data;
}

// 사용 예시
await deleteBid(123);
```

---

### 2. 키워드 관리 (Keywords)

#### 키워드 목록 조회
```javascript
async function getKeywords() {
  const data = await api.get('/api/keywords?action=list');
  return data;
}

// 사용 예시
const keywords = await getKeywords();
console.log(`Total keywords: ${keywords.total}`);
```

#### 키워드 생성
```javascript
async function createKeyword(keyword) {
  const data = await api.post('/api/keywords?action=create', { keyword });
  return data;
}

// 사용 예시
const newKeyword = await createKeyword('AI');
console.log('Keyword created:', newKeyword.keyword);
```

#### 키워드 삭제
```javascript
async function deleteKeyword(keywordId) {
  const data = await api.delete(`/api/keywords?action=delete&id=${keywordId}`);
  return data;
}

// 사용 예시
await deleteKeyword(1);
```

#### 제외 키워드 목록 조회
```javascript
async function getExcludeKeywords() {
  const data = await api.get('/api/keywords?action=exclude');
  return data;
}

// 사용 예시
const excludeKeywords = await getExcludeKeywords();
```

---

### 3. 결제 관리 (Payment)

#### 구독 정보 조회
```javascript
async function getSubscription() {
  const data = await api.get('/api/payment?action=subscription');
  return data;
}

// 사용 예시
const subscription = await getSubscription();
console.log('Plan:', subscription.plan_name);
console.log('Next billing:', subscription.next_billing_date);
```

#### 결제 내역 조회
```javascript
async function getPaymentHistory(page = 1, pageSize = 20) {
  const data = await api.get(
    `/api/payment?action=history&page=${page}&page_size=${pageSize}`
  );
  return data;
}

// 사용 예시
const payments = await getPaymentHistory(1, 10);
console.log(`Total payments: ${payments.total}`);
```

#### 결제 상태 조회
```javascript
async function getPaymentStatus(paymentId) {
  const data = await api.get(`/api/payment?action=status&payment_id=${paymentId}`);
  return data;
}

// 사용 예시
const payment = await getPaymentStatus('pay_abc123');
console.log('Status:', payment.status);
```

---

### 4. 프로필 관리 (Profile)

#### 프로필 조회
```javascript
async function getProfile() {
  const data = await api.get('/api/profile?action=get');
  return data;
}

// 사용 예시
const profile = await getProfile();
console.log('Company:', profile.company_name);
```

#### 프로필 생성
```javascript
async function createProfile(profileData) {
  const data = await api.post('/api/profile?action=create', profileData);
  return data;
}

// 사용 예시
const newProfile = await createProfile({
  company_name: '테스트 주식회사',
  brn: '123-45-67890',
  location_code: 'SEOUL',
});
```

#### 프로필 수정
```javascript
async function updateProfile(updates) {
  const data = await api.put('/api/profile?action=update', updates);
  return data;
}

// 사용 예시
await updateProfile({
  company_name: '새로운 회사명',
  keywords: 'AI, 빅데이터',
});
```

#### 면허 목록 조회
```javascript
async function getLicenses() {
  const data = await api.get('/api/profile?action=licenses');
  return data;
}

// 사용 예시
const licenses = await getLicenses();
```

#### 실적 목록 조회
```javascript
async function getPerformances() {
  const data = await api.get('/api/profile?action=performances');
  return data;
}

// 사용 예시
const performances = await getPerformances();
```

---

### 5. 파일 업로드 (Upload)

#### PDF 파일 업로드 및 AI 분석
```javascript
async function uploadPDF(file) {
  const formData = new FormData();
  formData.append('file', file);

  try {
    const response = await fetch(`${API_BASE_URL}/api/upload`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${api.token}`,
      },
      body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || 'Upload failed');
    }

    return data;
  } catch (error) {
    console.error('Upload error:', error);
    throw error;
  }
}

// 사용 예시 (HTML file input)
const fileInput = document.getElementById('fileInput');
fileInput.addEventListener('change', async (e) => {
  const file = e.target.files[0];
  if (file && file.type === 'application/pdf') {
    const result = await uploadPDF(file);
    console.log('AI Analysis:', result.analysis);
  }
});
```

---

## 에러 핸들링

### 공통 에러 처리
```javascript
async function safeAPICall(apiFunction, ...args) {
  try {
    return await apiFunction(...args);
  } catch (error) {
    // 에러 타입별 처리
    if (error.message.includes('401')) {
      // 인증 실패
      console.error('Authentication failed. Please login again.');
      api.clearToken();
      window.location.href = '/login';
    } else if (error.message.includes('403')) {
      // 권한 없음
      console.error('Permission denied.');
      alert('접근 권한이 없습니다.');
    } else if (error.message.includes('404')) {
      // 리소스 없음
      console.error('Resource not found.');
      alert('요청한 리소스를 찾을 수 없습니다.');
    } else if (error.message.includes('500')) {
      // 서버 에러
      console.error('Server error.');
      alert('서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
    } else {
      // 기타 에러
      console.error('Unknown error:', error);
      alert('오류가 발생했습니다: ' + error.message);
    }
    
    throw error;
  }
}

// 사용 예시
await safeAPICall(getBids, 1, 20);
```

### Toast 알림 예시
```javascript
function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);
  
  setTimeout(() => {
    toast.remove();
  }, 3000);
}

// API 호출 시 사용
try {
  const data = await createKeyword('AI');
  showToast('키워드가 생성되었습니다.', 'success');
} catch (error) {
  showToast('키워드 생성에 실패했습니다.', 'error');
}
```

---

## 코드 예제

### 완전한 로그인 폼 예제
```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <title>Login Example</title>
</head>
<body>
  <form id="loginForm">
    <input type="email" id="email" placeholder="이메일" required>
    <input type="password" id="password" placeholder="비밀번호" required>
    <button type="submit">로그인</button>
  </form>

  <script type="module">
    import api from './lib/api.js';

    const form = document.getElementById('loginForm');
    form.addEventListener('submit', async (e) => {
      e.preventDefault();

      const email = document.getElementById('email').value;
      const password = document.getElementById('password').value;

      try {
        const data = await api.post('/api/auth?action=login', {
          email,
          password,
        });

        // Token 저장
        api.setToken(data.access_token);

        // 사용자 정보 조회
        const user = await api.get('/api/auth?action=me');
        console.log('Logged in as:', user.email);

        // 대시보드로 리다이렉트
        window.location.href = '/dashboard';
      } catch (error) {
        alert('로그인 실패: ' + error.message);
      }
    });
  </script>
</body>
</html>
```

### 공고 목록 렌더링 예제
```javascript
async function renderBids() {
  const container = document.getElementById('bidsContainer');
  
  try {
    // 로딩 표시
    container.innerHTML = '<p>Loading...</p>';

    // API 호출
    const data = await api.get('/api/bids?action=list&page=1&page_size=20');

    // 목록 렌더링
    container.innerHTML = `
      <h2>공고 목록 (총 ${data.total}건)</h2>
      <div class="bids-grid">
        ${data.items.map(bid => `
          <div class="bid-card">
            <h3>${bid.title}</h3>
            <p>기관: ${bid.agency}</p>
            <p>예산: ${bid.base_price?.toLocaleString()}원</p>
            <p>마감: ${bid.deadline}</p>
            <button onclick="viewDetail(${bid.id})">상세보기</button>
          </div>
        `).join('')}
      </div>
    `;
  } catch (error) {
    container.innerHTML = `<p class="error">공고를 불러오는데 실패했습니다: ${error.message}</p>`;
  }
}

// 페이지 로드 시 실행
document.addEventListener('DOMContentLoaded', renderBids);
```

---

## Best Practices

### 1. Token 관리
```javascript
// Token 자동 갱신 (Refresh Token 미구현 시)
setInterval(async () => {
  try {
    const user = await api.get('/api/auth?action=me');
    console.log('Token still valid:', user.email);
  } catch (error) {
    // Token 만료 시 로그아웃
    api.clearToken();
    window.location.href = '/login';
  }
}, 5 * 60 * 1000); // 5분마다 체크
```

### 2. 로딩 상태 관리
```javascript
class LoadingManager {
  constructor() {
    this.loading = false;
  }

  show() {
    this.loading = true;
    document.getElementById('spinner').style.display = 'block';
  }

  hide() {
    this.loading = false;
    document.getElementById('spinner').style.display = 'none';
  }

  async wrap(asyncFunction) {
    this.show();
    try {
      return await asyncFunction();
    } finally {
      this.hide();
    }
  }
}

const loading = new LoadingManager();

// 사용 예시
await loading.wrap(async () => {
  const bids = await api.get('/api/bids?action=list');
  return bids;
});
```

### 3. 캐싱
```javascript
class APICache {
  constructor(ttl = 5 * 60 * 1000) { // 5분 기본 TTL
    this.cache = new Map();
    this.ttl = ttl;
  }

  get(key) {
    const item = this.cache.get(key);
    if (!item) return null;

    if (Date.now() - item.timestamp > this.ttl) {
      this.cache.delete(key);
      return null;
    }

    return item.data;
  }

  set(key, data) {
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
    });
  }

  clear() {
    this.cache.clear();
  }
}

const cache = new APICache();

// 캐싱 적용 API 호출
async function getCachedBids(page = 1) {
  const cacheKey = `bids_page_${page}`;
  
  // 캐시 확인
  const cached = cache.get(cacheKey);
  if (cached) {
    console.log('Returning cached data');
    return cached;
  }

  // API 호출
  const data = await api.get(`/api/bids?action=list&page=${page}`);
  
  // 캐시 저장
  cache.set(cacheKey, data);
  
  return data;
}
```

### 4. Debouncing (검색 최적화)
```javascript
function debounce(func, delay) {
  let timeoutId;
  return function (...args) {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => func.apply(this, args), delay);
  };
}

// 사용 예시: 검색 입력
const searchInput = document.getElementById('search');
const debouncedSearch = debounce(async (query) => {
  const results = await api.get(`/api/bids?action=list&search=${query}`);
  renderSearchResults(results);
}, 300); // 300ms 후 실행

searchInput.addEventListener('input', (e) => {
  debouncedSearch(e.target.value);
});
```

### 5. 에러 로깅
```javascript
// Sentry 또는 로깅 서비스 연동
function logError(error, context = {}) {
  console.error('Error:', error);
  
  // Sentry로 전송 (예시)
  if (window.Sentry) {
    window.Sentry.captureException(error, {
      extra: context,
    });
  }
  
  // 서버로 전송 (예시)
  fetch('/api/logs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      error: error.message,
      stack: error.stack,
      context,
      timestamp: new Date().toISOString(),
    }),
  }).catch(console.error);
}

// 사용 예시
try {
  await api.get('/api/bids?action=list');
} catch (error) {
  logError(error, { endpoint: '/api/bids', action: 'list' });
  throw error;
}
```

---

## 추가 리소스

- **API Reference**: [`API_REFERENCE.md`](./API_REFERENCE.md) - 전체 API 문서
- **Cron Setup**: [`CRON_AUTOMATION_GUIDE.md`](./CRON_AUTOMATION_GUIDE.md) - 크론 작업 설정
- **Project Summary**: [`PROJECT_SUMMARY.md`](./PROJECT_SUMMARY.md) - 프로젝트 개요

---

**Last Updated**: 2026-02-04  
**API Version**: 1.0.0  
**Production URL**: https://sideproject-one.vercel.app
