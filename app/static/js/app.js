// Phase 3: Mock Server Port Check (Default 8003 for Mock)
const API_BASE = '/api/v1'; // Logic: If serving from same origin.
// But if running index.html directly or from port 8000 while API is 8003, we need full URL.
// Since we serve static from same app, relative path '/api/v1' works IF user accesses http://localhost:8003.
// If user accesses 8000, they will fail.
// So I will assume user accesses the port where server is running.
let token = localStorage.getItem('access_token');

// Nodes
const loginView = document.getElementById('login-view');
const dashboardView = document.getElementById('dashboard-view');
const signupLink = document.getElementById('signup-link');
const loginLink = document.getElementById('login-link');
const authTitle = document.getElementById('auth-title');
const authBtn = document.getElementById('auth-btn');
const emailInput = document.getElementById('email');
const passwordInput = document.getElementById('password');
const uploadModal = document.getElementById('upload-modal');
const detailModal = document.getElementById('detail-modal');

let isLoginMode = true;
let currentImportanceFilter = null; // Phase 1: 중요도 필터

// Init
document.addEventListener('DOMContentLoaded', () => {
    if (token) {
        showDashboard();
    } else {
        showLogin();
    }
});

// Navigation
function showLogin() {
    loginView.style.display = 'block';
    dashboardView.style.display = 'none';
}

function showDashboard() {
    loginView.style.display = 'none';
    dashboardView.style.display = 'block';
    loadBids();
}

// Auth Logic
signupLink?.addEventListener('click', () => toggleAuthMode(false));
loginLink?.addEventListener('click', () => toggleAuthMode(true));

function toggleAuthMode(login) {
    isLoginMode = login;
    authTitle.textContent = login ? 'Welcome Back' : 'Create Account';
    authBtn.textContent = login ? 'Login' : 'Sign Up';
    document.getElementById('signup-prompt').style.display = login ? 'block' : 'none';
    document.getElementById('login-prompt').style.display = login ? 'none' : 'block';
}

authBtn.addEventListener('click', async () => {
    const email = emailInput.value;
    const password = passwordInput.value;
    const endpoint = isLoginMode ? '/auth/login/access-token' : '/auth/register';

    // Convert to URLSearchParams for OAuth2 PasswordRequestForm if login
    let body;
    let headers = {};

    if (isLoginMode) {
        body = new URLSearchParams();
        body.append('username', email); // OAuth2 expects username
        body.append('password', password);
        headers['Content-Type'] = 'application/x-www-form-urlencoded';
    } else {
        body = JSON.stringify({ email, password });
        headers['Content-Type'] = 'application/json';
    }

    try {
        const res = await fetch(`${API_BASE}${endpoint}`, {
            method: 'POST',
            headers: headers,
            body: body
        });

        const data = await res.json();

        if (!res.ok) throw new Error(data.detail || 'Auth failed');

        if (isLoginMode) {
            token = data.access_token;
            localStorage.setItem('access_token', token);
            showToast('Login Successful', 'success');
            showDashboard();
        } else {
            showToast('Account Created! Please Login.', 'success');
            toggleAuthMode(true);
        }
    } catch (e) {
        showToast(e.message, 'error');
    }
});

document.getElementById('logout-btn').addEventListener('click', () => {
    localStorage.removeItem('access_token');
    token = null;
    showLogin();
});

// Phase 1: 수동 크롤링 트리거
document.getElementById('manual-crawl-btn')?.addEventListener('click', async () => {
    const btn = document.getElementById('manual-crawl-btn');
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = '크롤링 중...';

    try {
        const res = await fetch(`${API_BASE}/crawler/trigger`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        const data = await res.json();

        if (!res.ok) throw new Error(data.detail || 'Failed');

        showToast('크롤링이 시작되었습니다!', 'success');

        // 5초 후 목록 새로고침
        setTimeout(() => loadBids(), 5000);
    } catch (e) {
        showToast(e.message, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
});

// Phase 1: 중요도 필터
function setImportanceFilter(score) {
    currentImportanceFilter = score;

    // 버튼 활성 상태 업데이트
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    if (score !== null) {
        document.querySelector(`[data-filter="${score}"]`)?.classList.add('active');
    }

    loadBids();
}

// Dashboard Logic
async function loadBids() {
    try {
        let url = `${API_BASE}/bids/`;

        // Phase 1: 중요도 필터 적용
        if (currentImportanceFilter !== null) {
            url += `?importance_score=${currentImportanceFilter}`;
        }

        const res = await fetch(url, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.status === 401) {
            // Token expired
            localStorage.removeItem('access_token');
            showLogin();
            return;
        }
        const data = await res.json();
        renderBids(data);
    } catch (e) {
        console.error(e);
    }
}

function renderBids(bids) {
    const grid = document.getElementById('bid-grid');
    grid.innerHTML = '';

    if (bids.length === 0) {
        grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 3rem; color: #64748b;">공고가 없습니다. 크롤링을 실행해주세요.</div>';
        return;
    }

    bids.forEach(bid => {
        const card = document.createElement('div');
        card.className = 'bid-card';
        const date = new Date(bid.created_at).toLocaleDateString();
        const statusClass = bid.processed ? 'status-processed' : 'status-pending';
        const statusText = bid.processed ? 'Processed' : 'Analyzing...';

        // Phase 1: 중요도 별표시
        const stars = '⭐'.repeat(bid.importance_score || 1);

        // Phase 2: 상태 뱃지
        const statusBadgeMap = {
            'new': { text: '신규', color: '#3b82f6' },
            'reviewing': { text: '검토중', color: '#f59e0b' },
            'bidding': { text: '투찰예정', color: '#10b981' },
            'completed': { text: '완료', color: '#6b7280' }
        };
        const statusInfo = statusBadgeMap[bid.status] || statusBadgeMap['new'];

        card.innerHTML = `
            <div class="status-badge ${statusClass}">${statusText}</div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 0.5rem;">
                <span style="font-size: 1.2rem;">${stars}</span>
                <span style="background: ${statusInfo.color}; color: white; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.75rem;">${statusInfo.text}</span>
            </div>
            <h3 class="bid-title">${bid.title}</h3>
            <div class="bid-meta">${date} | ${bid.source || 'Unknown'}</div>
            <p style="font-size: 0.9rem; color: #cbd5e1; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
                ${bid.content.substring(0, 100)}...
            </p>
        `;
        card.onclick = () => openDetail(bid);
        grid.appendChild(card);
    });
}

// Upload
document.getElementById('open-upload').addEventListener('click', () => {
    uploadModal.classList.add('active');
});

document.querySelectorAll('.modal-close').forEach(btn => {
    btn.onclick = () => {
        uploadModal.classList.remove('active');
        detailModal.classList.remove('active');
    };
});

const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');

dropZone.onclick = () => fileInput.click();

fileInput.onchange = async (e) => {
    const file = e.target.files[0];
    if (file) await uploadFile(file);
};

async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    try {
        const res = await fetch(`${API_BASE}/bids/upload`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData
        });

        if (!res.ok) throw new Error('Upload failed');

        showToast('File uploaded! Analysis started.', 'success');
        uploadModal.classList.remove('active');
        loadBids(); // Refresh list (might not be processed yet)
    } catch (e) {
        showToast(e.message, 'error');
    }
}

// Detail View
function openDetail(bid) {
    const content = document.getElementById('detail-content');
    const stars = '⭐'.repeat(bid.importance_score || 1);

    content.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 1rem;">
            <h2 style="margin: 0;">${bid.title}</h2>
            <span style="font-size: 1.5rem;">${stars}</span>
        </div>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem; padding: 1rem; background: rgba(0,0,0,0.2); border-radius: 8px;">
            <div><strong>출처:</strong> ${bid.source || 'Unknown'}</div>
            <div><strong>기관:</strong> ${bid.agency || 'N/A'}</div>
            <div><strong>마감일:</strong> ${bid.deadline ? new Date(bid.deadline).toLocaleString() : 'N/A'}</div>
            <div><strong>추정가:</strong> ${bid.estimated_price ? `${parseInt(bid.estimated_price).toLocaleString()}원` : 'N/A'}</div>
        </div>
        
        ${bid.keywords_matched && bid.keywords_matched.length > 0 ? `
            <div style="margin-bottom: 1rem;">
                <strong>매칭 키워드:</strong>
                ${bid.keywords_matched.map(k => `<span style="background: var(--primary); padding: 0.25rem 0.5rem; border-radius: 4px; margin-right: 0.5rem; font-size: 0.85rem;">${k}</span>`).join('')}
            </div>
        ` : ''}
        
        <div style="background: rgba(0,0,0,0.2); padding: 1rem; border-radius: 8px; margin-bottom: 1rem">
            <strong>공고 내용:</strong>
            <p style="margin-top: 0.5rem; white-space: pre-wrap; color: #cbd5e1">${bid.content}</p>
        </div>
        
        ${bid.analysis_result ? `
            <div style="border-left: 4px solid var(--success); padding-left: 1rem;">
                <h3 style="color: var(--success)">AI Analysis</h3>
                <p><strong>Summary:</strong> ${bid.analysis_result.summary || 'N/A'}</p>
                <p><strong>Keywords:</strong> ${(bid.analysis_result.keywords || []).join(', ')}</p>
            </div>
        ` : `
            <div style="color: var(--warning)">Analysis is in progress...</div>
        `}
        
        ${bid.url ? `
            <div style="margin-top: 1rem;">
                <a href="${bid.url}" target="_blank" style="color: var(--primary); text-decoration: underline;">원본 공고 보기 →</a>
            </div>
        ` : ''}

        <!-- Phase 3: AI Price Prediction -->
        <div style="margin-top: 1.5rem; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 1rem;">
            <h3>🤖 AI 투찰가 분석</h3>
            <button id="predict-btn-${bid.id}" class="btn" style="background: linear-gradient(135deg, #8b5cf6, #6d28d9); margin-top: 0.5rem;">
                💰 적정 투찰가 예측하기
            </button>
            <div id="prediction-result-${bid.id}" style="margin-top: 1rem; display: none;"></div>
        </div>
    `;
    detailModal.classList.add('active');

    // Add Event Listener
    setTimeout(() => {
        document.getElementById(`predict-btn-${bid.id}`)?.addEventListener('click', () => predictPrice(bid.id));
    }, 0);
}

// Phase 3: AI Price Prediction Logic
async function predictPrice(bidId) {
    const resultDiv = document.getElementById(`prediction-result-${bidId}`);
    const btn = document.getElementById(`predict-btn-${bidId}`);

    if (!resultDiv) return;

    btn.disabled = true;
    btn.textContent = 'AI 분석 중...';

    try {
        const res = await fetch(`${API_BASE}/analysis/predict-price/${bidId}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Prediction failed');

        const price = data.prediction.recommended_price;
        const confidence = data.prediction.confidence || 0.0;

        // Display logic
        let priceText = '분석 불가';
        if (price !== null && !isNaN(price)) {
            priceText = `${parseInt(price).toLocaleString()}원`;
        }

        resultDiv.style.display = 'block';
        resultDiv.innerHTML = `
            <div style="background: rgba(139, 92, 246, 0.2); border: 1px solid #8b5cf6; padding: 1rem; border-radius: 8px;">
                <h4 style="color: #c4b5fd; margin-bottom: 0.5rem;">AI 추천 투찰가</h4>
                <div style="font-size: 1.5rem; font-weight: bold; color: white;">
                    ${priceText}
                </div>
                <div style="font-size: 0.9rem; color: #a78bfa; margin-top: 0.25rem;">
                    (신뢰도: ${(confidence * 100).toFixed(0)}%)
                </div>
            </div>
        `;
        showToast('AI 분석 완료!', 'success');
    } catch (e) {
        showToast(e.message, 'error');
        resultDiv.textContent = '분석 실패: ' + e.message;
    } finally {
        btn.disabled = false;
        btn.textContent = '💰 적정 투찰가 예측하기';
    }
}

// Toast
function showToast(msg, type) {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = msg;
    document.body.appendChild(toast);

    requestAnimationFrame(() => toast.classList.add('show'));
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}
