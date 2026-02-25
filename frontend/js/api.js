// API Service

// 환경별 API URL 결정 (config.js에서 주입된 __CONFIG__ 사용)
const API_BASE = (() => {
    const config = window.__CONFIG__ || {};
    // localhost/127.0.0.1이면 로컬 개발 환경
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        return config.LOCAL_API_URL || 'http://localhost:8000/api/v1';
    }
    // Production: config.js에서 설정된 URL 사용
    return config.API_URL || 'http://localhost:8000/api/v1';
})();

class APIService {
    // Token refresh 진행 중 플래그 (중복 refresh 방지)
    static _refreshing = null;

    static async request(endpoint, options = {}) {
        const token = localStorage.getItem('token');

        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        if (token && !options.skipAuth) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        // Remove Content-Type if explicitly set to null/undefined (for FormData)
        if (headers['Content-Type'] === undefined || headers['Content-Type'] === null) {
            delete headers['Content-Type'];
        }

        try {
            const response = await fetch(`${API_BASE}${endpoint}`, {
                ...options,
                headers
            });

            // 401 응답 시 Token Refresh 시도
            if (response.status === 401 && !options.skipAuth && !options._isRetry) {
                const refreshed = await this._tryRefreshToken();
                if (refreshed) {
                    // 새 토큰으로 원래 요청 재시도
                    return this.request(endpoint, { ...options, _isRetry: true });
                }
                // Refresh 실패 시 로그아웃
                localStorage.removeItem('token');
                localStorage.removeItem('refresh_token');
                window.location.href = '/index.html';
                throw new Error('인증이 만료되었습니다. 다시 로그인해주세요.');
            }

            if (!response.ok) {
                const contentType = response.headers.get("content-type");
                if (contentType && contentType.indexOf("application/json") !== -1) {
                    const errorData = await response.json();

                    // Parse user-friendly error message from new format
                    let errorMessage = '요청 처리 중 오류가 발생했습니다.';

                    if (errorData.message) {
                        errorMessage = errorData.message;
                    } else if (errorData.detail) {
                        errorMessage = errorData.detail;
                    }

                    // Add details if validation error
                    if (errorData.details && Array.isArray(errorData.details)) {
                        errorMessage += '\n\n세부 사항:\n' + errorData.details.join('\n');
                    }

                    // 계정 잠금 에러: 남은 시간 파싱하여 구조화된 에러 생성
                    if (response.status === 400 && errorData.detail &&
                        errorData.detail.includes('Account locked')) {
                        const error = new Error(errorMessage);
                        error.isAccountLocked = true;
                        // "Try again in X minutes." 패턴에서 분 추출
                        const minutesMatch = errorData.detail.match(/(\d+)\s*minutes?/);
                        error.lockRemainingMinutes = minutesMatch ? parseInt(minutesMatch[1]) : 30;
                        throw error;
                    }

                    // 상태 코드별 사용자 친화적 에러 메시지 및 재시도 가능 여부 표시
                    const error = new Error(errorMessage);
                    error.statusCode = response.status;
                    error.isRetryable = [408, 429, 500, 502, 503, 504].includes(response.status);

                    if (response.status === 429) {
                        error.message = '요청이 너무 많습니다. 잠시 후 다시 시도해주세요.';
                        error.retryAfter = parseInt(response.headers.get('Retry-After') || '30');
                    } else if (response.status === 503) {
                        error.message = '서비스가 일시적으로 이용 불가합니다. 잠시 후 다시 시도해주세요.';
                    } else if (response.status === 502 || response.status === 504) {
                        error.message = '서버 연결에 실패했습니다. 잠시 후 다시 시도해주세요.';
                    } else if (response.status === 403) {
                        error.message = '접근 권한이 없습니다. 플랜을 업그레이드해주세요.';
                    } else if (response.status === 404) {
                        error.message = errorMessage || '요청하신 리소스를 찾을 수 없습니다.';
                    }

                    throw error;
                } else {
                    const text = await response.text();
                    console.error('Non-JSON Error Response:', text);
                    const error = new Error(`서버 오류가 발생했습니다. (Status: ${response.status})`);
                    error.statusCode = response.status;
                    error.isRetryable = response.status >= 500;
                    throw error;
                }
            }

            const body = await response.json();

            // ADR-001: 표준 응답 envelope 자동 unwrap
            // 새 엔드포인트: {success: true, data: {...}, timestamp: ...}
            // 레거시 엔드포인트: raw object/array
            if (body && typeof body === 'object' && 'success' in body && 'data' in body) {
                if (!body.success) {
                    const error = new Error(body.error?.message || '요청 처리 중 오류가 발생했습니다.');
                    error.errorCode = body.error?.code;
                    error.statusCode = response.status;
                    throw error;
                }
                return body.data;
            }

            return body;
        } catch (error) {
            // Network errors (TypeError: Failed to fetch)
            if (error instanceof TypeError && error.message.includes('fetch')) {
                const netError = new Error('네트워크에 연결할 수 없습니다. 인터넷 연결을 확인해주세요.');
                netError.isRetryable = true;
                netError.statusCode = 0;
                throw netError;
            }
            console.error('API Error:', error);
            throw error;
        }
    }

    /**
     * Refresh Token으로 새 Access Token 발급 시도
     * 동시 다중 요청 시 중복 refresh 방지 (Promise 공유)
     */
    static async _tryRefreshToken() {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) return false;

        // 이미 refresh 중이면 같은 Promise 재사용
        if (this._refreshing) return this._refreshing;

        this._refreshing = (async () => {
            try {
                const response = await fetch(`${API_BASE}/auth/refresh`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ refresh_token: refreshToken })
                });

                if (!response.ok) return false;

                const data = await response.json();
                localStorage.setItem('token', data.access_token);
                localStorage.setItem('refresh_token', data.refresh_token);
                return true;
            } catch {
                return false;
            } finally {
                this._refreshing = null;
            }
        })();

        return this._refreshing;
    }

    // Crawler
    static async triggerCrawl() {
        return this.request('/crawler/trigger', {
            method: 'POST'
        });
    }

    // Analysis
    static async predictPrice(id) {
        return this.request(`/analysis/predict-price/${id}`);
    }

    static async checkMatch(id) {
        return this.request(`/analysis/match/${id}`);
    }

    static async smartSearch(query, limit = 10) {
        return this.request('/analysis/smart-search', {
            method: 'POST',
            body: JSON.stringify({ query, limit })
        });
    }

    // Auth
    static async checkEmailExists(email) {
        return this.request(`/auth/check-email?email=${encodeURIComponent(email)}`, {
            skipAuth: true
        });
    }

    static async register(email, password) {
        return this.request('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ email, password }),
            skipAuth: true
        });
    }

    static async login(email, password) {
        const formData = new URLSearchParams();
        formData.append('username', email);
        formData.append('password', password);
        formData.append('grant_type', 'password');  // OAuth2 spec requirement

        const response = await this.request('/auth/login/access-token', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: formData,
            skipAuth: true
        });

        // Access Token + Refresh Token 모두 저장
        if (response.access_token) {
            localStorage.setItem('token', response.access_token);
        }
        if (response.refresh_token) {
            localStorage.setItem('refresh_token', response.refresh_token);
        }

        return response;
    }

    static async logout() {
        try {
            await this.request('/auth/logout', {
                method: 'POST'
            });
        } catch (error) {
            console.error('Logout API call failed:', error);
        }
        // Clear local storage
        localStorage.removeItem('token');
        localStorage.removeItem('refresh_token');
        // Redirect to login
        window.location.href = '/index.html';
    }

    // Bids
    static async getBids(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        return this.request(`/bids/${queryString ? '?' + queryString : ''}`);
    }

    static async getMatchedBids(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        return this.request(`/bids/matched${queryString ? '?' + queryString : ''}`);
    }

    static async getBid(id) {
        return this.request(`/bids/${id}`);
    }

    static async createBid(data) {
        return this.request('/bids/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    static async updateBid(id, data) {
        return this.request(`/bids/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    static async patchBid(id, data) {
        return this.request(`/bids/${id}`, {
            method: 'PATCH',
            body: JSON.stringify(data)
        });
    }


    // Keywords (제외 키워드)
    static async getKeywords() {
        return this.request('/filters/keywords');
    }

    static async addKeyword(keyword) {
        return this.request('/filters/keywords', {
            method: 'POST',
            body: JSON.stringify({ keyword })
        });
    }

    static async deleteKeyword(keyword) {
        return this.request(`/filters/keywords/${encodeURIComponent(keyword)}`, {
            method: 'DELETE'
        });
    }

    // Subscription Status
    static async getSubscription() {
        return this.request('/payment/subscription');
    }

    // Analytics
    static async getAnalytics() {
        return this.request('/analytics/summary');
    }

    // Export
    static async exportExcel(params = {}) {
        const token = localStorage.getItem('token');
        const queryString = new URLSearchParams(params).toString();

        const response = await fetch(
            `${API_BASE}/export/excel${queryString ? '?' + queryString : ''}`,
            {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            }
        );

        if (!response.ok) {
            throw new Error('Excel 내보내기 실패');
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'bids.xlsx';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    }

    // Profile (Phase 2)
    static async getProfile() {
        return this.request('/profile/');
    }

    static async updateProfile(data) {
        return this.request('/profile/', {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    static async uploadCertificate(file) {
        const formData = new FormData();
        formData.append('file', file);

        return this.request('/profile/upload-certificate', {
            method: 'POST',
            headers: {
                // Content-Type: multipart/form-data is automatically set by fetch for FormData
                'Content-Type': null
            },
            body: formData
        });
    }

    // License Management (Phase 9)
    static async getLicenses() {
        return this.request('/profile/licenses');
    }

    static async addLicense(data) {
        return this.request('/profile/licenses', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    static async deleteLicense(licenseId) {
        return this.request(`/profile/licenses/${licenseId}`, {
            method: 'DELETE'
        });
    }

    // Performance Management (Phase 9)
    static async getPerformances() {
        return this.request('/profile/performances');
    }

    static async addPerformance(data) {
        return this.request('/profile/performances', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    static async deletePerformance(performanceId) {
        return this.request(`/profile/performances/${performanceId}`, {
            method: 'DELETE'
        });
    }

    // Payment & Subscription (Phase 10)
    static async createPayment(planName) {
        return this.request('/payment/create', {
            method: 'POST',
            body: JSON.stringify({ plan_name: planName })
        });
    }

    static async confirmPayment(paymentKey, orderId, amount) {
        return this.request('/payment/confirm', {
            method: 'POST',
            body: JSON.stringify({
                paymentKey,
                orderId,
                amount
            })
        });
    }

    static async cancelPayment(paymentKey, cancelReason) {
        return this.request('/payment/cancel', {
            method: 'POST',
            body: JSON.stringify({
                paymentKey,
                cancelReason
            })
        });
    }

    static async getPaymentHistory() {
        return this.request('/payment/history');
    }

    static async getPlans() {
        return this.request('/payment/plans');
    }

}

// Export API service
window.API = APIService;
