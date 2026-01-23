import APIService from '../services/api';
import { BidAnnouncement } from '../types';

// State
let allBids: BidAnnouncement[] = [];

// DOM Elements
const columns = document.querySelectorAll('.kanban-column');
const toast = document.getElementById('toast') as HTMLElement;

// Initialization
document.addEventListener('DOMContentLoaded', async () => {
    // Auth Check
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = 'index.html';
        return;
    }

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
        allBids = await APIService.getBids();
        renderBoard();
    } catch (error) {
        showToast('공고 불러오기 실패: ' + (error as Error).message, 'error');
    }
}

function renderBoard() {
    // Clear Columns
    document.querySelectorAll('.column-body').forEach(el => el.innerHTML = '');
    document.querySelectorAll('.count').forEach(el => el.textContent = '0');

    // Group by Status
    const grouped: Record<string, BidAnnouncement[]> = {
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

function createCard(bid: BidAnnouncement): HTMLElement {
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
        (window as any).draggedCardId = bid.id;
    });

    card.addEventListener('dragend', () => {
        card.classList.remove('dragging');
        (window as any).draggedCardId = null;
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
            (body as HTMLElement).classList.add('drag-over');
        });

        body.addEventListener('dragleave', () => {
            (body as HTMLElement).classList.remove('drag-over');
        });

        body.addEventListener('drop', async (e) => {
            e.preventDefault();
            (body as HTMLElement).classList.remove('drag-over');

            const bidId = (window as any).draggedCardId; // Use global ref since dataTransfer might be tricky in some contexts, but dataTransfer is standard.
            // Using dataTransfer generally better.
            const transferId = (e as any).dataTransfer?.getData('text/plain');
            const finalId = bidId || transferId;

            if (!finalId) return;

            const newStatus = (column as HTMLElement).dataset.status;
            if (newStatus) {
                await updateStatus(parseInt(finalId), newStatus as BidAnnouncement['status']);
            }
        });
    });
}

async function updateStatus(id: number, newStatus: BidAnnouncement['status']) {
    // Optimistic Update can be complex, let's just wait for API
    try {
        await APIService.patchBid(id, { status: newStatus });

        // Update Local State
        const bid = allBids.find(b => b.id === id);
        if (bid) {
            bid.status = newStatus;
        }

        // Re-render
        renderBoard();
        showToast('상태가 변경되었습니다.');
    } catch (error) {
        showToast('상태 변경 실패: ' + (error as Error).message, 'error');
        // Reload to ensure sync
        await loadBids();
    }
}

// Utils
function showToast(message: string, type: 'info' | 'error' = 'info') {
    toast.textContent = message;
    toast.className = `toast show ${type}`;
    setTimeout(() => {
        toast.className = 'toast';
    }, 3000);
}

// Basic Handlers
function setupRefresh() {
    document.getElementById('refreshBtn')?.addEventListener('click', loadBids);
}

function setupLogout() {
    document.getElementById('logoutBtn')?.addEventListener('click', () => {
        localStorage.removeItem('token');
        window.location.href = 'index.html';
    });

    document.getElementById('userMenuBtn')?.addEventListener('click', () => {
        const menu = document.getElementById('userDropdown');
        menu?.classList.toggle('show');
    });
}

function setupDarkMode() {
    const toggle = document.getElementById('darkModeToggle');
    toggle?.addEventListener('click', () => {
        document.body.classList.toggle('dark-theme');
    });
}
