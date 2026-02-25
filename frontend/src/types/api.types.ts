// API Response Types
export interface LoginResponse {
    access_token: string;
    token_type: string;
}

export interface User {
    id: number;
    email: string;
    created_at: string;
}

export interface BidAnnouncement {
    id: number;
    title: string;
    content: string;
    agency: string;
    url: string;
    source: string;
    estimated_price?: number;
    deadline?: string;
    importance_score: number;
    status: 'new' | 'reviewing' | 'bidding' | 'completed';
    keywords_matched?: string[];
    assigned_to?: number;
    notes?: string;
    created_at: string;
    updated_at: string;
}

export interface AnalyticsSummary {
    total_bids: number;
    high_priority_count: number;
    avg_base_price: number;
    recent_bids: BidAnnouncement[];
}

export interface ApiError {
    detail: string;
}

// Request Types
export interface RegisterRequest {
    email: string;
    password: string;
}

export interface BidFilters {
    skip?: number;
    limit?: number;
    status?: string;
    min_importance?: number;
}
