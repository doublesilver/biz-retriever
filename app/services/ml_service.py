import os
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (ML_MIN_TRAINING_SAMPLES, ML_MODEL_PATH,
                                ML_N_ESTIMATORS, ML_RANDOM_STATE, ML_TEST_SIZE)
from app.core.exceptions import InsufficientDataError, ModelNotTrainedError
from app.core.logging import logger
from app.db.models import BidResult

if TYPE_CHECKING:
    import numpy as np
    import pandas as pd


class MLService:
    """
    Machine Learning Service for Bid Price Prediction

    Uses Random Forest Regressor to predict winning prices.
    Optimized for Raspberry Pi: Uses lazy loading for heavy libraries.
    """

    MODEL_PATH = ML_MODEL_PATH

    def __init__(self):
        """Initialize ML service"""
        self.model = None
        # Do not load model at startup to save memory
        # self._load_model()

    def _get_deps(self):
        """Lazy load heavy dependencies"""
        try:
            import joblib
            import numpy as np
            import pandas as pd

            return joblib, pd, np
        except ImportError as e:
            logger.error(f"❌ ML dependencies missing: {e}")
            raise

    def _load_model(self):
        """Load trained model from disk if exists"""
        if os.path.exists(self.MODEL_PATH):
            try:
                joblib, _, _ = self._get_deps()
                self.model = joblib.load(self.MODEL_PATH)
                logger.info(f"✅ Loaded ML model from {self.MODEL_PATH}")
                return True
            except Exception as e:
                logger.error(f"❌ Failed to load ML model: {e}")
                return False
        return False

    async def train_model(self, db: AsyncSession) -> Dict[str, float]:
        """Train ML model with historical bid data"""
        logger.info("🔄 Starting model training...")

        # Lazy load deps
        joblib, pd, np = self._get_deps()

        # 1. Fetch Data
        query = select(BidResult).where(
            BidResult.winning_price.isnot(None),
            BidResult.estimated_price.isnot(None),
            BidResult.estimated_price > 0,
        )
        result = await db.execute(query)
        bid_results = result.scalars().all()

        if not bid_results or len(bid_results) < ML_MIN_TRAINING_SAMPLES:
            raise InsufficientDataError(
                required=ML_MIN_TRAINING_SAMPLES,
                actual=len(bid_results) if bid_results else 0,
            )

        # 2. Prepare Feature DataFrame
        data = []
        for bid in bid_results:
            data.append(
                {
                    "estimated_price": bid.estimated_price,
                    "base_price": (
                        bid.base_price if bid.base_price else bid.estimated_price
                    ),
                    "winning_price": bid.winning_price,
                    "category_code": hash(bid.category) if bid.category else 0,
                }
            )

        df = pd.DataFrame(data)

        # Features (X) & Target (y)
        X = df[["estimated_price", "base_price", "category_code"]]
        y = df["winning_price"]

        # 3. Train Model (Lazy import)
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.metrics import mean_absolute_error, r2_score
        from sklearn.model_selection import train_test_split

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=ML_TEST_SIZE, random_state=ML_RANDOM_STATE
        )

        model = RandomForestRegressor(
            n_estimators=ML_N_ESTIMATORS, random_state=ML_RANDOM_STATE
        )
        model.fit(X_train, y_train)

        # 4. Evaluate
        predictions = model.predict(X_test)
        mae = mean_absolute_error(y_test, predictions)
        r2 = r2_score(y_test, predictions)

        logger.info(f"✅ Model trained. MAE: {mae:,.0f}, R2: {r2:.4f}")

        # 5. Save Model
        os.makedirs(os.path.dirname(self.MODEL_PATH), exist_ok=True)
        joblib.dump(model, self.MODEL_PATH)
        self.model = model

        return {"status": "success", "samples": len(df), "mae": mae, "r2": r2}

    def predict_price(
        self,
        estimated_price: float,
        base_price: Optional[float] = None,
        category: Optional[str] = None,
    ) -> Dict[str, float]:
        """Predict winning price for a bid"""
        # Try to load model if not loaded
        if not self.model:
            if not self._load_model():
                raise ModelNotTrainedError()

        # Lazy load deps
        _, pd, _ = self._get_deps()

        if not base_price:
            base_price = estimated_price

        category_code = hash(category) if category else 0

        # Create input DataFrame
        X_new = pd.DataFrame(
            [
                {
                    "estimated_price": estimated_price,
                    "base_price": base_price,
                    "category_code": category_code,
                }
            ]
        )

        prediction = self.model.predict(X_new)[0]

        # Calculate confidence
        confidence = min(0.95, 0.7 + (len(self.model.estimators_) / 200))

        return {"recommended_price": float(prediction), "confidence": confidence}


ml_service = MLService()
ml_predictor = ml_service
MLBidPricePredictor = MLService
