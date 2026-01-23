"""
ML 서비스 단위 테스트
"""
import pytest
from app.services.ml_service import MLBidPricePredictor, BidResult


class TestMLBidPricePredictor:
    """ML 투찰가 예측 서비스 테스트"""

    @pytest.fixture
    def predictor(self):
        """예측기 인스턴스"""
        return MLBidPricePredictor()

    # ============================================
    # predict 테스트
    # ============================================

    def test_predict_without_historical_data(self, predictor):
        """과거 데이터 없을 때 기본 전략 적용"""
        estimated_price = 100000000  # 1억

        result = predictor.predict(estimated_price=estimated_price)

        # 기본 전략: 추정가의 95%
        assert result["recommended_price"] == estimated_price * 0.95
        assert result["confidence"] == 0.5
        assert result["range_min"] == estimated_price * 0.90
        assert result["range_max"] == estimated_price * 0.98
        assert "message" in result

    def test_predict_with_historical_data(self, predictor):
        """과거 데이터 있을 때 평균 기반 예측"""
        # 학습 데이터 준비
        historical_data = [
            BidResult(estimated_price=100000000, winning_price=95000000, competition_ratio=3.0),
            BidResult(estimated_price=120000000, winning_price=114000000, competition_ratio=4.0),
            BidResult(estimated_price=80000000, winning_price=76000000, competition_ratio=2.5),
        ]
        predictor.train(historical_data)

        # 예측 실행
        result = predictor.predict(estimated_price=110000000)

        # 과거 데이터 기반 예측
        assert "recommended_price" in result
        assert result["confidence"] == 0.75
        assert "historical_count" in result
        assert result["historical_count"] == 3
        assert "average_ratio" in result

    def test_predict_returns_required_fields(self, predictor):
        """반환 딕셔너리 필수 필드 확인"""
        result = predictor.predict(estimated_price=50000000)

        required_fields = ["recommended_price", "confidence", "range_min", "range_max"]
        for field in required_fields:
            assert field in result

    def test_predict_with_expected_competition(self, predictor):
        """경쟁률 파라미터 테스트"""
        result = predictor.predict(
            estimated_price=100000000,
            expected_competition=5.0
        )

        # 경쟁률이 높아도 기본 로직은 동일 (Phase 3에서 고도화)
        assert result["recommended_price"] == 100000000 * 0.95

    # ============================================
    # train 테스트
    # ============================================

    def test_train_stores_data(self, predictor):
        """train 메서드가 데이터를 저장하는지 확인"""
        assert len(predictor.historical_data) == 0

        historical_data = [
            BidResult(estimated_price=100000000, winning_price=95000000, competition_ratio=3.0),
        ]
        predictor.train(historical_data)

        assert len(predictor.historical_data) == 1

    def test_train_replaces_existing_data(self, predictor):
        """train이 기존 데이터를 대체하는지 확인"""
        # 첫 번째 학습
        data1 = [BidResult(100000000, 95000000, 3.0)]
        predictor.train(data1)
        assert len(predictor.historical_data) == 1

        # 두 번째 학습
        data2 = [
            BidResult(120000000, 114000000, 4.0),
            BidResult(80000000, 76000000, 2.5),
        ]
        predictor.train(data2)
        assert len(predictor.historical_data) == 2

    # ============================================
    # BidResult 테스트
    # ============================================

    def test_bid_result_creation(self):
        """BidResult 객체 생성"""
        result = BidResult(
            estimated_price=100000000,
            winning_price=95000000,
            competition_ratio=3.5
        )

        assert result.estimated_price == 100000000
        assert result.winning_price == 95000000
        assert result.competition_ratio == 3.5

    def test_winning_ratio_calculation(self, predictor):
        """낙찰률 계산 테스트"""
        historical_data = [
            BidResult(100000000, 90000000, 3.0),  # 90% 낙찰
            BidResult(100000000, 95000000, 3.0),  # 95% 낙찰
        ]
        predictor.train(historical_data)

        # 평균 낙찰률: (0.90 + 0.95) / 2 = 0.925
        result = predictor.predict(estimated_price=100000000)

        expected_ratio = (90000000 / 100000000 + 95000000 / 100000000) / 2
        assert result["average_ratio"] == pytest.approx(expected_ratio, rel=0.01)
