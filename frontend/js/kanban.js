// Kanban Logic
let allBids = [];

const columns = document.querySelectorAll('.kanban-column');
const toast = document.getElementById('toast');

document.addEventListener('DOMContentLoaded', async () => {
    // Auth Check
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = 'index.html';
        return;
    }

    // Initialize dark mode
    utils.initDarkMode();

    // Load Data
    await loadBids();

    // Event Listeners
    setupDragAndDrop();
    setupRefresh();
    setupLogout();
    setupDarkMode();
});

async function loadBids() {
    try {
        // Get up to 100 items for Kanban board
        const response = await API.getBids({ size: 100 });

        if (Array.isArray(response)) {
            allBids = response;
        } else if (response.items) {
            allBids = response.items;
        } else {
            console.warn('Unknown response format', response);
            allBids = [];
        }

        renderBoard();
    } catch (error) {
        utils.showToast('공고 불러오기 실패: ' + error.message, 'error');
    }
}

function renderBoard() {
    // Clear Columns
    document.querySelectorAll('.column-body').forEach(el => el.innerHTML = '');
    document.querySelectorAll('.count').forEach(el => el.textContent = '0');

    // Group by Status
    const grouped = {
        'new': [],
        'reviewing': [],
        'bidding': [],
        'completed': []
    };

    allBids.forEach(bid => {
        const status = bid.status || 'new'; // Default to new if null
        if (grouped[status]) {
            grouped[status].push(bid);
        } else {
            // Handle unknown status if any, treat as new or ignore
            if (!grouped['new']) grouped['new'] = [];
            grouped['new'].push(bid);
        }
    });

    // Render
    Object.keys(grouped).forEach(status => {
        const columnBody = document.getElementById(`col-${status}`);
        const countBadge = document.getElementById(`count-${status}`);

        if (columnBody && countBadge) {
            const bids = grouped[status];
            countBadge.textContent = bids.length.toString();

            bids.forEach(bid => {
                const card = createCard(bid);
                columnBody.appendChild(card);
            });
        }
    });
}

function createCard(bid) {
    const card = document.createElement('div');
    card.className = 'kanban-card';
    card.draggable = true;
    card.dataset.id = bid.id.toString();

    const price = bid.estimated_price
        ? new Intl.NumberFormat('ko-KR').format(bid.estimated_price) + '원'
        : '-';

    const deadline = bid.deadline
        ? new Date(bid.deadline).toLocaleDateString()
        : '-';

    // Tags
    let tagsHtml = '';
    if (bid.importance_score > 1) {
        tagsHtml += `<span class="tag" style="background:#ffeb3b;color:#333">⭐ ${bid.importance_score}</span>`;
    }
    if (bid.source) {
        tagsHtml += `<span class="tag">${bid.source}</span>`;
    }

    card.innerHTML = `
        <div class="card-header">
            <span class="card-id">#${bid.id}</span>
            <span class="card-date">${deadline} 마감</span>
        </div>
        <div class="card-title" title="${bid.title}">${bid.title}</div>
        <div class="card-meta">
            <span class="card-agency">${bid.agency || 'Unknown'}</span>
            <span class="card-price">${price}</span>
        </div>
        <div class="card-tags">
            ${tagsHtml}
        </div>
    `;

    // Drag Events
    card.addEventListener('dragstart', (e) => {
        e.dataTransfer?.setData('text/plain', bid.id.toString());
        card.classList.add('dragging');
        window.draggedCardId = bid.id;
    });

    card.addEventListener('dragend', () => {
        card.classList.remove('dragging');
        window.draggedCardId = null;
        document.querySelectorAll('.column-body').forEach(col => col.classList.remove('drag-over'));
    });

    return card;
}

function setupDragAndDrop() {
    columns.forEach(column => {
        const body = column.querySelector('.column-body');
        if (!body) return;

        body.addEventListener('dragover', (e) => {
            e.preventDefault(); // Necessary for drop to work
            body.classList.add('drag-over');
        });

        body.addEventListener('dragleave', () => {
            body.classList.remove('drag-over');
        });

        body.addEventListener('drop', async (e) => {
            e.preventDefault();
            body.classList.remove('drag-over');

            const bidId = window.draggedCardId;
            const transferId = e.dataTransfer?.getData('text/plain');
            const finalId = bidId || transferId;

            if (!finalId) return;

            const newStatus = column.dataset.status;
            if (newStatus) {
                await updateStatus(parseInt(finalId), newStatus);
            }
        });
    });
}

async function updateStatus(id, newStatus) {
    try {
        await API.patchBid(id, { status: newStatus });

        // Update Local State
        const bid = allBids.find(b => b.id === id);
        if (bid) {
            bid.status = newStatus;
        }

        // Re-render
        renderBoard();
        utils.showToast('상태가 변경되었습니다.');
    } catch (error) {
        utils.showToast('상태 변경 실패: ' + error.message, 'error');
        // Reload to ensure sync
        await loadBids();
    }
}

// Basic Handlers
function setupRefresh() {
    document.getElementById('refreshBtn')?.addEventListener('click', loadBids);
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

    // Logout button
    document.getElementById('logoutBtn')?.addEventListener('click', () => {
        localStorage.removeItem('token');
        utils.showToast('로그아웃되었습니다', 'success');
        setTimeout(() => {
            window.location.href = 'index.html';
        }, 500);
    });
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
