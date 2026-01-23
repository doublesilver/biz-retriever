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
    agency: string;
    base_price: number;
    deadline: string;
    priority_score: number;
    status: 'new' | 'reviewing' | 'bidding' | 'completed';
    ai_summary?: string;
    ai_keywords?: string[];
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
    min_priority?: number;
}
