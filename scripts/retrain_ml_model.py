"""
ML Model Retraining Script
Trains the model with real data and evaluates performance
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.db.session import SessionLocal
from app.services.ml_service import ml_service
from app.db.models import BidResult
from sqlalchemy import select

async def retrain_model():
    """Retrain ML model with collected data"""
    
    print("=" * 60)
    print("🧠 ML Model Retraining")
    print("=" * 60)
    
    async with SessionLocal() as session:
        # Check data availability
        result = await session.execute(select(BidResult))
        bid_results = result.scalars().all()
        
        print(f"\n📊 Available training data: {len(bid_results)} records")
        
        if len(bid_results) < 10:
            print("❌ Insufficient data for training (minimum: 10)")
            return False
        
        # Train model
        print("\n🔄 Training model...")
        training_result = await ml_service.train_model(session)
        
        print("\n" + "=" * 60)
        print("✅ Training Complete!")
        print("=" * 60)
        
        print(f"\n📊 Model Performance:")
        print(f"  - Samples: {training_result['samples']}")
        print(f"  - MAE: {training_result['mae']:,.0f}원")
        print(f"  - R²: {training_result['r2']:.4f}")
        
        # Evaluate
        if training_result['r2'] > 0.5:
            print("\n✅ Model quality: GOOD")
        elif training_result['r2'] > 0:
            print("\n⚠️ Model quality: ACCEPTABLE")
        else:
            print("\n❌ Model quality: POOR (need more data)")
        
        # Test prediction
        print("\n🧪 Testing prediction...")
        test_price = 500_000_000
        prediction = ml_service.predict_price(estimated_price=test_price)
        
        print(f"  Input: {test_price:,}원")
        print(f"  Predicted: {prediction['recommended_price']:,}원")
        print(f"  Confidence: {prediction['confidence']:.2%}")
        
        return True

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    success = asyncio.run(retrain_model())
    sys.exit(0 if success else 1)
