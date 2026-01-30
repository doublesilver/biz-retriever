document.addEventListener('DOMContentLoaded', () => {
    const profileForm = document.getElementById('profileForm');
    const dropZone = document.getElementById('dropZone');
    const certFile = document.getElementById('certFile');
    const uploadStatus = document.getElementById('uploadStatus');
    const statusText = document.getElementById('statusText');

    // 1. 프로필 정보 로드
    async function loadProfile() {
        try {
            const profile = await API.getProfile();
            if (profile) {
                document.getElementById('companyName').value = profile.company_name || '';
                document.getElementById('brn').value = profile.brn || '';

                // Subscription Plan
                const plan = profile.plan_name || 'free';
                document.getElementById('currentPlanBadge').textContent = plan.toUpperCase();
                document.getElementById('currentPlanBadge').className = `badge ${plan === 'pro' ? 'success' : plan === 'basic' ? 'warning' : ''}`;
                document.getElementById('planSelect').value = plan;

                document.getElementById('representative').value = profile.representative || '';
                document.getElementById('address').value = profile.address || '';
                document.getElementById('locationCode').value = profile.location_code || '';
                document.getElementById('companyType').value = profile.company_type || '';

                // Phase 6.1 Fields
                document.getElementById('creditRating').value = profile.credit_rating || '';
                document.getElementById('employeeCount').value = profile.employee_count || '';
                document.getElementById('foundingYear').value = profile.founding_year || '';
                document.getElementById('mainBank').value = profile.main_bank || '';

                // Array to comma-separated string
                const codes = profile.standard_industry_codes || [];
                document.getElementById('industryCodes').value = Array.isArray(codes) ? codes.join(', ') : '';

                // Phase 8: Notification Settings
                document.getElementById('slackWebhookUrl').value = profile.slack_webhook_url || '';
                document.getElementById('slackNotificationsEnabled').checked = profile.is_slack_enabled || false;
                document.getElementById('enableEmail').checked = profile.is_email_enabled || false;
            }
        } catch (error) {
            console.error('Failed to load profile:', error);
            showToast('프로필을 불러오지 못했습니다.', 'error');
        }
    }

    // 2. 사업자등록증 파일 업로드 및 추출
    async function handleFileUpload(file) {
        if (!file) return;

        uploadStatus.style.display = 'block';
        statusText.innerText = 'Gemini AI가 사업자 정보를 읽고 있습니다...';

        try {
            const result = await API.uploadCertificate(file);
            showToast('사업자 정보 추출 성공!', 'success');

            // 추출된 데이터 폼에 채우기
            const data = result.data;
            document.getElementById('companyName').value = data.company_name || '';
            document.getElementById('brn').value = data.brn || '';
            document.getElementById('representative').value = data.representative || '';
            document.getElementById('address').value = data.address || '';
            document.getElementById('locationCode').value = data.location_code || '';
            document.getElementById('companyType').value = data.company_type || '';

        } catch (error) {
            showToast('AI 분석 실패: ' + error.message, 'error');
        } finally {
            uploadStatus.style.display = 'none';
        }
    }

    // 2.5 Plan Update - Redirect to payment page
    document.getElementById('updatePlanBtn').addEventListener('click', () => {
        const plan = document.getElementById('planSelect').value;
        const currentPlan = document.getElementById('currentPlanBadge').textContent.toLowerCase();

        // If downgrading to free or staying on current plan
        if (plan === 'free') {
            if (confirm('무료 플랜으로 변경하시겠습니까?\n현재 구독이 취소되고 제한된 기능만 사용할 수 있습니다.')) {
                // TODO: Implement downgrade logic (cancel subscription)
                showToast('관리자에게 문의하여 다운그레이드를 요청하세요', 'info');
            }
            return;
        }

        if (plan === currentPlan) {
            showToast('이미 사용 중인 플랜입니다', 'info');
            return;
        }

        // Redirect to payment page with pre-selected plan
        window.location.href = `payment.html?plan=${plan}`;
    });

    // 3. 프로필 저장
    profileForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const profileData = {
            company_name: document.getElementById('companyName').value,
            brn: document.getElementById('brn').value,
            representative: document.getElementById('representative').value,
            address: document.getElementById('address').value,
            location_code: document.getElementById('locationCode').value,
            company_type: document.getElementById('companyType').value,

            // Phase 6.1
            credit_rating: document.getElementById('creditRating').value,
            employee_count: parseInt(document.getElementById('employeeCount').value) || null,
            founding_year: parseInt(document.getElementById('foundingYear').value) || null,
            main_bank: document.getElementById('mainBank').value,
            standard_industry_codes: document.getElementById('industryCodes').value
                ? document.getElementById('industryCodes').value.split(',').map(s => s.trim())
                : [],

            // Phase 8
            slack_webhook_url: document.getElementById('slackWebhookUrl').value,
            is_slack_enabled: document.getElementById('slackNotificationsEnabled').checked,
            is_email_enabled: document.getElementById('enableEmail').checked
        };

        try {
            await API.updateProfile(profileData);
            showToast('프로필이 저장되었습니다.', 'success');
        } catch (error) {
            showToast('저장 실패: ' + error.message, 'error');
        }
    });

    // 드래그 앤 드롭 이벤트
    dropZone.addEventListener('click', () => certFile.click());
    certFile.addEventListener('change', (e) => handleFileUpload(e.target.files[0]));

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = 'var(--primary-color)';
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.style.borderColor = 'var(--border-color)';
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = 'var(--border-color)';
        handleFileUpload(e.dataTransfer.files[0]);
    });

    loadProfile();
    loadLicenses();
    loadPerformances();

    // License Management
    document.getElementById('addLicenseBtn').addEventListener('click', () => {
        document.getElementById('licenseModal').classList.add('active');
        document.getElementById('licenseForm').reset();
    });

    document.getElementById('saveLicenseBtn').addEventListener('click', async () => {
        const licenseName = document.getElementById('licenseName').value.trim();
        if (!licenseName) {
            showToast('면허명을 입력하세요', 'error');
            return;
        }

        const licenseData = {
            license_name: licenseName,
            license_number: document.getElementById('licenseNumber').value.trim() || null,
            issue_date: document.getElementById('licenseIssueDate').value || null
        };

        try {
            await API.addLicense(licenseData);
            showToast('면허가 추가되었습니다', 'success');
            closeLicenseModal();
            loadLicenses();
        } catch (error) {
            showToast('면허 추가 실패: ' + error.message, 'error');
        }
    });

    // Performance Management
    document.getElementById('addPerformanceBtn').addEventListener('click', () => {
        document.getElementById('performanceModal').classList.add('active');
        document.getElementById('performanceForm').reset();
    });

    document.getElementById('savePerformanceBtn').addEventListener('click', async () => {
        const projectName = document.getElementById('projectName').value.trim();
        const projectAmount = document.getElementById('projectAmount').value;

        if (!projectName || !projectAmount) {
            showToast('프로젝트명과 계약금액을 입력하세요', 'error');
            return;
        }

        const performanceData = {
            project_name: projectName,
            amount: parseFloat(projectAmount),
            completion_date: document.getElementById('completionDate').value || null
        };

        try {
            await API.addPerformance(performanceData);
            showToast('실적이 추가되었습니다', 'success');
            closePerformanceModal();
            loadPerformances();
        } catch (error) {
            showToast('실적 추가 실패: ' + error.message, 'error');
        }
    });
});

// Load Licenses
async function loadLicenses() {
    try {
        const licenses = await API.getLicenses();
        const licenseList = document.getElementById('licenseList');

        if (licenses && licenses.length > 0) {
            licenseList.innerHTML = licenses.map(license => `
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.75rem; background: var(--bg-secondary); border-radius: var(--radius-md);">
                    <div>
                        <div style="font-weight: 500;">${license.license_name}</div>
                        <div style="font-size: 0.85rem; color: var(--text-muted);">
                            ${license.license_number ? `면허번호: ${license.license_number}` : ''}
                            ${license.issue_date ? ` | 취득: ${new Date(license.issue_date).toLocaleDateString('ko-KR')}` : ''}
                        </div>
                    </div>
                    <button class="btn-icon" onclick="deleteLicense(${license.id})" style="color: var(--danger);">🗑️</button>
                </div>
            `).join('');
        } else {
            licenseList.innerHTML = '<p style="color: var(--text-muted); font-size: 0.9rem;">등록된 면허가 없습니다.</p>';
        }
    } catch (error) {
        console.error('Failed to load licenses:', error);
    }
}

// Load Performances
async function loadPerformances() {
    try {
        const performances = await API.getPerformances();
        const performanceList = document.getElementById('performanceList');

        if (performances && performances.length > 0) {
            performanceList.innerHTML = performances.map(perf => `
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.75rem; background: var(--bg-secondary); border-radius: var(--radius-md);">
                    <div>
                        <div style="font-weight: 500;">${perf.project_name}</div>
                        <div style="font-size: 0.85rem; color: var(--text-muted);">
                            계약금액: ${new Intl.NumberFormat('ko-KR').format(perf.amount)}원
                            ${perf.completion_date ? ` | 준공: ${new Date(perf.completion_date).toLocaleDateString('ko-KR')}` : ''}
                        </div>
                    </div>
                    <button class="btn-icon" onclick="deletePerformance(${perf.id})" style="color: var(--danger);">🗑️</button>
                </div>
            `).join('');
        } else {
            performanceList.innerHTML = '<p style="color: var(--text-muted); font-size: 0.9rem;">등록된 실적이 없습니다.</p>';
        }
    } catch (error) {
        console.error('Failed to load performances:', error);
    }
}

// Delete License
async function deleteLicense(licenseId) {
    if (!confirm('이 면허를 삭제하시겠습니까?')) return;

    try {
        await API.deleteLicense(licenseId);
        showToast('면허가 삭제되었습니다', 'success');
        loadLicenses();
    } catch (error) {
        showToast('면허 삭제 실패: ' + error.message, 'error');
    }
}

// Delete Performance
async function deletePerformance(performanceId) {
    if (!confirm('이 실적을 삭제하시겠습니까?')) return;

    try {
        await API.deletePerformance(performanceId);
        showToast('실적이 삭제되었습니다', 'success');
        loadPerformances();
    } catch (error) {
        showToast('실적 삭제 실패: ' + error.message, 'error');
    }
}

// Modal Controls
function closeLicenseModal() {
    document.getElementById('licenseModal').classList.remove('active');
}

function closePerformanceModal() {
    document.getElementById('performanceModal').classList.remove('active');
}

// Export for inline onclick handlers
window.deleteLicense = deleteLicense;
window.deletePerformance = deletePerformance;
window.closeLicenseModal = closeLicenseModal;
window.closePerformanceModal = closePerformanceModal;
