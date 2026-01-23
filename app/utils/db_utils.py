"""
Database utility functions
Common database operations to reduce code duplication
"""
from typing import Type, TypeVar, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from app.db.base import Base

T = TypeVar('T', bound=Base)


async def get_object_or_404(
    db: AsyncSession,
    model: Type[T],
    object_id: int,
    error_message: str = "Object not found"
) -> T:
    """
    Get object by ID or raise 404 error
    
    Args:
        db: Database session
        model: SQLAlchemy model class
        object_id: Object ID to fetch
        error_message: Custom error message
        
    Returns:
        Model instance
        
    Raises:
        HTTPException: 404 if object not found
        
    Example:
        >>> bid = await get_object_or_404(db, BidAnnouncement, 1)
    """
    obj = await db.get(model, object_id)
    if not obj:
        raise HTTPException(status_code=404, detail=error_message)
    return obj


async def get_or_create(
    db: AsyncSession,
    model: Type[T],
    defaults: dict = None,
    **kwargs
) -> Tuple[T, bool]:
    """
    Get existing object or create new one
    
    Args:
        db: Database session
        model: SQLAlchemy model class
        defaults: Default values for creation
        **kwargs: Filter criteria
        
    Returns:
        Tuple of (object, created) where created is True if new object
        
    Example:
        >>> user, created = await get_or_create(
        ...     db, User, 
        ...     defaults={"is_active": True},
        ...     email="test@example.com"
        ... )
    """
    # Try to get existing
    stmt = select(model).filter_by(**kwargs)
    result = await db.execute(stmt)
    obj = result.scalar_one_or_none()
    
    if obj:
        return obj, False
    
    # Create new
    if defaults is None:
        defaults = {}
    
    create_data = {**kwargs, **defaults}
    obj = model(**create_data)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    
    return obj, True


async def bulk_create(
    db: AsyncSession,
    model: Type[T],
    data_list: list[dict]
) -> list[T]:
    """
    Bulk create objects
    
    Args:
        db: Database session
        model: SQLAlchemy model class
        data_list: List of dictionaries with object data
        
    Returns:
        List of created objects
        
    Example:
        >>> bids = await bulk_create(db, BidAnnouncement, [
        ...     {"title": "Bid 1", "agency": "Agency A"},
        ...     {"title": "Bid 2", "agency": "Agency B"}
        ... ])
    """
    objects = [model(**data) for data in data_list]
    db.add_all(objects)
    await db.commit()
    
    for obj in objects:
        await db.refresh(obj)
    
    return objects
