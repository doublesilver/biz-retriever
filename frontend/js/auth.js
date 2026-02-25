// Authentication Logic

document.addEventListener('DOMContentLoaded', function () {
    // Check if already logged in
    if (localStorage.getItem('token')) {
        window.location.href = '/dashboard.html';
        return;
    }

    // Initialize
    utils.initPasswordToggle();
    utils.initDarkMode();

    // Login Form
    const loginForm = document.getElementById('loginForm');
    loginForm.addEventListener('submit', async function (e) {
        e.preventDefault();

        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;

        if (!utils.isValidEmail(email)) {
            utils.showToast('유효한 이메일을 입력해주세요.', 'error');
            return;
        }

        const submitBtn = loginForm.querySelector('button[type="submit"]');
        utils.setLoading(submitBtn, true);

        try {
            await API.login(email, password);
            utils.showToast('로그인 성공!', 'success');

            setTimeout(() => {
                window.location.href = '/dashboard.html';
            }, 500);
        } catch (error) {
            // 계정 잠금 에러 UI 처리
            if (error.isAccountLocked) {
                showAccountLockedMessage(error.lockRemainingMinutes);
            } else {
                utils.showToast(error.message || '로그인 실패', 'error');
            }
            utils.setLoading(submitBtn, false);
        }
    });

    // Show Register Modal
    const showRegisterBtn = document.getElementById('showRegisterBtn');
    const registerModal = document.getElementById('registerModal');

    showRegisterBtn.addEventListener('click', function () {
        utils.showModal('registerModal');
    });

    // Close Modal
    const closeModalBtn = registerModal.querySelector('.modal-close');
    const backdrop = registerModal.querySelector('.modal-backdrop');

    closeModalBtn.addEventListener('click', function () {
        utils.hideModal('registerModal');
    });

    backdrop.addEventListener('click', function () {
        utils.hideModal('registerModal');
    });

    // Email Duplicate Check
    const registerEmail = document.getElementById('registerEmail');
    let emailCheckTimeout;
    
    registerEmail.addEventListener('blur', async function() {
        const email = this.value.trim();
        if (!email || !utils.isValidEmail(email)) return;
        
        clearTimeout(emailCheckTimeout);
        emailCheckTimeout = setTimeout(async () => {
            try {
                const result = await API.checkEmailExists(email);
                const hint = this.parentElement.querySelector('.email-hint') || 
                            document.createElement('small');
                hint.className = 'hint email-hint';
                
                if (result.exists) {
                    hint.textContent = '✗ ' + result.message;
                    hint.style.color = '#ef4444';
                    this.classList.add('error');
                    this.classList.remove('valid');
                } else {
                    hint.textContent = '✓ ' + result.message;
                    hint.style.color = '#10b981';
                    this.classList.add('valid');
                    this.classList.remove('error');
                }
                
                if (!this.parentElement.querySelector('.email-hint')) {
                    this.parentElement.appendChild(hint);
                }
            } catch (error) {
                console.error('Email check failed:', error);
            }
        }, 500);
    });

    // Caps Lock Detection for all password inputs
    document.querySelectorAll('input[type="password"]').forEach(input => {
        let capsLockWarning = input.parentElement.querySelector('.caps-lock-warning');
        
        if (!capsLockWarning) {
            capsLockWarning = document.createElement('small');
            capsLockWarning.className = 'hint caps-lock-warning';
            capsLockWarning.style.display = 'none';
            capsLockWarning.style.color = '#f59e0b';
            input.parentElement.appendChild(capsLockWarning);
        }
        
        input.addEventListener('keyup', function(e) {
            const capsLockOn = e.getModifierState && e.getModifierState('CapsLock');
            
            if (capsLockOn) {
                capsLockWarning.style.display = 'block';
                capsLockWarning.textContent = '⚠️ Caps Lock이 켜져 있습니다';
            } else {
                capsLockWarning.style.display = 'none';
            }
        });
    });

    // Password Strength Indicator
    const registerPassword = document.getElementById('registerPassword');
    const passwordStrength = document.getElementById('passwordStrength');
    const strengthFill = passwordStrength.querySelector('.strength-fill');
    const strengthText = passwordStrength.querySelector('.strength-text');
    
    registerPassword.addEventListener('input', function() {
        const password = this.value;
        
        if (password.length === 0) {
            passwordStrength.style.display = 'none';
            return;
        }
        
        passwordStrength.style.display = 'block';
        
        // Calculate password strength
        let strength = 0;
        let strengthLabel = '';
        let strengthColor = '';
        
        // Length check
        if (password.length >= 8) strength += 25;
        if (password.length >= 12) strength += 15;
        
        // Lowercase check
        if (/[a-z]/.test(password)) strength += 15;
        
        // Uppercase check
        if (/[A-Z]/.test(password)) strength += 15;
        
        // Number check
        if (/[0-9]/.test(password)) strength += 15;
        
        // Special character check
        if (/[^a-zA-Z0-9]/.test(password)) strength += 15;
        
        // Determine strength level
        if (strength < 40) {
            strengthLabel = '약함';
            strengthColor = '#ef4444'; // red
        } else if (strength < 70) {
            strengthLabel = '보통';
            strengthColor = '#f59e0b'; // orange
        } else {
            strengthLabel = '강함';
            strengthColor = '#10b981'; // green
        }
        
        strengthFill.style.width = strength + '%';
        strengthFill.style.backgroundColor = strengthColor;
        strengthText.textContent = strengthLabel;
        strengthText.style.color = strengthColor;
    });
    
    // Password Confirmation Validation
    const registerPasswordConfirm = document.getElementById('registerPasswordConfirm');
    const passwordMatchHint = document.getElementById('passwordMatchHint');
    
    function checkPasswordMatch() {
        const password = registerPassword.value;
        const confirmPassword = registerPasswordConfirm.value;
        
        if (confirmPassword.length === 0) {
            passwordMatchHint.style.display = 'none';
            return true;
        }
        
        passwordMatchHint.style.display = 'block';
        
        if (password === confirmPassword) {
            passwordMatchHint.textContent = '✓ 비밀번호가 일치합니다';
            passwordMatchHint.style.color = '#10b981';
            return true;
        } else {
            passwordMatchHint.textContent = '✗ 비밀번호가 일치하지 않습니다';
            passwordMatchHint.style.color = '#ef4444';
            return false;
        }
    }
    
    registerPassword.addEventListener('input', checkPasswordMatch);
    registerPasswordConfirm.addEventListener('input', checkPasswordMatch);

    // Register Form
    const registerForm = document.getElementById('registerForm');
    registerForm.addEventListener('submit', async function (e) {
        e.preventDefault();

        const email = document.getElementById('registerEmail').value;
        const password = registerPassword.value;
        const passwordConfirm = registerPasswordConfirm.value;

        if (!utils.isValidEmail(email)) {
            utils.showToast('유효한 이메일을 입력해주세요.', 'error');
            return;
        }

        if (!utils.isValidPassword(password)) {
            utils.showToast('비밀번호는 영문 대/소문자, 숫자, 특수문자를 포함한 8자 이상이어야 합니다.', 'error');
            return;
        }

        if (password !== passwordConfirm) {
            utils.showToast('비밀번호가 일치하지 않습니다. 다시 확인해주세요.', 'error');
            return;
        }

        const submitBtn = registerForm.querySelector('button[type="submit"]');
        utils.setLoading(submitBtn, true);

        try {
            await API.register(email, password);
            utils.showToast('회원가입 완료! 로그인해주세요.', 'success');
            utils.hideModal('registerModal');
            registerForm.reset();
            passwordStrength.style.display = 'none';
            passwordMatchHint.style.display = 'none';

            // Auto fill login form
            document.getElementById('email').value = email;
            document.getElementById('password').focus();
        } catch (error) {
            utils.showToast(error.message || '회원가입 실패', 'error');
        } finally {
            utils.setLoading(submitBtn, false);
        }
    });
});

/**
 * 계정 잠금 메시지 UI 표시
 * 남은 잠금 시간을 실시간 카운트다운으로 보여줌
 */
function showAccountLockedMessage(remainingMinutes) {
    // 기존 잠금 메시지가 있으면 제거
    const existing = document.getElementById('accountLockedBanner');
    if (existing) existing.remove();

    const banner = document.createElement('div');
    banner.id = 'accountLockedBanner';
    banner.style.cssText = `
        margin-bottom: var(--spacing-4);
        padding: var(--spacing-4) var(--spacing-5);
        background: var(--danger-light);
        border: 1px solid var(--danger);
        border-radius: var(--radius-md);
        color: var(--danger);
        font-size: var(--font-size-sm);
        line-height: var(--line-height-relaxed);
    `;

    const title = document.createElement('div');
    title.style.cssText = 'font-weight: 600; margin-bottom: var(--spacing-2);';
    title.textContent = '계정이 일시적으로 잠겼습니다';

    const desc = document.createElement('div');
    desc.textContent = '로그인 시도가 너무 많아 보안을 위해 계정이 잠겼습니다.';
    desc.style.marginBottom = 'var(--spacing-2)';

    const timer = document.createElement('div');
    timer.style.cssText = 'font-weight: 600; font-size: var(--font-size-base);';

    banner.appendChild(title);
    banner.appendChild(desc);
    banner.appendChild(timer);

    // 로그인 폼 위에 삽입
    const loginForm = document.getElementById('loginForm');
    loginForm.parentElement.insertBefore(banner, loginForm);

    // 실시간 카운트다운
    let totalSeconds = remainingMinutes * 60;

    function updateTimer() {
        if (totalSeconds <= 0) {
            banner.remove();
            return;
        }
        const mins = Math.floor(totalSeconds / 60);
        const secs = totalSeconds % 60;
        timer.textContent = `${mins}분 ${String(secs).padStart(2, '0')}초 후 다시 시도할 수 있습니다`;
        totalSeconds--;
        setTimeout(updateTimer, 1000);
    }

    updateTimer();
}
