// Kanban Board Logic

document.addEventListener('DOMContentLoaded', async () => {
    // Check Auth
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = 'index.html';
        return;
    }

    // Initialize
    await loadUsers();
    await loadKanbanBoard();
    setupDragAndDrop();
    setupModal();
    setupRefresh();
    setupLogout();
});

// State
let allUsers = [];
let currentEditingBidId = null;

const columns = {
    'new': document.getElementById('col-new'),
    'reviewing': document.getElementById('col-reviewing'),
    'bidding': document.getElementById('col-bidding'),
    'submitted': document.getElementById('col-submitted')
};

// Pipeline indicator counts
const counts = {
    'new': document.getElementById('count-new'),
    'reviewing': document.getElementById('count-reviewing'),
    'bidding': document.getElementById('count-bidding'),
    'submitted': document.getElementById('count-submitted')
};

// Column header counts
const countDisplays = {
    'new': document.getElementById('count-new-display'),
    'reviewing': document.getElementById('count-reviewing-display'),
    'bidding': document.getElementById('count-bidding-display'),
    'submitted': document.getElementById('count-submitted-display')
};

// Modal Elements
const modalOverlay = document.getElementById('modalOverlay');
const modalTitle = document.getElementById('modalTitle');
const modalAgency = document.getElementById('modalAgency');
const modalPrice = document.getElementById('modalPrice');
const aiRecommendedPrice = document.getElementById('aiRecommendedPrice');
const aiConfidence = document.getElementById('aiConfidence');
const aiReason = document.getElementById('aiReason');
const modalStatus = document.getElementById('modalStatus');
const modalAssignee = document.getElementById('modalAssignee');
const modalNotes = document.getElementById('modalNotes');
const saveModalBtn = document.getElementById('saveModal');
const closeModalBtn = document.getElementById('closeModal');
const cancelModalBtn = document.getElementById('cancelModal');

async function loadUsers() {
    try {
        allUsers = await API.request('/auth/users');
        modalAssignee.innerHTML = '<option value="">미지정</option>';
        allUsers.forEach(user => {
            const option = document.createElement('option');
            option.value = user.id;
            option.textContent = user.email.split('@')[0]; // Simple display name
            modalAssignee.appendChild(option);
        });
    } catch (error) {
        console.error('Failed to load users:', error);
    }
}

async function loadKanbanBoard() {
    try {
        const data = await API.getBids({ limit: 200 });
        const bids = data.items;

        Object.values(columns).forEach(col => col.innerHTML = '');

        bids.forEach(bid => {
            const card = createCard(bid);
            const status = bid.status || 'new';
            if (columns[status]) {
                columns[status].appendChild(card);
            }
        });

        updateCounts();
    } catch (error) {
        console.error('Failed to load kanban:', error);
        utils.showToast('데이터를 불러오는데 실패했습니다.', 'error');
    }
}

function createCard(bid) {
    const div = document.createElement('div');
    div.className = 'kanban-card';
    div.dataset.id = bid.id;

    // Save full data for modal
    div.dataset.bid = JSON.stringify(bid);

    const dDay = utils.calculateDday(bid.deadline);
    const dDayClass = dDay.includes('오늘') || dDay.includes('!') ? 'badge-dday' : '';

    const stars = '⭐'.repeat(Math.min(bid.importance_score, 3));

    // Assignee initials
    let assigneeLabel = '';
    if (bid.assignee) {
        const name = bid.assignee.email.substring(0, 1).toUpperCase();
        assigneeLabel = `<span style="background: var(--primary-color); color: white; border-radius: 50%; width: 20px; height: 20px; display: inline-flex; align-items: center; justify-content: center; font-size: 0.7rem; margin-left: 0.5rem;" title="${bid.assignee.email}">${name}</span>`;
    }

    div.innerHTML = `
        <div class="card-title" title="${bid.title}">${bid.title}</div>
        <div class="card-meta">
            <span>${bid.agency || '발주처 미상'}</span>
            ${assigneeLabel}
        </div>
        <div class="card-meta">
            <span class="card-badge ${dDayClass}">${dDay}</span>
            <span>${stars}</span>
        </div>
    `;

    // Click to open modal
    div.addEventListener('click', () => openModal(bid));

    return div;
}

function updateCounts() {
    Object.keys(columns).forEach(status => {
        const count = columns[status].children.length;
        // Update pipeline indicator
        if (counts[status]) {
            counts[status].textContent = count;
        }
        // Update column header
        if (countDisplays[status]) {
            countDisplays[status].textContent = count;
        }
    });
}

function setupModal() {
    const close = () => {
        modalOverlay.style.display = 'none';
        currentEditingBidId = null;
    };

    closeModalBtn.addEventListener('click', close);
    cancelModalBtn.addEventListener('click', close);
    modalOverlay.addEventListener('click', (e) => {
        if (e.target === modalOverlay) close();
    });

    saveModalBtn.addEventListener('click', async () => {
        if (!currentEditingBidId) return;

        const data = {
            status: modalStatus.value,
            assigned_to: modalAssignee.value ? parseInt(modalAssignee.value) : null,
            notes: modalNotes.value
        };

        try {
            await API.patchBid(currentEditingBidId, data);
            utils.showToast('변경사항이 저장되었습니다.', 'success');
            close();
            loadKanbanBoard(); // Refresh
        } catch (error) {
            console.error('Update failed:', error);
            utils.showToast('저장에 실패했습니다.', 'error');
        }
    });
}

async function openModal(bid) {
    currentEditingBidId = bid.id;

    // Fill basic info
    modalTitle.textContent = bid.title;
    modalAgency.textContent = bid.agency || '발주처 미상';
    modalPrice.textContent = bid.estimated_price ? `${bid.estimated_price.toLocaleString()}원` : '미상';

    modalStatus.value = bid.status || 'new';
    modalAssignee.value = bid.assigned_to || '';
    modalNotes.value = bid.notes || '';

    // Show modal
    modalOverlay.style.display = 'flex';

    // AI Prediction
    aiRecommendedPrice.textContent = '분석 중...';
    aiConfidence.textContent = '-';
    aiReason.textContent = '';

    try {
        const pred = await API.predictPrice(bid.id);
        aiRecommendedPrice.textContent = `${pred.recommended_price.toLocaleString()}원`;
        aiConfidence.textContent = `${Math.round(pred.confidence * 100)}%`;
        aiReason.textContent = pred.prediction_reason || '';
    } catch (error) {
        console.error('AI Prediction failed:', error);
        aiRecommendedPrice.textContent = '예측 불가';
    }
}

function setupDragAndDrop() {
    Object.values(columns).forEach(col => {
        new Sortable(col, {
            group: 'kanban',
            animation: 150,
            ghostClass: 'sortable-ghost',
            dragClass: 'sortable-drag',
            onEnd: async function (evt) {
                const itemEl = evt.item;
                const newStatus = evt.to.dataset.status;
                const oldStatus = evt.from.dataset.status;
                const bidId = itemEl.dataset.id;

                if (newStatus === oldStatus) return;

                updateCounts();

                try {
                    await API.patchBid(bidId, { status: newStatus });
                    utils.showToast('상태가 변경되었습니다.', 'success');
                } catch (error) {
                    console.error('Update failed:', error);
                    utils.showToast('상태 변경 실패. 되돌립니다.', 'error');
                    if (oldStatus && columns[oldStatus]) {
                        columns[oldStatus].appendChild(itemEl);
                        updateCounts();
                    }
                }
            }
        });
    });
}

function setupRefresh() {
    const btn = document.getElementById('refreshBtn');
    if (btn) {
        btn.addEventListener('click', () => {
            btn.classList.add('spinning');
            loadKanbanBoard().finally(() => {
                setTimeout(() => btn.classList.remove('spinning'), 500);
            });
        });
    }
}

function setupLogout() {
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            API.logout();
        });
    }

    const userMenuBtn = document.getElementById('userMenuBtn');
    const userDropdown = document.getElementById('userDropdown');

    if (userMenuBtn && userDropdown) {
        userMenuBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            userDropdown.classList.toggle('show');
        });

        document.addEventListener('click', () => {
            userDropdown.classList.remove('show');
        });
    }
}
