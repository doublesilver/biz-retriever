import sys
import os
sys.path.append(os.getcwd())

try:
    from app.db.repositories.bid_repository import BidRepository
    from app.db.models import UserKeyword
    from app.schemas.keyword import UserKeywordCreate
    from app.api.endpoints import keywords
    print("Imports successful")
except Exception as e:
    print(f"Import failed: {e}")
    sys.exit(1)
