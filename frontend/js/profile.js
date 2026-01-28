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
                document.getElementById('representative').value = profile.representative || '';
                document.getElementById('address').value = profile.address || '';
                document.getElementById('locationCode').value = profile.location_code || '';
                document.getElementById('companyType').value = profile.company_type || '';
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

    // 3. 프로필 저장
    profileForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const profileData = {
            company_name: document.getElementById('companyName').value,
            brn: document.getElementById('brn').value,
            representative: document.getElementById('representative').value,
            address: document.getElementById('address').value,
            location_code: document.getElementById('locationCode').value,
            company_type: document.getElementById('companyType').value
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
});
