import pytest
import os
import shutil
from unittest.mock import AsyncMock, MagicMock
from app.services.ml_service import MLService
from app.db.models import BidResult

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

@pytest.mark.asyncio
async def test_train_model_insufficient_data(ml_service, mock_db_session):
    # Mock DB returning empty list
    result_mock = MagicMock()
    result_mock.scalars().all.return_value = []
    mock_db_session.execute.return_value = result_mock
    
    metrics = await ml_service.train_model(mock_db_session)
    
    assert metrics["status"] == "skipped"
    assert metrics["reason"] == "insufficient_data"

@pytest.mark.asyncio
async def test_train_and_predict_flow(ml_service, mock_db_session):
    # Mock DB returning dummy data (20 records)
    dummy_data = []
    for i in range(20):
        est = 10000 + (i * 1000)
        dummy_data.append(BidResult(
            winning_price=est * 0.95, # 95% winning rate
            estimated_price=est,
            base_price=est,
            category="Test"
        ))
    
    result_mock = MagicMock()
    result_mock.scalars().all.return_value = dummy_data
    mock_db_session.execute.return_value = result_mock
    
    # 1. Train
    metrics = await ml_service.train_model(mock_db_session)
    assert metrics["status"] == "success"
    assert metrics["samples"] == 20
    assert metrics["r2"] > 0.8 # Synthetic data should have good fit
    
    # 2. Predict
    prediction = ml_service.predict_price(
        estimated_price=20000,
        base_price=20000,
        category="Test"
    )
    
    assert prediction is not None
    # Expect around 19000 (95% of 20000)
    assert 18000 < prediction < 20000 
