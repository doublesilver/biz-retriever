import APIService from '../services/api';
import type { BidAnnouncement } from '../types';
import { showToast, formatCurrency, formatDate } from '../utils/toast';

class DashboardModule {
    private bidsContainer: HTMLElement | null;
    private searchInput: HTMLInputElement | null;
    private filters: {
        status?: string;
        minImportance?: number;
    } = {};

    constructor() {
        this.bidsContainer = document.getElementById('bids-list');
        this.searchInput = document.getElementById('search-input') as HTMLInputElement;

        this.init();
    }

    private async init(): Promise<void> {
        // Check authentication
        const token = localStorage.getItem('token');
        if (!token) {
            window.location.href = '/index.html';
            return;
        }

        await this.loadBids();
        await this.loadAnalytics();
        this.setupEventListeners();
    }

    private async loadBids(): Promise<void> {
        try {
            const bids = await APIService.getBids(this.filters);
            this.renderBids(bids);
        } catch (error) {
            showToast((error as Error).message, 'error');
        }
    }

    private async loadAnalytics(): Promise<void> {
        try {
            const analytics = await APIService.getAnalytics();
            this.renderAnalytics(analytics);
        } catch (error) {
            console.error('Analytics load failed:', error);
        }
    }

    private renderBids(bids: BidAnnouncement[]): void {
        if (!this.bidsContainer) return;

        if (bids.length === 0) {
            this.bidsContainer.innerHTML = `
        <div class="empty-state">
          <p>📭 공고가 없습니다.</p>
          <p>크롤링을 실행하여 공고를 수집하세요.</p>
        </div>
      `;
            return;
        }

        this.bidsContainer.innerHTML = bids.map(bid => `
      <div class="bid-card" data-id="${bid.id}">
        <div class="bid-header">
          <h3>${this.escapeHtml(bid.title)}</h3>
          <span class="priority-badge priority-${bid.importance_score}">
            ${'⭐'.repeat(bid.importance_score)}
          </span>
        </div>
        <div class="bid-body">
          <p class="agency">🏛️ ${this.escapeHtml(bid.agency || '')}</p>
          <p class="price">💰 ${formatCurrency(bid.estimated_price || 0)}</p>
          <p class="deadline">📅 ${formatDate(bid.deadline || '')}</p>
        </div>
        <div class="bid-footer">
          <span class="status status-${bid.status}">${this.getStatusText(bid.status)}</span>
          ${bid.keywords_matched ? `
            <div class="keywords">
              ${bid.keywords_matched.map(kw => `<span class="keyword">${this.escapeHtml(kw)}</span>`).join('')}
            </div>
          ` : ''}
        </div>
      </div>
    `).join('');
    }

    private renderAnalytics(analytics: any): void {
        const totalBidsEl = document.getElementById('total-bids');
        const highPriorityEl = document.getElementById('high-priority-count');
        const avgPriceEl = document.getElementById('avg-price');

        if (totalBidsEl) totalBidsEl.textContent = String(analytics.total_bids || 0);
        if (highPriorityEl) highPriorityEl.textContent = String(analytics.high_priority_count || 0);
        if (avgPriceEl) avgPriceEl.textContent = formatCurrency(analytics.avg_base_price || 0);
    }

    private setupEventListeners(): void {
        // Logout
        document.getElementById('logout-btn')?.addEventListener('click', () => {
            localStorage.removeItem('token');
            window.location.href = '/index.html';
        });

        // Manual crawl
        document.getElementById('manual-crawl-btn')?.addEventListener('click', async () => {
            const btn = document.getElementById('manual-crawl-btn') as HTMLButtonElement;
            try {
                btn.disabled = true;
                btn.textContent = '수집 중...';

                const response = await APIService.triggerCrawl();
                showToast(`크롤링 시작: ${response.message}`, 'success');

                // Refresh bids after short delay
                setTimeout(() => this.loadBids(), 3000);
            } catch (error) {
                showToast((error as Error).message, 'error');
            } finally {
                setTimeout(() => {
                    btn.disabled = false;
                    btn.textContent = '지금 수집하기';
                }, 3000);
            }
        });

        // Excel export
        document.getElementById('export-excel-btn')?.addEventListener('click', async () => {
            try {
                await APIService.exportExcel(this.filters);
                showToast('Excel 파일이 다운로드되었습니다.', 'success');
            } catch (error) {
                showToast((error as Error).message, 'error');
            }
        });

        // Search
        this.searchInput?.addEventListener('input', (e) => {
            const target = e.target as HTMLInputElement;
            this.filterBids(target.value);
        });

        // Filter buttons
        document.querySelectorAll('[data-filter]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const target = e.currentTarget as HTMLElement;
                const filter = target.dataset.filter;

                if (filter === 'all') {
                    this.filters = {};
                } else if (filter === 'high-priority') {
                    this.filters.minImportance = 2;
                }

                this.loadBids();
            });
        });
    }

    private filterBids(searchTerm: string): void {
        const cards = this.bidsContainer?.querySelectorAll('.bid-card');

        cards?.forEach(card => {
            const element = card as HTMLElement;
            const text = element.textContent?.toLowerCase() || '';
            const matches = text.includes(searchTerm.toLowerCase());
            element.style.display = matches ? 'block' : 'none';
        });
    }

    private escapeHtml(text: string): string {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    private getStatusText(status: string): string {
        const statusMap: Record<string, string> = {
            'new': '신규',
            'reviewing': '검토중',
            'bidding': '투찰예정',
            'completed': '완료'
        };
        return statusMap[status] || status;
    }
}

// Auto-initialize
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => new DashboardModule());
} else {
    new DashboardModule();
}
