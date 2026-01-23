import APIService from '../services/api';
import { showToast } from '../utils/toast';

class AuthModule {
    private loginForm: HTMLFormElement | null;
    private registerForm: HTMLFormElement | null;
    private registerModal: HTMLElement | null;

    constructor() {
        this.loginForm = document.getElementById('loginForm') as HTMLFormElement;
        this.registerForm = document.getElementById('registerForm') as HTMLFormElement;
        this.registerModal = document.getElementById('registerModal');

        this.init();
    }

    private init(): void {
        // Login form
        this.loginForm?.addEventListener('submit', this.handleLogin.bind(this));

        // Register form
        this.registerForm?.addEventListener('submit', this.handleRegister.bind(this));

        // Show register modal
        const showRegisterBtn = document.getElementById('showRegisterBtn');
        showRegisterBtn?.addEventListener('click', () => {
            this.registerModal?.classList.add('active');
        });

        // Close modal
        const closeBtn = this.registerModal?.querySelector('.modal-close');
        closeBtn?.addEventListener('click', () => {
            this.closeModal();
        });

        // Close on backdrop click
        const backdrop = this.registerModal?.querySelector('.modal-backdrop');
        backdrop?.addEventListener('click', () => {
            this.closeModal();
        });

        // Password toggle
        document.querySelectorAll('.toggle-password').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const target = e.currentTarget as HTMLElement;
                const input = target.previousElementSibling as HTMLInputElement;
                if (input) {
                    input.type = input.type === 'password' ? 'text' : 'password';
                    target.textContent = input.type === 'password' ? '👁️' : '🙈';
                }
            });
        });
    }

    private async handleLogin(e: Event): Promise<void> {
        e.preventDefault();

        const emailInput = document.getElementById('email') as HTMLInputElement;
        const passwordInput = document.getElementById('password') as HTMLInputElement;
        const submitBtn = this.loginForm?.querySelector('button[type="submit"]') as HTMLButtonElement;

        if (!emailInput || !passwordInput) return;

        const email = emailInput.value.trim();
        const password = passwordInput.value;

        try {
            submitBtn.disabled = true;
            submitBtn.textContent = '로그인 중...';

            const response = await APIService.login(email, password);
            localStorage.setItem('token', response.access_token);

            showToast('로그인 성공!', 'success');

            // Redirect to dashboard
            setTimeout(() => {
                window.location.href = '/dashboard.html';
            }, 500);

        } catch (error) {
            showToast((error as Error).message, 'error');
            submitBtn.disabled = false;
            submitBtn.textContent = '로그인';
        }
    }

    private async handleRegister(e: Event): Promise<void> {
        e.preventDefault();

        const emailInput = document.getElementById('registerEmail') as HTMLInputElement;
        const passwordInput = document.getElementById('registerPassword') as HTMLInputElement;
        const submitBtn = this.registerForm?.querySelector('button[type="submit"]') as HTMLButtonElement;

        if (!emailInput || !passwordInput) return;

        const email = emailInput.value.trim();
        const password = passwordInput.value;

        try {
            submitBtn.disabled = true;
            submitBtn.textContent = '가입 중...';

            await APIService.register(email, password);

            showToast('회원가입 성공! 로그인해주세요.', 'success');

            // Close modal and reset form
            this.closeModal();
            this.registerForm?.reset();

        } catch (error) {
            showToast((error as Error).message, 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = '가입하기';
        }
    }

    private closeModal(): void {
        this.registerModal?.classList.remove('active');
    }
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => new AuthModule());
} else {
    new AuthModule();
}
