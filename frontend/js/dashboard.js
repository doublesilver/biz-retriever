// Dashboard Logic

let currentPage = 1;
let currentFilters = {};

document.addEventListener('DOMContentLoaded', async function () {
    // Check authentication
    if (!localStorage.getItem('token')) {
        window.location.href = '/frontend/index.html';
        return;
    }

    // Initialize
    utils.initDarkMode();
    initEventListeners();

    // Load data
    await loadStats();
    await loadBids();
});

function initEventListeners() {
    // Dark mode toggle
    document.getElementById('darkModeToggle').addEventListener('click', function () {
        utils.toggleDarkMode();
        this.textContent = document.body.classList.contains('dark-mode') ? '☀️' : '🌙';
    });

    // Refresh
    document.getElementById('refreshBtn').addEventListener('click', async function () {
        await loadStats();
        await loadBids();
        utils.showToast('새로고침 완료', 'success');
    });

    // User menu
    const userMenuBtn = document.getElementById('userMenuBtn');
    const userDropdown = document.getElementById('userDropdown');

    userMenuBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        userDropdown.classList.toggle('show');
    });

    document.addEventListener('click', function () {
        userDropdown.classList.remove('show');
    });

    // Logout
    document.getElementById('logoutBtn').addEventListener('click', function () {
        localStorage.removeItem('token');
        utils.showToast('로그아웃되었습니다', 'success');
        setTimeout(() => {
            window.location.href = '/frontend/index.html';
        }, 500);
    });

    // Export Excel
    document.getElementById('exportExcelBtn').addEventListener('click', async function () {
        try {
            await API.exportExcel(currentFilters);
            utils.showToast('Excel 다운로드 완료!', 'success');
        } catch (error) {
            utils.showToast('Excel 내보내기 실패', 'error');
        }
    });

    // Search
    let searchTimeout;
    document.getElementById('searchInput').addEventListener('input', function (e) {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(async () => {
            currentFilters.search = e.target.value;
            currentPage = 1;
            await loadBids();
        }, 500);
    });

    // Sort
    document.getElementById('sortSelect').addEventListener('change', async function (e) {
        currentFilters.sort_by = e.target.value;
        currentPage = 1;
        await loadBids();
    });

    // Priority filter
    document.getElementById('priorityFilter').addEventListener('change', async function (e) {
        if (e.target.value) {
            currentFilters.min_priority = e.target.value;
        } else {
            delete currentFilters.min_priority;
        }
        currentPage = 1;
        await loadBids();
    });
}

async function loadStats() {
    try {
        const stats = await API.getAnalytics();

        document.getElementById('statTotal').textContent = stats.total_bids || 0;
        document.getElementById('statNew').textContent = stats.new_bids || 0;
        document.getElementById('statDeadline').textContent = stats.urgent_bids || 0;
        document.getElementById('statBudget').textContent =
            utils.formatCurrency(stats.total_budget || 0);
    } catch (error) {
        console.error('Failed to load stats:', error);
        // Set defaults
        document.getElementById('statTotal').textContent = '0';
        document.getElementById('statNew').textContent = '0';
        document.getElementById('statDeadline').textContent = '0';
        document.getElementById('statBudget').textContent = '0원';
    }
}

async function loadBids() {
    const bidsList = document.getElementById('bidsList');
    bidsList.innerHTML = '<div class="loading-container"><div class="spinner-lg"></div><p>공고를 불러오는 중...</p></div>';

    try {
        const params = {
            page: currentPage,
            size: 10,
            ...currentFilters
        };

        const response = await API.getBids(params);

        if (response.items && response.items.length > 0) {
            renderBids(response.items);
            renderPagination(response.total, response.size);
        } else {
            bidsList.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">🔍</div>
          <h3>공고가 없습니다</h3>
          <p>아직 수집된 공고가 없거나 필터 조건에 맞는 공고가 없습니다.</p>
        </div>
      `;
        }
    } catch (error) {
        console.error('Failed to load bids:', error);
        bidsList.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">⚠️</div>
        <h3>오류가 발생했습니다</h3>
        <p>${error.message}</p>
        <button class="btn btn-primary" onclick="loadBids()">다시 시도</button>
      </div>
    `;
    }
}

function renderBids(bids) {
    const bidsList = document.getElementById('bidsList');

    bidsList.innerHTML = bids.map(bid => {
        const priorityClass = bid.priority_score >= 3 ? 'priority-high' :
            bid.priority_score >= 2 ? 'priority-medium' : 'priority-low';

        return `
      <div class="bid-card ${priorityClass}" onclick="viewBidDetail(${bid.id})">
        <div class="bid-header">
          <div class="bid-priority">${utils.getPriorityStars(bid.priority_score)}</div>
          <span class="bid-status">${bid.status || '신규'}</span>
        </div>
        <h3 class="bid-title">${bid.title}</h3>
        <div class="bid-meta">
          <span class="bid-meta-item">📅 ${bid.deadline ? utils.formatDate(bid.deadline) : '미정'}</span>
          <span class="bid-meta-item">💰 ${bid.base_price ? utils.formatCurrency(bid.base_price) : '미정'}</span>
          <span class="bid-meta-item">🏢 ${bid.agency || '미정'}</span>
        </div>
        ${bid.ai_summary ? `
          <div class="bid-summary">
            🤖 ${bid.ai_summary}
          </div>
        ` : ''}
        ${bid.ai_keywords && bid.ai_keywords.length > 0 ? `
          <div class="bid-keywords">
            ${bid.ai_keywords.map(keyword => `<span class="badge">${keyword}</span>`).join('')}
          </div>
        ` : ''}
      </div>
    `;
    }).join('');
}

function renderPagination(total, size) {
    const totalPages = Math.ceil(total / size);
    const pagination = document.getElementById('pagination');

    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }

    let html = `
    <button onclick="changePage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}>
      ◀
    </button>
  `;

    const maxButtons = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxButtons / 2));
    let endPage = Math.min(totalPages, startPage + maxButtons - 1);

    if (endPage - startPage < maxButtons - 1) {
        startPage = Math.max(1, endPage - maxButtons + 1);
    }

    for (let i = startPage; i <= endPage; i++) {
        html += `
      <button 
        onclick="changePage(${i})" 
        class="${i === currentPage ? 'active' : ''}"
      >
        ${i}
      </button>
    `;
    }

    html += `
    <button onclick="changePage(${currentPage + 1})" ${currentPage === totalPages ? 'disabled' : ''}>
      ▶
    </button>
  `;

    pagination.innerHTML = html;
}

async function changePage(page) {
    currentPage = page;
    await loadBids();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function viewBidDetail(id) {
    utils.showToast('공고 상세 페이지는 준비 중입니다', 'warning');
    // TODO: Implement bid detail page
    // window.location.href = `/frontend/bid-detail.html?id=${id}`;
}

// Export for inline onclick handlers
window.changePage = changePage;
window.loadBids = loadBids;
window.viewBidDetail = viewBidDetail;
