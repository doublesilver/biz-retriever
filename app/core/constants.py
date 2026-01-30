"""
Application-wide constants
Centralizes magic numbers and strings for better maintainability
"""

# Importance Scores
IMPORTANCE_LOW = 1
IMPORTANCE_MEDIUM = 2
IMPORTANCE_HIGH = 3

# Cache TTL (seconds)
CACHE_TTL_SHORT = 60  # 1 minute
CACHE_TTL_MEDIUM = 300  # 5 minutes
CACHE_TTL_LONG = 3600  # 1 hour

# Pagination
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 500

# ML Model
ML_MIN_TRAINING_SAMPLES = 10
ML_MODEL_PATH = "app/models/saved/bid_predictor.joblib"
ML_TEST_SIZE = 0.2
ML_RANDOM_STATE = 42
ML_N_ESTIMATORS = 100

# File Upload
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_FILE_EXTENSIONS = {".pdf", ".hwp"}

# Price Thresholds
PRICE_THRESHOLD_HIGH = 100_000_000  # 1억원

# Notification
NOTIFICATION_IMPORTANCE_THRESHOLD = IMPORTANCE_MEDIUM  # 2점 이상
MORNING_BRIEFING_HOUR = 8
MORNING_BRIEFING_MINUTE = 30

# API
API_TIMEOUT_SECONDS = 30
API_MAX_RETRIES = 3
