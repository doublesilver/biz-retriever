import os
import joblib
import pandas as pd
import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict
from app.db.models import BidResult
from app.core.logging import logger
from app.core.constants import (
    ML_MIN_TRAINING_SAMPLES,
    ML_MODEL_PATH,
    ML_TEST_SIZE,
    ML_RANDOM_STATE,
    ML_N_ESTIMATORS
)
from app.core.exceptions import InsufficientDataError, ModelNotTrainedError

class MLService:
    """
    Machine Learning Service for Bid Price Prediction
    
    Uses Random Forest Regressor to predict winning prices based on
    historical bid data. The model learns from past bid results to
    estimate optimal bidding prices.
    
    Attributes:
        MODEL_PATH: Path to saved model file
        model: Trained RandomForestRegressor instance
        
    Example:
        >>> ml_service = MLService()
        >>> await ml_service.train_model(db_session)
        >>> prediction = ml_service.predict_price(50_000_000)
    """
    
    MODEL_PATH = ML_MODEL_PATH
    
    def __init__(self):
        """Initialize ML service and load existing model if available"""
        self.model = None
        self._load_model()

    def _load_model(self):
        """
        Load trained model from disk if exists
        
        Attempts to load a previously trained model from MODEL_PATH.
        If no model exists, logs a warning and continues without error.
        """
        if os.path.exists(self.MODEL_PATH):
            try:
                self.model = joblib.load(self.MODEL_PATH)
                logger.info(f"✅ Loaded ML model from {self.MODEL_PATH}")
            except Exception as e:
                logger.error(f"❌ Failed to load ML model: {e}")
        else:
            logger.warning("⚠️ No trained model found. Prediction will not work until training is done.")

    async def train_model(self, db: AsyncSession) -> Dict[str, float]:
        """
        Train ML model with historical bid data
        
        Fetches BidResult data from database, prepares features,
        trains a Random Forest model, and saves it to disk.
        
        Args:
            db: Async database session
            
        Returns:
            Dictionary with training results:
                - status: "success" or "skipped"
                - samples: Number of training samples
                - mae: Mean Absolute Error
                - r2: R-squared score
                
        Raises:
            InsufficientDataError: If fewer than ML_MIN_TRAINING_SAMPLES records
            
        Example:
            >>> result = await ml_service.train_model(db)
            >>> print(f"Trained with {result['samples']} samples")
        """
        logger.info("🔄 Starting model training...")
        
        # 1. Fetch Data
        query = select(BidResult).where(
            BidResult.winning_price.isnot(None),
            BidResult.estimated_price.isnot(None), 
            BidResult.estimated_price > 0
        )
        result = await db.execute(query)
        bid_results = result.scalars().all()
        
        if not bid_results or len(bid_results) < ML_MIN_TRAINING_SAMPLES:
            raise InsufficientDataError(
                required=ML_MIN_TRAINING_SAMPLES,
                actual=len(bid_results) if bid_results else 0
            )

        # 2. Prepare Feature DataFrame
        data = []
        for bid in bid_results:
            data.append({
                "estimated_price": bid.estimated_price,
                "base_price": bid.base_price if bid.base_price else bid.estimated_price,
                "winning_price": bid.winning_price,
                "category_code": hash(bid.category) if bid.category else 0 # Simple encoding
            })
            
        df = pd.DataFrame(data)
        
        # Features (X) & Target (y)
        X = df[['estimated_price', 'base_price', 'category_code']]
        y = df['winning_price']
        
        # 3. Train Model (Lazy import to save startup time if not used)
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import mean_absolute_error, r2_score
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, 
            test_size=ML_TEST_SIZE, 
            random_state=ML_RANDOM_STATE
        )
        
        model = RandomForestRegressor(
            n_estimators=ML_N_ESTIMATORS, 
            random_state=ML_RANDOM_STATE
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
        
        return {
            "status": "success",
            "samples": len(df),
            "mae": mae,
            "r2": r2
        }

    def predict_price(
        self, 
        estimated_price: float, 
        base_price: Optional[float] = None, 
        category: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Predict winning price for a bid
        
        Uses the trained Random Forest model to predict the likely
        winning price based on estimated price and other features.
        
        Args:
            estimated_price: Estimated/base price from bid announcement
            base_price: Optional base price (defaults to estimated_price)
            category: Optional category for better prediction
            
        Returns:
            Dictionary with prediction results:
                - recommended_price: Predicted winning price
                - confidence: Model confidence (0-1)
                
        Raises:
            ModelNotTrainedError: If model hasn't been trained yet
            
        Example:
            >>> result = ml_service.predict_price(50_000_000)
            >>> print(f"Recommended: {result['recommended_price']:,}원")
        """
        if not self.model:
            raise ModelNotTrainedError()
            
        if not base_price:
            base_price = estimated_price
            
        category_code = hash(category) if category else 0
        
        # Create input DataFrame (must match training feature names)
        X_new = pd.DataFrame([{
            'estimated_price': estimated_price,
            'base_price': base_price,
            'category_code': category_code
        }])
        
        prediction = self.model.predict(X_new)[0]
        
        # Calculate confidence (simplified)
        confidence = min(0.95, 0.7 + (len(self.model.estimators_) / 200))
        
        return {
            "recommended_price": float(prediction),
            "confidence": confidence
        }

ml_service = MLService()
ml_predictor = ml_service # Alias for analysis.py
MLBidPricePredictor = MLService # Alias for conftest.py (temporary)
