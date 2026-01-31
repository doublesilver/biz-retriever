// Utility Functions

// Toast Notification
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    
    // Handle multi-line messages (preserve line breaks)
    if (message.includes('\n')) {
        toast.innerHTML = message.split('\n').map(line => 
            line ? `<div>${line}</div>` : '<br>'
        ).join('');
    } else {
        toast.textContent = message;
    }
    
    toast.className = `toast ${type} show`;

    // Longer duration for error messages (5 seconds vs 3 seconds)
    const duration = type === 'error' ? 5000 : 3000;
    
    setTimeout(() => {
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

// Modal Control
function showModal(modalId) {
    const modal = document.getElementById(modalId);
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function hideModal(modalId) {
    const modal = document.getElementById(modalId);
    modal.classList.remove('active');
    document.body.style.overflow = '';
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

// Dark Mode
function initDarkMode() {
    const savedMode = localStorage.getItem('darkMode');
    if (savedMode === 'true') {
        document.body.classList.add('dark-mode');
    }
}

function toggleDarkMode() {
    document.body.classList.toggle('dark-mode');
    localStorage.setItem('darkMode', document.body.classList.contains('dark-mode'));
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

// Auto dark mode based on time
function autoSwitchDarkMode() {
    const theme = localStorage.getItem('theme');
    
    if (theme === 'auto') {
        const hour = new Date().getHours();
        const shouldBeDark = hour >= 18 || hour < 6;
        document.body.classList.toggle('dark-mode', shouldBeDark);
    }
}

// Initialize auto dark mode
setInterval(autoSwitchDarkMode, 60 * 60 * 1000); // Check every hour

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
    autoSwitchDarkMode
};
