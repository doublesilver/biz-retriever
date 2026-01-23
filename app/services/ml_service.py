"""
Phase 3: ML 기반 투찰가 예측 서비스
"""
from typing import List, Dict, Optional
from datetime import datetime
from app.core.logging import logger


class BidResult:
    """낙찰 결과 데이터 (추후 DB 모델로 전환)"""
    def __init__(self, estimated_price: float, winning_price: float, competition_ratio: float):
        self.estimated_price = estimated_price
        self.winning_price = winning_price
        self.competition_ratio = competition_ratio


class MLBidPricePredictor:
    """
    투찰가 예측 서비스
    Phase 3: 간단한 통계 기반 예측 (추후 ML 모델로 고도화)
    """
    
    def __init__(self):
        self.historical_data: List[Dict] = []
        # Phase 3에서 sklearn.linear_model.LinearRegression으로 교체 예정
    
    def train(self, historical_data: List[BidResult]):
        """
        과거 낙찰 데이터로 모델 학습
        
        Args:
            historical_data: 낙찰 결과 리스트
        """
        self.historical_data = historical_data
        logger.info(f"ML 모델 학습 완료: {len(historical_data)}건의 데이터")
    
    def predict(self, estimated_price: float, expected_competition: float = 3.0) -> Dict:
        """
        투찰가 예측
        
        Args:
            estimated_price: 추정가
            expected_competition: 예상 경쟁률
        
        Returns:
            예측 결과 (추천 투찰가, 신뢰도)
        """
        if not self.historical_data:
            # 데이터 부족 시 기본 로직
            return {
                "recommended_price": estimated_price * 0.95,  # 추정가의 95%
                "confidence": 0.5,
                "range_min": estimated_price * 0.90,
                "range_max": estimated_price * 0.98,
                "message": "과거 데이터 부족 - 기본 전략 적용"
            }
        
        # 단순 평균 기반 예측 (Phase 3에서 ML 모델로 교체)
        avg_ratio = sum(d.winning_price / d.estimated_price for d in self.historical_data) / len(self.historical_data)
        predicted_price = estimated_price * avg_ratio
        
        return {
            "recommended_price": predicted_price,
            "confidence": 0.75,
            "range_min": predicted_price * 0.98,
            "range_max": predicted_price * 1.02,
            "historical_count": len(self.historical_data),
            "average_ratio": avg_ratio
        }


# 싱글톤 인스턴스
ml_predictor = MLBidPricePredictor()
