"""
Backward compatibility re-export.
HardMatchEngine is now part of matching_service.py (unified matching module).
"""

from app.services.matching_service import HardMatchEngine, hard_match_engine

__all__ = ["HardMatchEngine", "hard_match_engine"]
