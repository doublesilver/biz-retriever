// API Service

const API_BASE = 'http://localhost:8000/api/v1';

class APIService {
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

            if (response.status === 401) {
                // Token expired
                localStorage.removeItem('token');
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
                    
                    throw new Error(errorMessage);
                } else {
                    const text = await response.text();
                    console.error('Non-JSON Error Response:', text);
                    throw new Error(`서버 오류가 발생했습니다. (Status: ${response.status})`);
                }
            }

            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
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

        return this.request('/auth/login/access-token', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: formData,
            skipAuth: true
        });
    }

    static loginSNS(provider) {
        window.location.href = `${API_BASE}/auth/login/${provider}`;
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

    // Payment (Phase 3)
    static async subscribe(planName) {
        return this.request('/payment/subscribe', {
            method: 'POST',
            body: JSON.stringify({ plan_name: planName })
        });
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
