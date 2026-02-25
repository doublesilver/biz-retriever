// Utility Functions

// Toast Notification - 접근성: role="alert" + aria-live
function showToast(message, type = 'success') {
    var toast = document.getElementById('toast');
    if (!toast) return;

    // 접근성: 스크린 리더가 알림을 읽도록 role, aria-live 설정
    toast.setAttribute('role', type === 'error' ? 'alert' : 'status');
    toast.setAttribute('aria-live', type === 'error' ? 'assertive' : 'polite');

    // Handle multi-line messages (preserve line breaks)
    if (message.includes('\n')) {
        toast.innerHTML = message.split('\n').map(function(line) {
            return line ? '<div>' + escapeHtml(line) + '</div>' : '<br>';
        }).join('');
    } else {
        toast.textContent = message;
    }

    toast.className = 'toast ' + type + ' show';

    // Longer duration for error messages (5 seconds vs 3 seconds)
    var duration = type === 'error' ? 5000 : 3000;

    setTimeout(function() {
        toast.classList.remove('show');
    }, duration);
}

// Password Toggle
function initPasswordToggle() {
    const toggleButtons = document.querySelectorAll('.toggle-password');

    toggleButtons.forEach(button => {
        button.addEventListener('click', function () {
            const input = this.parentElement.querySelector('input');
            const type = input.getAttribute('type') === 'password' ? 'text' : 'password';
            input.setAttribute('type', type);
            this.textContent = type === 'password' ? '👁️' : '🙈';
        });
    });
}

// Modal Control - 접근성 포커스 트랩 포함
var _previousFocusElement = null;

function showModal(modalId) {
    var modal = document.getElementById(modalId);
    _previousFocusElement = document.activeElement;
    modal.classList.add('active');
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
    document.body.classList.add('modal-open');

    // 포커스를 모달 내부 첫 번째 포커스 가능 요소로 이동
    var focusable = modal.querySelectorAll('button, [href], input:not([type="hidden"]), select, textarea, [tabindex]:not([tabindex="-1"])');
    if (focusable.length > 0) {
        setTimeout(function() { focusable[0].focus(); }, 50);
    }

    // Escape 키로 모달 닫기
    modal._escHandler = function(e) {
        if (e.key === 'Escape') {
            hideModal(modalId);
        }
    };
    document.addEventListener('keydown', modal._escHandler);

    // 포커스 트랩
    modal._trapHandler = function(e) {
        if (e.key !== 'Tab') return;
        var currentFocusable = modal.querySelectorAll('button, [href], input:not([type="hidden"]), select, textarea, [tabindex]:not([tabindex="-1"])');
        if (currentFocusable.length === 0) return;
        var first = currentFocusable[0];
        var last = currentFocusable[currentFocusable.length - 1];
        if (e.shiftKey && document.activeElement === first) {
            e.preventDefault();
            last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
            e.preventDefault();
            first.focus();
        }
    };
    modal.addEventListener('keydown', modal._trapHandler);
}

function hideModal(modalId) {
    var modal = document.getElementById(modalId);
    modal.classList.remove('active');
    modal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
    document.body.classList.remove('modal-open');

    // 이벤트 리스너 정리
    if (modal._escHandler) {
        document.removeEventListener('keydown', modal._escHandler);
        modal._escHandler = null;
    }
    if (modal._trapHandler) {
        modal.removeEventListener('keydown', modal._trapHandler);
        modal._trapHandler = null;
    }

    // 이전 포커스 복원
    if (_previousFocusElement && _previousFocusElement.focus) {
        _previousFocusElement.focus();
        _previousFocusElement = null;
    }
}

// Format Date
function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diff = Math.floor((date - now) / (1000 * 60 * 60 * 24));

    if (diff === 0) return '오늘';
    if (diff === 1) return '내일';
    if (diff < 0) return `D+${Math.abs(diff)}`;
    return `D-${diff}`;
}

// Format Currency
function formatCurrency(amount) {
    if (amount >= 100000000) {
        return `${(amount / 100000000).toFixed(1)}억원`;
    } else if (amount >= 10000) {
        return `${(amount / 10000).toFixed(0)}만원`;
    }
    return `${amount.toLocaleString()}원`;
}

// Priority Stars
function getPriorityStars(priority) {
    const stars = '⭐'.repeat(priority);
    return stars || '☆';
}

// Validate Email
function isValidEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

// Validate Password
function isValidPassword(password) {
    // At least 8 characters, contains uppercase, lowercase, number, and special char
    const re = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/;
    return re.test(password);
}

// Dark Mode - 3단계: system / light / dark
// localStorage 'theme': 'system' | 'light' | 'dark'
function initDarkMode() {
    // 레거시 마이그레이션: 기존 darkMode key -> 신규 theme key
    if (!localStorage.getItem('theme') && localStorage.getItem('darkMode') === 'true') {
        localStorage.setItem('theme', 'dark');
    }
    const saved = localStorage.getItem('theme') || 'system';
    applyTheme(saved);
    updateDarkModeToggleIcon(saved);

    // prefers-color-scheme 변경 시 system 모드면 자동 전환
    if (window.matchMedia) {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function() {
            if ((localStorage.getItem('theme') || 'system') === 'system') {
                applyTheme('system');
            }
        });
    }
}

function applyTheme(mode) {
    var html = document.documentElement;
    var body = document.body;
    body.classList.remove('dark-mode');
    html.classList.remove('light-mode');

    if (mode === 'dark') {
        body.classList.add('dark-mode');
    } else if (mode === 'light') {
        html.classList.add('light-mode');
    }
    // 'system' => prefers-color-scheme 미디어쿼리가 자동 적용
}

function toggleDarkMode() {
    // system -> dark -> light -> system 순환
    var current = localStorage.getItem('theme') || 'system';
    var next;
    if (current === 'system') next = 'dark';
    else if (current === 'dark') next = 'light';
    else next = 'system';

    localStorage.setItem('theme', next);
    applyTheme(next);
    updateDarkModeToggleIcon(next);

    // 레거시 호환
    localStorage.setItem('darkMode', next === 'dark' ? 'true' : 'false');
}

function updateDarkModeToggleIcon(mode) {
    var btn = document.getElementById('darkModeToggle');
    if (!btn) return;
    var icons = { system: '💻', dark: '🌙', light: '☀️' };
    var labels = { system: '시스템 테마 (자동)', dark: '다크모드 켜짐', light: '라이트모드 켜짐' };
    btn.textContent = icons[mode] || '💻';
    btn.setAttribute('aria-label', labels[mode] || '테마 변경');
    btn.setAttribute('aria-pressed', mode === 'dark' ? 'true' : 'false');
    btn.title = labels[mode] || '테마 변경';
}

// Loading State
function setLoading(button, isLoading) {
    if (isLoading) {
        button.disabled = true;
        button.dataset.originalText = button.textContent;
        button.innerHTML = '<span class="spinner"></span> 처리 중...';
    } else {
        button.disabled = false;
        button.textContent = button.dataset.originalText;
    }
}

// Calculate D-Day
function calculateDday(dateString) {
    if (!dateString) return '미정';
    const date = new Date(dateString);
    const now = new Date();
    const diff = Math.floor((date - now) / (1000 * 60 * 60 * 24));
    if (diff === 0) return '오늘!';
    if (diff < 0) return `D+${Math.abs(diff)}`;
    return `D-${diff}`;
}

// Debounce function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Hide Toast
function hideToast() {
    const toast = document.getElementById('toast');
    if (toast) {
        toast.classList.remove('show');
    }
}

// Escape HTML
function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Format BRN (Business Registration Number)
function formatBRN(value) {
    const cleaned = value.replace(/[^0-9]/g, '');
    
    if (cleaned.length <= 3) {
        return cleaned;
    } else if (cleaned.length <= 5) {
        return cleaned.slice(0, 3) + '-' + cleaned.slice(3);
    } else if (cleaned.length <= 10) {
        return cleaned.slice(0, 3) + '-' + cleaned.slice(3, 5) + '-' + cleaned.slice(5, 10);
    }
    return cleaned.slice(0, 3) + '-' + cleaned.slice(3, 5) + '-' + cleaned.slice(5, 10);
}

// Format Phone Number
function formatPhone(value) {
    const cleaned = value.replace(/[^0-9]/g, '');
    
    if (cleaned.length <= 3) {
        return cleaned;
    } else if (cleaned.length <= 7) {
        return cleaned.slice(0, 3) + '-' + cleaned.slice(3);
    } else if (cleaned.length <= 11) {
        return cleaned.slice(0, 3) + '-' + cleaned.slice(3, 7) + '-' + cleaned.slice(7, 11);
    }
    return cleaned.slice(0, 3) + '-' + cleaned.slice(3, 7) + '-' + cleaned.slice(7, 11);
}

// Format Number with Comma
function formatNumberWithComma(value) {
    const cleaned = value.replace(/[^0-9]/g, '');
    if (!cleaned) return '';
    return Number(cleaned).toLocaleString();
}

// Auto-format input fields
function initAutoFormat() {
    // BRN formatting
    document.querySelectorAll('input[name="brn"], #brn').forEach(input => {
        input.addEventListener('input', function(e) {
            e.target.value = formatBRN(e.target.value);
        });
    });
    
    // Phone formatting
    document.querySelectorAll('input[type="tel"], input[name="phone"]').forEach(input => {
        input.addEventListener('input', function(e) {
            e.target.value = formatPhone(e.target.value);
        });
    });
    
    // Number formatting with comma
    document.querySelectorAll('.number-format').forEach(input => {
        input.addEventListener('input', function(e) {
            const cursorPos = e.target.selectionStart;
            const oldValue = e.target.value;
            const newValue = formatNumberWithComma(e.target.value);
            e.target.value = newValue;
            
            // Restore cursor position
            const diff = newValue.length - oldValue.length;
            e.target.setSelectionRange(cursorPos + diff, cursorPos + diff);
        });
    });
}

// Unsaved changes warning
let hasUnsavedChanges = false;

function trackFormChanges(formElement) {
    const inputs = formElement.querySelectorAll('input, textarea, select');
    
    inputs.forEach(input => {
        input.addEventListener('change', () => {
            hasUnsavedChanges = true;
        });
    });
}

function clearUnsavedChanges() {
    hasUnsavedChanges = false;
}

// Setup unsaved changes warning
window.addEventListener('beforeunload', (e) => {
    if (hasUnsavedChanges) {
        e.preventDefault();
        e.returnValue = '저장하지 않은 변경사항이 있습니다. 정말 나가시겠습니까?';
    }
});

// Session expiry warning
let sessionExpiryTimer;

function startSessionTimer(expiresInSeconds) {
    // Clear existing timer
    if (sessionExpiryTimer) {
        clearTimeout(sessionExpiryTimer);
    }
    
    // Warn 5 minutes before expiry
    const warnTime = (expiresInSeconds - 5 * 60) * 1000;
    
    if (warnTime > 0) {
        sessionExpiryTimer = setTimeout(() => {
            showToast('5분 후 자동 로그아웃됩니다. 작업을 저장해주세요.', 'warning');
        }, warnTime);
    }
}

// Recent items (generic)
function addToRecentItems(key, itemId, maxItems = 10) {
    const history = JSON.parse(localStorage.getItem(key) || '[]');
    const updated = [itemId, ...history.filter(id => id !== itemId)].slice(0, maxItems);
    localStorage.setItem(key, JSON.stringify(updated));
}

function getRecentItems(key) {
    return JSON.parse(localStorage.getItem(key) || '[]');
}

// Keyboard shortcuts
function initKeyboardShortcuts(shortcuts) {
    document.addEventListener('keydown', (e) => {
        for (const [key, handler] of Object.entries(shortcuts)) {
            const parts = key.split('+');
            const keyMatch = parts[parts.length - 1].toLowerCase() === e.key.toLowerCase();
            const ctrlMatch = parts.includes('ctrl') === (e.ctrlKey || e.metaKey);
            const shiftMatch = parts.includes('shift') === e.shiftKey;
            const altMatch = parts.includes('alt') === e.altKey;
            
            if (keyMatch && ctrlMatch && shiftMatch && altMatch) {
                e.preventDefault();
                handler(e);
            }
        }
    });
}

// Auto dark mode - 이제 CSS prefers-color-scheme으로 대체됨 (레거시 호환)
function autoSwitchDarkMode() {
    // initDarkMode()에서 prefers-color-scheme 리스너로 처리됨
}

// Skeleton Screen Generator
function createSkeleton(type = 'card', count = 1) {
    const templates = {
        card: `<div class="skeleton-card-wrapper" style="padding: 1.5rem; background: var(--bg-primary); border-radius: var(--radius-lg); border: 1px solid var(--border-color); margin-bottom: 1rem;">
            <div class="skeleton skeleton-title" style="width: 60%; height: 1.25rem; margin-bottom: 1rem;"></div>
            <div class="skeleton skeleton-text" style="width: 100%; height: 0.875rem; margin-bottom: 0.5rem;"></div>
            <div class="skeleton skeleton-text" style="width: 80%; height: 0.875rem; margin-bottom: 0.5rem;"></div>
            <div class="skeleton skeleton-text" style="width: 40%; height: 0.875rem;"></div>
        </div>`,
        stat: `<div class="skeleton-stat" style="padding: 1.25rem; background: var(--bg-primary); border-radius: var(--radius-lg); border: 1px solid var(--border-color);">
            <div class="skeleton skeleton-text" style="width: 50%; height: 0.75rem; margin-bottom: 0.75rem;"></div>
            <div class="skeleton skeleton-title" style="width: 40%; height: 2rem;"></div>
        </div>`,
        table: `<div style="padding: 1rem; border-bottom: 1px solid var(--border-color);">
            <div style="display: flex; gap: 1rem; align-items: center;">
                <div class="skeleton" style="width: 60%; height: 0.875rem;"></div>
                <div class="skeleton" style="width: 20%; height: 0.875rem;"></div>
                <div class="skeleton" style="width: 15%; height: 0.875rem;"></div>
            </div>
        </div>`,
        plan: `<div style="padding: 2rem; background: var(--bg-primary); border-radius: var(--radius-lg); border: 2px solid var(--border-color);">
            <div class="skeleton" style="width: 40%; height: 1.5rem; margin-bottom: 1rem;"></div>
            <div class="skeleton" style="width: 50%; height: 2.5rem; margin-bottom: 1.5rem;"></div>
            <div class="skeleton skeleton-text" style="width: 80%; margin-bottom: 0.5rem;"></div>
            <div class="skeleton skeleton-text" style="width: 70%; margin-bottom: 0.5rem;"></div>
            <div class="skeleton skeleton-text" style="width: 60%;"></div>
        </div>`
    };

    return Array(count).fill(templates[type] || templates.card).join('');
}

// Enhanced Toast with action button and auto-dismiss progress
function showActionToast(message, type = 'info', options = {}) {
    const existing = document.getElementById('action-toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.id = 'action-toast';
    toast.className = `toast ${type} show`;
    toast.style.cssText = 'position: fixed; bottom: 2rem; right: 2rem; z-index: 9999; max-width: 400px; padding: 1rem 1.25rem; display: flex; flex-direction: column; gap: 0.5rem;';

    const textEl = document.createElement('div');
    textEl.textContent = message;
    toast.appendChild(textEl);

    if (options.actionText && options.onAction) {
        const actionBtn = document.createElement('button');
        actionBtn.textContent = options.actionText;
        actionBtn.style.cssText = 'align-self: flex-end; background: none; border: 1px solid currentColor; padding: 0.25rem 0.75rem; border-radius: var(--radius-sm); cursor: pointer; color: inherit; font-size: 0.85rem;';
        actionBtn.addEventListener('click', () => {
            options.onAction();
            toast.remove();
        });
        toast.appendChild(actionBtn);
    }

    document.body.appendChild(toast);

    const duration = options.duration || (type === 'error' ? 8000 : 4000);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// Retry wrapper for API calls with exponential backoff
async function withRetry(fn, options = {}) {
    const maxRetries = options.maxRetries || 3;
    const baseDelay = options.baseDelay || 1000;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
        try {
            return await fn();
        } catch (error) {
            if (attempt === maxRetries || !error.isRetryable) {
                throw error;
            }
            const delay = baseDelay * Math.pow(2, attempt);
            await new Promise(resolve => setTimeout(resolve, delay));
        }
    }
}

// Format subscription plan display name
function formatPlanName(planName) {
    const planMap = {
        'free': 'Free',
        'basic': 'Basic',
        'pro': 'Pro'
    };
    return planMap[planName] || planName;
}

// Format date in Korean locale
function formatDateKR(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('ko-KR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

// Format payment status
function formatPaymentStatus(status) {
    const statusMap = {
        'paid': { text: '결제완료', class: 'success' },
        'pending': { text: '대기중', class: 'warning' },
        'failed': { text: '실패', class: 'danger' },
        'refunded': { text: '환불', class: '' },
        'cancelled': { text: '취소', class: '' }
    };
    return statusMap[status] || { text: status, class: '' };
}

window.utils = {
    formatCurrency,
    formatDate,
    debounce,
    showToast,
    hideToast,
    showModal,
    hideModal,
    initPasswordToggle,
    initDarkMode,
    isValidEmail,
    isValidPassword,
    setLoading,
    escapeHtml,
    calculateDday,
    getPriorityStars,
    formatBRN,
    formatPhone,
    formatNumberWithComma,
    initAutoFormat,
    trackFormChanges,
    clearUnsavedChanges,
    startSessionTimer,
    addToRecentItems,
    getRecentItems,
    initKeyboardShortcuts,
    autoSwitchDarkMode,
    createSkeleton,
    showActionToast,
    withRetry,
    formatPlanName,
    formatDateKR,
    formatPaymentStatus
};
