"""
강력한 SECRET_KEY 생성 스크립트
프로덕션 환경에서 사용할 보안 키 생성
"""
import secrets
import string

def generate_secret_key(length=64):
    """강력한 SECRET_KEY 생성"""
    # Hex 방식 (권장)
    hex_key = secrets.token_hex(32)  # 32바이트 = 64자
    
    # URL-safe 방식
    urlsafe_key = secrets.token_urlsafe(48)  # ~64자
    
    # Custom 방식 (대소문자+숫자+특수문자)
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}|;:,.<>?"
    custom_key = ''.join(secrets.choice(alphabet) for _ in range(length))
    
    print("=" * 70)
    print("🔐 SECRET_KEY 생성")
    print("=" * 70)
    print()
    print("다음 중 하나를 선택하여 .env 파일에 입력하세요:")
    print()
    print("📌 방법 1: Hex (권장)")
    print(f"SECRET_KEY={hex_key}")
    print()
    print("📌 방법 2: URL-safe")
    print(f"SECRET_KEY={urlsafe_key}")
    print()
    print("📌 방법 3: Custom")
    print(f"SECRET_KEY={custom_key}")
    print()
    print("=" * 70)
    print()
    print("⚠️  주의사항:")
    print("1. 생성된 키는 안전하게 보관하세요")
    print("2. Git에 커밋하지 마세요")
    print("3. 프로덕션 환경에서는 절대 변경하지 마세요")
    print("4. 키가 노출되면 즉시 재생성하세요")
    print()

if __name__ == "__main__":
    generate_secret_key()
