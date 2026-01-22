from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy import func

class Base(AsyncAttrs, DeclarativeBase):
    pass

class TimestampMixin:
    """
    Mixin for created_at and updated_at timestamps
    """
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )
