"""
MLService 확장 단위 테스트
- _get_deps: ImportError
- _load_model: 파일 없음/성공/실패
- predict_price: 성공/모델 미학습/자동 로드/base_price 없음
- train_model: 데이터 부족
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ml_service import MLService
from app.core.exceptions import InsufficientDataError, ModelNotTrainedError


class TestLoadModel:
    """_load_model 테스트"""

    def test_no_file(self):
        """모델 파일 없음"""
        service = MLService()
        with patch("os.path.exists", return_value=False):
            result = service._load_model()
        assert result is False

    def test_load_success(self):
        """모델 로드 성공"""
        service = MLService()
        mock_model = MagicMock()
        mock_joblib = MagicMock()
        mock_joblib.load.return_value = mock_model

        with patch("os.path.exists", return_value=True):
            with patch.object(service, "_get_deps", return_value=(mock_joblib, MagicMock(), MagicMock())):
                result = service._load_model()

        assert result is True
        assert service.model == mock_model

    def test_load_failure(self):
        """모델 로드 실패"""
        service = MLService()
        mock_joblib = MagicMock()
        mock_joblib.load.side_effect = Exception("Corrupted")

        with patch("os.path.exists", return_value=True):
            with patch.object(service, "_get_deps", return_value=(mock_joblib, MagicMock(), MagicMock())):
                result = service._load_model()

        assert result is False


class TestPredictPrice:
    """predict_price 테스트"""

    def test_no_model_no_file_raises(self):
        """모델 미학습 → ModelNotTrainedError"""
        service = MLService()
        service.model = None
        with patch.object(service, "_load_model", return_value=False):
            with pytest.raises(ModelNotTrainedError):
                service.predict_price(100000000)

    def test_predict_success(self):
        """예측 성공"""
        service = MLService()
        mock_model = MagicMock()
        mock_model.predict.return_value = [95000000.0]
        mock_model.estimators_ = [MagicMock()] * 100
        service.model = mock_model

        mock_pd = MagicMock()

        with patch.object(service, "_get_deps", return_value=(MagicMock(), mock_pd, MagicMock())):
            result = service.predict_price(100000000, base_price=98000000, category="건설")

        assert result["recommended_price"] == 95000000.0
        assert 0.0 < result["confidence"] <= 1.0

    def test_predict_no_base_price(self):
        """base_price 없이 예측 — estimated_price가 base_price로 사용됨"""
        service = MLService()
        mock_model = MagicMock()
        mock_model.predict.return_value = [80000000.0]
        mock_model.estimators_ = [MagicMock()] * 50
        service.model = mock_model

        mock_pd = MagicMock()
        with patch.object(service, "_get_deps", return_value=(MagicMock(), mock_pd, MagicMock())):
            result = service.predict_price(100000000)

        assert result["recommended_price"] == 80000000.0

    def test_predict_no_category(self):
        """category 없이 예측"""
        service = MLService()
        mock_model = MagicMock()
        mock_model.predict.return_value = [90000000.0]
        mock_model.estimators_ = [MagicMock()] * 100
        service.model = mock_model

        mock_pd = MagicMock()
        with patch.object(service, "_get_deps", return_value=(MagicMock(), mock_pd, MagicMock())):
            result = service.predict_price(100000000, base_price=95000000)

        assert result["recommended_price"] == 90000000.0

    def test_predict_auto_loads_model(self):
        """모델 미로드 → 자동 로드 후 예측"""
        service = MLService()
        service.model = None

        mock_model = MagicMock()
        mock_model.predict.return_value = [70000000.0]
        mock_model.estimators_ = [MagicMock()] * 100

        def fake_load():
            service.model = mock_model
            return True

        mock_pd = MagicMock()

        with patch.object(service, "_load_model", side_effect=fake_load):
            with patch.object(service, "_get_deps", return_value=(MagicMock(), mock_pd, MagicMock())):
                result = service.predict_price(100000000)

        assert result["recommended_price"] == 70000000.0

    def test_confidence_calculation(self):
        """confidence는 max 0.95"""
        service = MLService()
        mock_model = MagicMock()
        mock_model.predict.return_value = [50000000.0]
        mock_model.estimators_ = [MagicMock()] * 200  # 200 estimators → 0.7 + 1.0 = 1.7 → min(0.95, 1.7) = 0.95
        service.model = mock_model

        mock_pd = MagicMock()
        with patch.object(service, "_get_deps", return_value=(MagicMock(), mock_pd, MagicMock())):
            result = service.predict_price(100000000)

        assert result["confidence"] == 0.95


class TestTrainModel:
    """train_model 테스트"""

    async def test_insufficient_data_empty(self):
        """데이터 0건 → InsufficientDataError"""
        service = MLService()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result

        mock_pd = MagicMock()
        with patch.object(service, "_get_deps", return_value=(MagicMock(), mock_pd, MagicMock())):
            with pytest.raises(InsufficientDataError):
                await service.train_model(mock_session)

    async def test_insufficient_data_below_minimum(self):
        """최소 샘플 미만 → InsufficientDataError"""
        service = MLService()

        # 3건 (최소 기본값 10보다 적음)
        mock_bids = [MagicMock() for _ in range(3)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_bids

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result

        mock_pd = MagicMock()
        with patch.object(service, "_get_deps", return_value=(MagicMock(), mock_pd, MagicMock())):
            with pytest.raises(InsufficientDataError):
                await service.train_model(mock_session)
