// Dashboard Logic

let currentPage = 1;
let currentFilters = {};

document.addEventListener('DOMContentLoaded', async function () {
  // Check authentication
  if (!localStorage.getItem('token')) {
    window.location.href = '/index.html';
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
  const darkModeToggle = document.getElementById('darkModeToggle');
  // Update icon based on current state
  if (darkModeToggle && document.body.classList.contains('dark-mode')) {
    darkModeToggle.textContent = '☀️';
  }
  darkModeToggle.addEventListener('click', function () {
    utils.toggleDarkMode();
    this.textContent = document.body.classList.contains('dark-mode') ? '☀️' : '🌙';
  });

  // Refresh
  document.getElementById('refreshBtn').addEventListener('click', async function () {
    await loadStats();
    await loadBids();
    utils.showToast('새로고침 완료', 'success');
  });

  // Crawl Trigger
  document.getElementById('crawlBtn').addEventListener('click', async function () {
    const btn = this;
    utils.setLoading(btn, true);

    try {
      const result = await API.triggerCrawl();
      utils.showToast('크롤링이 시작되었습니다. (약 1-2분 소요)', 'success');

      // Poll for updates or just reload after some time
      setTimeout(async () => {
        await loadStats();
        await loadBids();
        utils.setLoading(btn, false);
      }, 5000);

    } catch (error) {
      utils.showToast(error.message || '크롤링 시작 실패', 'error');
      utils.setLoading(btn, false);
    }
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
      window.location.href = '/index.html';
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
    document.getElementById('statNew').textContent = stats.this_week || 0;  // 이번 주 공고
    document.getElementById('statDeadline').textContent = stats.high_importance || 0;  // 중요 공고(⭐⭐⭐)
    document.getElementById('statBudget').textContent =
      utils.formatCurrency(stats.average_price || 0);  // 평균 추정가
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

    // [FIX] Handle both Array and Object formats
    let items = [];
    let total = 0;
    let size = 10;

    if (Array.isArray(response)) {
      items = response;
      total = response.length;
    } else if (response && response.items) {
      items = response.items;
      total = response.total;
      size = response.limit || 10;
    }

    if (items && items.length > 0) {
      renderBids(items);
      renderPagination(total, size);
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
    const priorityClass = bid.importance_score >= 3 ? 'priority-high' :
      bid.importance_score >= 2 ? 'priority-medium' : 'priority-low';

    return `
      <div class="bid-card ${priorityClass}" onclick="viewBidDetail(${bid.id})">
        <div class="bid-header">
          <div class="bid-priority">${utils.getPriorityStars(bid.importance_score || 1)}</div>
          <span class="bid-status">${bid.status || '신규'}</span>
        </div>
        <h3 class="bid-title">${bid.title}</h3>
        <div class="bid-meta">
          <span class="bid-meta-item">📅 ${bid.deadline ? utils.formatDate(bid.deadline) : '미정'}</span>
          <span class="bid-meta-item">💰 ${bid.estimated_price ? utils.formatCurrency(bid.estimated_price) : '미정'}</span>
          <span class="bid-meta-item">🏢 ${bid.agency || '미정'}</span>
        </div>
        ${bid.ai_summary ? `
          <div class="bid-summary">
            🤖 ${bid.ai_summary}
          </div>
        ` : ''}
        ${bid.keywords_matched && bid.keywords_matched.length > 0 ? `
          <div class="bid-keywords">
            ${bid.keywords_matched.map(keyword => `<span class="badge">${keyword}</span>`).join('')}
          </div>
        ` : ''}
        <div class="bid-actions" style="margin-top: 10px; display: flex; justify-content: flex-end; gap: 8px;">
            <button class="btn-sm btn-outline" onclick="event.stopPropagation(); checkMatch(${bid.id})">🔍 매칭 분석</button>
            <button class="btn-sm btn-secondary" onclick="event.stopPropagation(); analyzeBid(${bid.id}, this)">💰 투찰가 예측</button>
        </div>
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

async function analyzeBid(id, btn) {
  const originalText = btn.textContent;
  btn.textContent = '⏳ 분석 중...';
  btn.disabled = true;

  try {
    const result = await API.predictPrice(id);
    const prediction = result.prediction;

    let msg = `[AI 분석 결과]\n`;
    msg += `추천 투찰가: ${utils.formatCurrency(prediction.recommended_price)}\n`;
    msg += `신뢰도: ${Math.round(prediction.confidence * 100)}%`;

    alert(msg);
  } catch (error) {
    utils.showToast('분석 실패: ' + error.message, 'error');
  } finally {
    btn.textContent = originalText;
    btn.disabled = false;
  }
}

// Check Soft Match Score
async function checkMatch(id) {
  const modal = document.getElementById('matchModal');
  const scoreEl = document.getElementById('matchScore');
  const listEl = document.getElementById('matchBreakdownList');
  const hardMatchEl = document.getElementById('hardMatchResult');

  // Reset UI
  scoreEl.textContent = '--';
  listEl.innerHTML = '<li class="loading">분석 중...</li>';
  hardMatchEl.textContent = '-';
  modal.classList.add('active');

  try {
    const response = await API.checkMatch(id);

    // 1. Soft Match Score
    const soft = response.soft_match || { score: 0, breakdown: [] };
    scoreEl.textContent = soft.score;

    // Colorize score
    const circle = modal.querySelector('.score-circle');
    circle.style.borderColor = soft.score >= 80 ? 'var(--success)' :
      soft.score >= 50 ? 'var(--warning)' : 'var(--text-disabled)';

    // 2. Breakdown
    if (soft.breakdown && soft.breakdown.length > 0) {
      listEl.innerHTML = soft.breakdown.map(item => `<li>✅ ${item}</li>`).join('');
    } else {
      listEl.innerHTML = '<li>특이사항 없음 (기본 점수)</li>';
    }

    // 3. Hard Match
    if (response.is_match) {
      hardMatchEl.innerHTML = '<span class="badge success">PASS</span> 모든 필수 조건 만족';
    } else {
      const reasons = response.reasons || [];
      hardMatchEl.innerHTML = `<span class="badge error">FAIL</span> ${reasons.join(', ')}`;
    }

  } catch (error) {
    console.error(error);
    listEl.innerHTML = `<li class="error">오류: ${error.message}</li>`;
  }
}

function closeMatchModal() {
  document.getElementById('matchModal').classList.remove('active');
}

// Close modal on outside click
document.getElementById('matchModal').addEventListener('click', function (e) {
  if (e.target === this) {
    closeMatchModal();
  }
});

// Export for inline onclick handlers
window.changePage = changePage;
window.loadBids = loadBids;
window.viewBidDetail = viewBidDetail;
window.analyzeBid = analyzeBid;
window.checkMatch = checkMatch;
window.closeMatchModal = closeMatchModal;
