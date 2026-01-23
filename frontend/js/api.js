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

        try {
            const response = await fetch(`${API_BASE}${endpoint}`, {
                ...options,
                headers
            });

            if (response.status === 401) {
                // Token expired
                localStorage.removeItem('token');
                window.location.href = '/frontend/index.html';
                throw new Error('인증이 만료되었습니다. 다시 로그인해주세요.');
            }

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || '요청 처리 중 오류가 발생했습니다.');
            }

            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
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

    // Bids
    static async getBids(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        return this.request(`/bids/${queryString ? '?' + queryString : ''}`);
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
}

// Export API service
window.API = APIService;
