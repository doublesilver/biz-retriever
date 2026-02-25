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

  // Load data (parallel where possible)
  loadSubscriptionBanner();
  await Promise.all([loadStats(), loadBids()]);
});

function initEventListeners() {
  // Dark mode toggle (uses UX Engineer's 3-state toggle)
  const darkModeToggle = document.getElementById('darkModeToggle');
  if (darkModeToggle) {
    darkModeToggle.addEventListener('click', function () {
      if (typeof toggleDarkMode === 'function') {
        toggleDarkMode();
      } else if (utils.toggleDarkMode) {
        utils.toggleDarkMode();
      }
    });
  }

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

  // Logout (POST /api/v1/auth/logout 호출 후 로컬 토큰 삭제)
  document.getElementById('logoutBtn').addEventListener('click', function () {
    API.logout();
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
      currentFilters.keyword = e.target.value;
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

  // Matched Toggle
  document.getElementById('toggleMatchedView').addEventListener('click', async function () {
    this.classList.toggle('active');
    // Toggle visual state
    const isActive = this.classList.contains('active');
    this.style.background = isActive ? 'var(--primary-color)' : 'transparent';
    this.style.color = isActive ? 'white' : 'var(--text-color)';

    // Reset Page
    currentPage = 1;
    await loadBids();
  });

  // AI Smart Search
  document.getElementById('aiSearchBtn').addEventListener('click', async function () {
    const input = document.getElementById('aiSearchInput');
    const query = input.value.trim();
    if (!query) return;

    const btn = this;
    utils.setLoading(btn, true);

    try {
      const response = await API.smartSearch(query);
      const results = response.results || [];

      if (results.length > 0) {
        // UI 반영
        document.getElementById('aiSearchResults').style.display = 'block';
        document.getElementById('aiSearchStatus').textContent = `🤖 AI가 '${query}'와 가장 일치하는 공고 ${results.length}개를 찾았습니다.`;

        // 기존 목록 섹션을 숨기거나 업데이트 (여기서는 그냥 renderBids 호출)
        const bidsList = document.getElementById('bidsList');
        // AI 결과용 렌더링 (relevance_score 포함)
        renderBids(results, true);
        document.getElementById('pagination').style.display = 'none'; // AI 검색은 페이징 미지원( MVP)
      } else {
        utils.showToast('일치하는 공고가 없습니다.', 'warning');
      }
    } catch (error) {
      utils.showToast('AI 검색 실패: ' + error.message, 'error');
    } finally {
      utils.setLoading(btn, false);
    }
  });
}

function clearAiSearch() {
  document.getElementById('aiSearchInput').value = '';
  document.getElementById('aiSearchResults').style.display = 'none';
  document.getElementById('pagination').style.display = 'flex';
  loadBids();
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
  bidsList.innerHTML = utils.createSkeleton('card', 3);

  try {
    const params = {
      page: currentPage,
      size: 10,
      ...currentFilters
    };

    // Check Matched View Toggle
    const isMatchedView = document.getElementById('toggleMatchedView').classList.contains('active');

    let response;
    if (isMatchedView) {
      response = await API.getMatchedBids(params);
      document.getElementById('bidsList').classList.add('matched-mode');
    } else {
      response = await API.getBids(params);
      document.getElementById('bidsList').classList.remove('matched-mode');
    }

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
    var errorMsg = utils.escapeHtml(error.message || '공고 목록을 불러오는데 실패했습니다.');
    bidsList.innerHTML =
      '<div class="empty-state" style="padding:3rem 1.5rem;text-align:center;">' +
        '<div style="width:64px;height:64px;border-radius:50%;background:var(--danger-light);display:flex;align-items:center;justify-content:center;margin:0 auto var(--spacing-4);font-size:1.5rem;">!</div>' +
        '<h3 style="font-size:var(--font-size-lg);font-weight:var(--font-weight-semibold);color:var(--text-primary);margin-bottom:var(--spacing-2);">데이터를 불러올 수 없습니다</h3>' +
        '<p style="color:var(--text-secondary);font-size:var(--font-size-sm);margin-bottom:var(--spacing-5);max-width:360px;margin-left:auto;margin-right:auto;line-height:var(--line-height-relaxed);">' + errorMsg + '</p>' +
        '<button class="btn btn-primary btn-sm" onclick="loadBids()" style="gap:var(--spacing-2);">다시 시도</button>' +
      '</div>';

    // 재시도 가능한 에러일 때 action toast
    if (error.isRetryable) {
      utils.showActionToast(
        '네트워크 오류가 발생했습니다.',
        'error',
        { actionText: '다시 시도', onAction: loadBids, duration: 10000 }
      );
    }
  }
}

function renderBids(bids, isAiSearch = false) {
  const bidsList = document.getElementById('bidsList');

  bidsList.innerHTML = bids.map(bid => {
    const priorityClass = bid.importance_score >= 3 ? 'priority-high' :
      bid.importance_score >= 2 ? 'priority-medium' : 'priority-low';

    // AI 점수 태그
    const aiTag = isAiSearch && bid.relevance_score !== undefined ?
      `<span class="badge" style="background: var(--primary-color); color: white;">🤖 매칭률 ${Math.round(bid.relevance_score * 100)}%</span>` : '';

    return `
      <div class="bid-card ${priorityClass}" onclick="viewBidDetail(${bid.id})">
        <div class="bid-header">
          <div class="bid-priority">${utils.getPriorityStars(bid.importance_score || 1)}</div>
          <div style="display: flex; gap: 5px; align-items: center;">
            ${aiTag}
            <span class="bid-status">${bid.status || '신규'}</span>
          </div>
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

async function viewBidDetail(id) {
  const modal = document.getElementById('bidDetailModal');
  const loadingEl = document.getElementById('bidDetailLoading');
  const errorEl = document.getElementById('bidDetailError');
  const errorMsgEl = document.getElementById('bidDetailErrorMsg');
  const contentEl = document.getElementById('bidDetailContent');
  
  // Store current bid ID for action buttons
  window.currentBidId = id;
  
  // Show modal with loading state
  modal.classList.add('active');
  loadingEl.style.display = 'block';
  errorEl.style.display = 'none';
  contentEl.style.display = 'none';
  
  try {
    const bid = await API.getBid(id);
    
    // Populate modal content
    document.getElementById('bidDetailTitle').textContent = bid.title;
    document.getElementById('bidDetailPriority').innerHTML = utils.getPriorityStars(bid.importance_score || 1);
    document.getElementById('bidDetailStatus').textContent = getStatusText(bid.status || 'new');
    document.getElementById('bidDetailStatus').className = `badge ${getStatusClass(bid.status || 'new')}`;
    
    // Basic info
    document.getElementById('bidDetailAgency').textContent = bid.agency || '미정';
    document.getElementById('bidDetailDeadline').textContent = bid.deadline ? utils.formatDate(bid.deadline) : '미정';
    document.getElementById('bidDetailPrice').textContent = bid.estimated_price ? utils.formatCurrency(bid.estimated_price) : '미정';
    document.getElementById('bidDetailPosted').textContent = bid.posted_at ? utils.formatDate(bid.posted_at) : '-';
    document.getElementById('bidDetailUrl').href = bid.url || '#';
    
    // AI Summary
    if (bid.ai_summary) {
      document.getElementById('bidDetailAISection').style.display = 'block';
      document.getElementById('bidDetailAISummary').textContent = bid.ai_summary;
    } else {
      document.getElementById('bidDetailAISection').style.display = 'none';
    }
    
    // Keywords
    const keywords = bid.keywords_matched || bid.ai_keywords || [];
    if (keywords && keywords.length > 0) {
      document.getElementById('bidDetailKeywordsSection').style.display = 'block';
      document.getElementById('bidDetailKeywords').innerHTML = keywords
        .map(keyword => `<span class="badge">${keyword}</span>`)
        .join('');
    } else {
      document.getElementById('bidDetailKeywordsSection').style.display = 'none';
    }
    
    // Content
    document.getElementById('bidDetailContentPreview').textContent = bid.content || '내용 없음';
    
    // Notes
    if (bid.notes) {
      document.getElementById('bidDetailNotesSection').style.display = 'block';
      document.getElementById('bidDetailNotes').textContent = bid.notes;
    } else {
      document.getElementById('bidDetailNotesSection').style.display = 'none';
    }
    
    // Show content
    loadingEl.style.display = 'none';
    contentEl.style.display = 'block';
    
  } catch (error) {
    console.error('Failed to load bid detail:', error);
    loadingEl.style.display = 'none';
    errorEl.style.display = 'block';
    errorMsgEl.textContent = error.message || '공고 정보를 불러오는데 실패했습니다.';
  }
}

function closeBidDetailModal() {
  document.getElementById('bidDetailModal').classList.remove('active');
  window.currentBidId = null;
}

function getStatusText(status) {
  const statusMap = {
    'new': '신규',
    'reviewing': '검토중',
    'bidding': '입찰중',
    'submitted': '제출완료',
    'won': '낙찰',
    'lost': '탈락',
    'completed': '완료'
  };
  return statusMap[status] || status;
}

function getStatusClass(status) {
  const classMap = {
    'new': '',
    'reviewing': 'warning',
    'bidding': 'warning',
    'submitted': 'success',
    'won': 'success',
    'lost': 'danger',
    'completed': ''
  };
  return classMap[status] || '';
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

// Load subscription banner on dashboard
async function loadSubscriptionBanner() {
  var banner = document.getElementById('subscriptionBanner');
  if (!banner) return;

  try {
    var profile = await API.getProfile();
    var plan = (profile.plan_name || 'free').toLowerCase();
    var icons = { free: '🆓', basic: '⭐', pro: '👑' };
    var names = { free: 'Free', basic: 'Basic', pro: 'Pro' };
    var bgColors = { free: 'var(--gray-100)', basic: 'var(--info-light)', pro: 'var(--warning-light)' };

    document.getElementById('subBannerIcon').textContent = icons[plan] || '🆓';
    document.getElementById('subBannerIcon').style.background = bgColors[plan] || 'var(--gray-100)';
    document.getElementById('subBannerPlan').textContent = names[plan] || plan;

    var actionEl = document.getElementById('subBannerAction');
    if (plan === 'pro') {
      actionEl.textContent = '구독 관리';
      actionEl.style.borderColor = 'var(--success)';
      actionEl.style.color = 'var(--success)';
    } else {
      actionEl.textContent = '업그레이드';
    }

    banner.style.display = 'block';
  } catch (error) {
    // 배너 로딩 실패 시 조용히 숨김 (중요하지 않은 UI)
    console.warn('Subscription banner load failed:', error);
  }
}

// Export for inline onclick handlers
window.changePage = changePage;
window.loadBids = loadBids;
window.viewBidDetail = viewBidDetail;
window.closeBidDetailModal = closeBidDetailModal;
window.analyzeBid = analyzeBid;
window.checkMatch = checkMatch;
window.closeMatchModal = closeMatchModal;
window.clearAiSearch = clearAiSearch;
