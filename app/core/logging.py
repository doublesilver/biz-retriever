"""
Structured Logging 설정
개선사항: print() → logging 모듈
"""
import logging
import sys
from pathlib import Path

# 로그 디렉토리
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

def setup_logger(name: str = "biz_retriever") -> logging.Logger:
    """
    구조화된 로거 설정
    
    Args:
        name: 로거 이름
    
    Returns:
        설정된 Logger 인스턴스
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # 이미 핸들러가 있으면 추가하지 않음 (중복 방지)
    if logger.handlers:
        return logger
    
    # 포맷 설정
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 파일 핸들러
    file_handler = logging.FileHandler(LOG_DIR / "biz_retriever.log", encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # 에러 전용 파일 핸들러
    error_handler = logging.FileHandler(LOG_DIR / "errors.log", encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)
    
    return logger

# 싱글톤 로거
logger = setup_logger()
