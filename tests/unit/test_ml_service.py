"""
ML Service 단위 테스트
- 학습/예측 플로우
- 데이터 부족 처리
- 모델 미학습 에러

sklearn/joblib이 설치되지 않은 환경에서는 skip
"""

import os
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import InsufficientDataError, ModelNotTrainedError
from app.db.models import BidResult
from app.services.ml_service import MLService

try:
    import joblib
    import numpy
    import pandas
    import sklearn

    HAS_ML_DEPS = True
except ImportError:
    HAS_ML_DEPS = False

ml_deps_required = pytest.mark.skipif(
    not HAS_ML_DEPS,
    reason="ML dependencies (sklearn, joblib, pandas, numpy) not installed",
)


@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    return session


@pytest.fixture
def ml_service():
    # Setup: Use a temp path for model to avoid overwriting real one
    original_path = MLService.MODEL_PATH
    MLService.MODEL_PATH = "tests/temp_model.joblib"

    service = MLService()

    yield service

    # Teardown: Clean up temp model
    if os.path.exists(MLService.MODEL_PATH):
        os.remove(MLService.MODEL_PATH)
    MLService.MODEL_PATH = original_path


@ml_deps_required
@pytest.mark.asyncio
async def test_train_model_insufficient_data(ml_service, mock_db_session):
    """데이터 부족 시 InsufficientDataError 발생"""
    # Mock DB returning empty list
    result_mock = MagicMock()
    result_mock.scalars().all.return_value = []
    mock_db_session.execute.return_value = result_mock

    with pytest.raises(InsufficientDataError):
        await ml_service.train_model(mock_db_session)


@ml_deps_required
@pytest.mark.asyncio
async def test_train_and_predict_flow(ml_service, mock_db_session):
    """학습 및 예측 플로우 테스트"""
    # Mock DB returning dummy data (20 records)
    dummy_data = []
    for i in range(20):
        est = 10000 + (i * 1000)
        dummy_data.append(
            BidResult(
                winning_price=est * 0.95,
                estimated_price=est,
                base_price=est,
                category="Test",  # 95% winning rate
            )
        )

    result_mock = MagicMock()
    result_mock.scalars().all.return_value = dummy_data
    mock_db_session.execute.return_value = result_mock

    # 1. Train
    metrics = await ml_service.train_model(mock_db_session)
    assert metrics["status"] == "success"
    assert metrics["samples"] == 20
    assert metrics["r2"] > 0.8  # Synthetic data should have good fit

    # 2. Predict
    result = ml_service.predict_price(
        estimated_price=20000, base_price=20000, category="Test"
    )

    assert result is not None
    assert "recommended_price" in result
    assert "confidence" in result
    # Expect around 19000 (95% of 20000)
    assert 18000 < result["recommended_price"] < 20000


@pytest.mark.asyncio
async def test_predict_without_trained_model(ml_service):
    """모델 미학습 시 ModelNotTrainedError 발생"""
    ml_service.model = None

    with pytest.raises(ModelNotTrainedError):
        ml_service.predict_price(estimated_price=10000)


@ml_deps_required
@pytest.mark.asyncio
async def test_predict_returns_required_fields(ml_service, mock_db_session):
    """예측 결과가 필수 필드를 포함하는지 확인"""
    # Setup: Train with dummy data
    dummy_data = []
    for i in range(20):
        est = 10000 + (i * 1000)
        dummy_data.append(
            BidResult(
                winning_price=est * 0.95,
                estimated_price=est,
                base_price=est,
                category="Test",
            )
        )

    result_mock = MagicMock()
    result_mock.scalars().all.return_value = dummy_data
    mock_db_session.execute.return_value = result_mock

    await ml_service.train_model(mock_db_session)

    result = ml_service.predict_price(estimated_price=15000)

    assert "recommended_price" in result
    assert "confidence" in result
    assert isinstance(result["recommended_price"], float)
    assert 0 <= result["confidence"] <= 1
