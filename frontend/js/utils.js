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

// Export utilities
window.utils = {
    showToast,
    initPasswordToggle,
    showModal,
    hideModal,
    formatDate,
    formatCurrency,
    getPriorityStars,
    isValidEmail,
    isValidPassword,
    initDarkMode,
    toggleDarkMode,
    setLoading
};
