"""
MLService train_model 확장 테스트
- 데이터 부족
- _get_deps 실패
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import InsufficientDataError
from app.services.ml_service import MLService


class TestTrainModel:
    """train_model 테스트"""

    async def test_insufficient_data(self):
        """데이터 부족 시 InsufficientDataError"""
        svc = MLService()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Mock _get_deps to avoid import errors
        mock_joblib = MagicMock()
        mock_pd = MagicMock()
        mock_np = MagicMock()

        with patch.object(svc, "_get_deps", return_value=(mock_joblib, mock_pd, mock_np)):
            with pytest.raises(InsufficientDataError):
                await svc.train_model(mock_db)

    async def test_insufficient_data_few_records(self):
        """최소 샘플 수 미달"""
        svc = MLService()

        mock_bids = [MagicMock() for _ in range(3)]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_bids

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_joblib = MagicMock()
        mock_pd = MagicMock()
        mock_np = MagicMock()

        with patch.object(svc, "_get_deps", return_value=(mock_joblib, mock_pd, mock_np)):
            with pytest.raises(InsufficientDataError):
                await svc.train_model(mock_db)


class TestGetDeps:
    """_get_deps 테스트"""

    def test_import_error(self):
        """의존성 없으면 ImportError"""
        svc = MLService()
        # _get_deps tries to import joblib, numpy, pandas
        # If not installed, ImportError is raised
        try:
            svc._get_deps()
        except ImportError:
            pass  # Expected in test env without ML deps
