// Keywords Logic
const input = document.getElementById('keywordInput');
const addBtn = document.getElementById('addBtn');
const list = document.getElementById('keywordsList');
const emptyState = document.getElementById('emptyState');

document.addEventListener('DOMContentLoaded', async () => {
    // Auth Check
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = 'index.html';
        return;
    }

    // Initialize dark mode
    utils.initDarkMode();

    await loadKeywords();

    // Event Listeners
    addBtn?.addEventListener('click', handleAdd);
    input?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleAdd();
    });

    setupDarkMode();
    setupLogout();
});

async function loadKeywords() {
    try {
        const response = await API.getKeywords();
        renderList(response.keywords || []);
    } catch (error) {
        utils.showToast('불러오기 실패: ' + error.message, 'error');
    }
}

function renderList(keywords) {
    if (!list) return;
    list.innerHTML = '';

    if (keywords.length === 0) {
        if (emptyState) emptyState.style.display = 'block';
        return;
    }
    if (emptyState) emptyState.style.display = 'none';

    keywords.forEach(kw => {
        const chip = document.createElement('div');
        chip.className = 'keyword-chip';
        chip.innerHTML = `
            <span>${escapeHtml(kw)}</span>
            <button class="btn-delete" data-kw="${kw}" title="삭제">×</button>
        `;
        list.appendChild(chip);
    });

    // Delegate delete event
    document.querySelectorAll('.btn-delete').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const target = e.currentTarget;
            const kw = target.dataset.kw;
            if (kw) await handleDelete(kw);
        });
    });
}

async function handleAdd() {
    const kw = input.value.trim();
    if (!kw) return;

    try {
        await API.addKeyword(kw);
        utils.showToast(`'${kw}' 추가됨`);
        input.value = '';
        await loadKeywords();
    } catch (error) {
        utils.showToast('추가 실패: ' + error.message, 'error');
    }
}

async function handleDelete(kw) {
    if (!confirm(`'${kw}' 키워드를 정말 삭제하시겠습니까?`)) return;

    try {
        await API.deleteKeyword(kw);
        utils.showToast(`'${kw}' 삭제됨`);
        await loadKeywords();
    } catch (error) {
        utils.showToast('삭제 실패: ' + error.message, 'error');
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function setupDarkMode() {
    const toggle = document.getElementById('darkModeToggle');
    // Update icon based on current state
    if (toggle && document.body.classList.contains('dark-mode')) {
        toggle.textContent = '☀️';
    }
    toggle?.addEventListener('click', () => {
        utils.toggleDarkMode();
        toggle.textContent = document.body.classList.contains('dark-mode') ? '☀️' : '🌙';
    });
}

function setupLogout() {
    // User menu dropdown toggle
    const userMenuBtn = document.getElementById('userMenuBtn');
    const userDropdown = document.getElementById('userDropdown');

    userMenuBtn?.addEventListener('click', (e) => {
        e.stopPropagation();
        userDropdown?.classList.toggle('show');
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', () => {
        userDropdown?.classList.remove('show');
    });

    // Logout (POST /api/v1/auth/logout 호출 후 로컬 토큰 삭제)
    document.getElementById('logoutBtn')?.addEventListener('click', () => {
        API.logout();
    });
}
