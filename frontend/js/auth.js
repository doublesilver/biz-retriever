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
            const response = await API.login(email, password);
            localStorage.setItem('token', response.access_token);
            utils.showToast('로그인 성공!', 'success');

            setTimeout(() => {
                window.location.href = '/dashboard.html';
            }, 500);
        } catch (error) {
            utils.showToast(error.message || '로그인 실패', 'error');
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

    // Register Form
    const registerForm = document.getElementById('registerForm');
    registerForm.addEventListener('submit', async function (e) {
        e.preventDefault();

        const email = document.getElementById('registerEmail').value;
        const password = document.getElementById('registerPassword').value;

        if (!utils.isValidEmail(email)) {
            utils.showToast('유효한 이메일을 입력해주세요.', 'error');
            return;
        }

        if (!utils.isValidPassword(password)) {
            utils.showToast('비밀번호는 영문 대/소문자, 숫자, 특수문자를 포함한 8자 이상이어야 합니다.', 'error');
            return;
        }

        const submitBtn = registerForm.querySelector('button[type="submit"]');
        utils.setLoading(submitBtn, true);

        try {
            await API.register(email, password);
            utils.showToast('회원가입 완료! 로그인해주세요.', 'success');
            utils.hideModal('registerModal');
            registerForm.reset();

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
