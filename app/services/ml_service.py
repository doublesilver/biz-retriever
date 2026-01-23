import os
import joblib
import pandas as pd
import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict
from app.db.models import BidResult
from app.core.logging import logger

class MLService:
    """
    Machine Learning Service for Bid Price Prediction
    Uses Random Forest Regressor to predict winning prices.
    """
    
    MODEL_PATH = "app/models/saved/bid_predictor.joblib"
    
    def __init__(self):
        self.model = None
        self._load_model()

    def _load_model(self):
        """Load trained model from disk if exists"""
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
        Fetch data from BidResult and train the model.
        Returns training metrics.
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
        
        if not bid_results or len(bid_results) < 10:
            logger.warning("⚠️ Not enough data to train model (need at least 10 records).")
            return {"status": "skipped", "reason": "insufficient_data"}

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
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        model = RandomForestRegressor(n_estimators=100, random_state=42)
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

    def predict_price(self, estimated_price: float, base_price: Optional[float] = None, category: Optional[str] = None) -> Optional[float]:
        """
        Predict winning price for a single item.
        """
        if not self.model:
            logger.warning("⚠️ Prediction requested but no model loaded.")
            return None
            
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
        return float(prediction)

ml_service = MLService()
ml_predictor = ml_service # Alias for analysis.py
MLBidPricePredictor = MLService # Alias for conftest.py (temporary)
