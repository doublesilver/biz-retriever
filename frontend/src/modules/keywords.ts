import APIService from '../services/api';

const input = document.getElementById('keywordInput') as HTMLInputElement;
const addBtn = document.getElementById('addBtn');
const list = document.getElementById('keywordsList');
const emptyState = document.getElementById('emptyState');
const toast = document.getElementById('toast') as HTMLElement;

document.addEventListener('DOMContentLoaded', async () => {
    // Auth Check
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = 'index.html';
        return;
    }

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
        const response = await APIService.getKeywords();
        renderList(response.keywords);
    } catch (error) {
        showToast('불러오기 실패: ' + (error as Error).message, 'error');
    }
}

function renderList(keywords: string[]) {
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
            const target = e.currentTarget as HTMLElement;
            const kw = target.dataset.kw;
            if (kw) await handleDelete(kw);
        });
    });
}

async function handleAdd() {
    const kw = input.value.trim();
    if (!kw) return;

    try {
        await APIService.addKeyword(kw);
        showToast(`'${kw}' 추가됨`);
        input.value = '';
        await loadKeywords();
    } catch (error) {
        showToast('추가 실패: ' + (error as Error).message, 'error');
    }
}

async function handleDelete(kw: string) {
    if (!confirm(`'${kw}' 키워드를 정말 삭제하시겠습니까?`)) return;

    try {
        await APIService.deleteKeyword(kw);
        showToast(`'${kw}' 삭제됨`);
        await loadKeywords();
    } catch (error) {
        showToast('삭제 실패: ' + (error as Error).message, 'error');
    }
}

function escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showToast(message: string, type: 'info' | 'error' = 'info') {
    toast.textContent = message;
    toast.className = `toast show ${type}`;
    setTimeout(() => {
        toast.className = 'toast';
    }, 3000);
}

function setupDarkMode() {
    document.getElementById('darkModeToggle')?.addEventListener('click', () => {
        document.body.classList.toggle('dark-theme');
    });
}

function setupLogout() {
    document.getElementById('userMenuBtn')?.addEventListener('click', () => {
        // Toggle user menu or just logout specific logic if menu exists
        // Here we just logout for simplicity if no menu provided in HTML?
        // HTML has userMenuBtn but no dropdown code in snippet.
        // Let's just do logout for now or leave empty.
        // Reusing dashboard logout pattern might be better, but for now simple:
        localStorage.removeItem('token');
        window.location.href = 'index.html';
    });
}
