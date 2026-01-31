import type {
    LoginResponse,
    User,
    BidAnnouncement,
    AnalyticsSummary,
    BidFilters
} from '../types';

// Auto-detect API URL based on environment (consistent with api.js)
const API_BASE = (() => {
    // If running on Vercel or any production domain
    if (typeof window !== 'undefined' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
        return 'https://leeeunseok.tail32c3e2.ts.net/api/v1';
    }
    // Local development
    return 'http://localhost:8000/api/v1';
})();

interface RequestOptions extends RequestInit {
    skipAuth?: boolean;
}

class APIService {
    private static async request<T>(
        endpoint: string,
        options: RequestOptions = {}
    ): Promise<T> {
        const token = localStorage.getItem('token');

        const headers: Record<string, string> = {
            'Content-Type': 'application/json'
        };

        // Merge additional headers
        if (options.headers) {
            Object.entries(options.headers).forEach(([key, value]) => {
                if (typeof value === 'string') {
                    headers[key] = value;
                }
            });
        }

        if (token && !options.skipAuth) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        try {
            const response = await fetch(`${API_BASE}${endpoint}`, {
                ...options,
                headers
            });

            if (response.status === 401) {
                localStorage.removeItem('token');
                window.location.href = '/index.html';
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

    // Auth APIs
    static async register(email: string, password: string): Promise<User> {
        return this.request<User>('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ email, password }),
            skipAuth: true
        });
    }

    static async login(email: string, password: string): Promise<LoginResponse> {
        const formData = new URLSearchParams();
        formData.append('username', email);
        formData.append('password', password);
        formData.append('grant_type', 'password');

        return this.request<LoginResponse>('/auth/login/access-token', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: formData,
            skipAuth: true
        });
    }

    // Bid APIs
    static async getBids(params: BidFilters = {}): Promise<BidAnnouncement[]> {
        const queryString = new URLSearchParams(
            Object.entries(params)
                .filter(([_, value]) => value !== undefined)
                .map(([key, value]) => [key, String(value)])
        ).toString();

        return this.request<BidAnnouncement[]>(`/bids/${queryString ? '?' + queryString : ''}`);
    }

    static async getBid(id: number): Promise<BidAnnouncement> {
        return this.request<BidAnnouncement>(`/bids/${id}`);
    }

    static async createBid(data: Partial<BidAnnouncement>): Promise<BidAnnouncement> {
        return this.request<BidAnnouncement>('/bids/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    static async updateBid(id: number, data: Partial<BidAnnouncement>): Promise<BidAnnouncement> {
        return this.request<BidAnnouncement>(`/bids/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    static async patchBid(id: number, data: Partial<BidAnnouncement>): Promise<BidAnnouncement> {
        return this.request<BidAnnouncement>(`/bids/${id}`, {
            method: 'PATCH',
            body: JSON.stringify(data)
        });
    }

    // Analytics APIs
    static async getAnalytics(): Promise<AnalyticsSummary> {
        return this.request<AnalyticsSummary>('/analytics/summary');
    }

    // Keyword APIs
    static async addKeyword(keyword: string): Promise<{ message: string; id: number }> {
        return this.request<{ message: string; id: number }>('/filters/keywords', {
            method: 'POST',
            body: JSON.stringify({ keyword })
        });
    }

    static async getKeywords(activeOnly: boolean = true): Promise<{ keywords: string[] }> {
        return this.request<{ keywords: string[] }>(`/filters/keywords?active_only=${activeOnly}`);
    }

    static async deleteKeyword(keyword: string): Promise<{ message: string }> {
        return this.request<{ message: string }>(`/filters/keywords/${encodeURIComponent(keyword)}`, {
            method: 'DELETE'
        });
    }

    // Export API
    static async exportExcel(params: BidFilters = {}): Promise<void> {
        const token = localStorage.getItem('token');
        const queryString = new URLSearchParams(
            Object.entries(params)
                .filter(([_, value]) => value !== undefined)
                .map(([key, value]) => [key, String(value)])
        ).toString();

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
        a.download = `bids_${new Date().toISOString().split('T')[0]}.xlsx`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    }
    // Crawler API
    static async triggerCrawl(): Promise<{ message: string; task_id: string }> {
        return this.request<{ message: string; task_id: string }>('/crawler/trigger', {
            method: 'POST'
        });
    }
}

export default APIService;
