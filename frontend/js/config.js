// Environment Configuration
// Railway 이전 시 API_URL만 변경하면 됨
// Vercel 환경변수 사용 시: Settings > Environment Variables > VITE_API_URL 설정

window.__CONFIG__ = {
    // Production API URL (Tailscale -> Railway 이전 예정)
    API_URL: 'https://leeeunseok.tail32c3e2.ts.net/api/v1',

    // Local development fallback
    LOCAL_API_URL: 'http://localhost:8000/api/v1',

    // Token 설정
    ACCESS_TOKEN_KEY: 'token',
    REFRESH_TOKEN_KEY: 'refresh_token',
};
