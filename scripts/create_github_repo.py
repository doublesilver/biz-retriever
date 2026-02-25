"""
GitHub API를 사용하여 레포지토리 생성
"""
import requests
import json
import base64

# GitHub 인증 정보
USERNAME = "doublesilver"
PASSWORDS = ["qwer1234!!", "Qq9797822!!"]

# 레포지토리 정보
REPO_NAME = "biz-retriever"
REPO_DESCRIPTION = "🐕 AI-powered bid aggregation and analysis system"

def create_github_repo(username, password):
    """GitHub API를 사용하여 레포지토리 생성"""
    
    # API 엔드포인트
    url = "https://api.github.com/user/repos"
    
    # 레포지토리 설정
    data = {
        "name": REPO_NAME,
        "description": REPO_DESCRIPTION,
        "private": False,
        "auto_init": False,  # README 자동 생성 안 함
        "has_issues": True,
        "has_projects": True,
        "has_wiki": True
    }
    
    # Basic Auth 헤더
    auth_string = f"{username}:{password}"
    auth_bytes = auth_string.encode('ascii')
    auth_base64 = base64.b64encode(auth_bytes).decode('ascii')
    
    headers = {
        "Authorization": f"Basic {auth_base64}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }
    
    print(f"🚀 레포지토리 생성 시도: {REPO_NAME}")
    print(f"사용자: {username}")
    
    try:
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 201:
            repo_data = response.json()
            print(f"\n✅ 레포지토리 생성 성공!")
            print(f"URL: {repo_data['html_url']}")
            print(f"Clone URL: {repo_data['clone_url']}")
            return True, repo_data['clone_url']
        
        elif response.status_code == 422:
            error_data = response.json()
            if "name already exists" in error_data.get("message", "").lower():
                print(f"\n⚠️  레포지토리가 이미 존재합니다.")
                print(f"URL: https://github.com/{username}/{REPO_NAME}")
                return True, f"https://github.com/{username}/{REPO_NAME}.git"
            else:
                print(f"\n❌ 레포지토리 생성 실패: {error_data.get('message', 'Unknown error')}")
                return False, None
        
        elif response.status_code == 401:
            print(f"\n❌ 인증 실패: 잘못된 사용자 이름 또는 비밀번호")
            print(f"응답: {response.json()}")
            return False, None
        
        else:
            print(f"\n❌ 예상치 못한 오류 (HTTP {response.status_code})")
            print(f"응답: {response.text}")
            return False, None
    
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        return False, None

def main():
    """메인 함수"""
    print("=" * 60)
    print("GitHub 레포지토리 자동 생성 스크립트")
    print("=" * 60)
    print()
    
    # 비밀번호 시도
    for i, password in enumerate(PASSWORDS, 1):
        print(f"\n[시도 {i}/{len(PASSWORDS)}]")
        success, clone_url = create_github_repo(USERNAME, password)
        
        if success:
            print("\n" + "=" * 60)
            print("✅ 성공! 다음 명령어를 실행하세요:")
            print("=" * 60)
            print(f"\ngit remote add origin {clone_url}")
            print("git branch -M main")
            print("git push -u origin main")
            print()
            return True
        else:
            if i < len(PASSWORDS):
                print("다음 비밀번호로 재시도합니다...")
    
    print("\n❌ 모든 비밀번호 시도 실패")
    print("\n대안:")
    print("1. GitHub Personal Access Token 사용")
    print("   - Settings > Developer settings > Personal access tokens")
    print("   - 권한: repo (전체)")
    print("2. 수동으로 레포지토리 생성: https://github.com/new")
    return False

if __name__ == "__main__":
    main()
