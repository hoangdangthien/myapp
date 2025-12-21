"""Database Service - Centralized database operations.

This service provides:
- Common query patterns
- Session management helpers
- Data loading utilities
"""
import reflex as rx
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Type, TypeVar
from sqlmodel import select, func

T = TypeVar('T')


class DatabaseService:
    """Service class for common database operations."""
    
    @staticmethod
    def get_distinct_values(
        session,
        model_class: Type[T],
        field_name: str,
        filter_conditions: List = None
    ) -> List[Any]:
        """Get distinct values for a field.
        
        Args:
            session: Database session
            model_class: The model class
            field_name: Name of the field
            filter_conditions: Optional list of filter conditions
            
        Returns:
            List of distinct values
        """
        field = getattr(model_class, field_name)
        query = select(field).distinct()
        
        if filter_conditions:
            for condition in filter_conditions:
                query = query.where(condition)
        
        return list(session.exec(query).all())
    
    @staticmethod
    def get_available_versions(
        session,
        model_class: Type[T],
        unique_id: str,
        min_version: int = 0
    ) -> List[int]:
        """Get available forecast versions for a unique ID.
        
        Args:
            session: Database session
            model_class: The model class
            unique_id: The unique identifier
            min_version: Minimum version to include
            
        Returns:
            Sorted list of version numbers
        """
        versions = session.exec(
            select(model_class.Version).where(
                model_class.UniqueId == unique_id,
                model_class.Version >= min_version
            ).distinct()
        ).all()
        
        return sorted(versions)
    
    @staticmethod
    def load_forecast_by_version(
        session,
        model_class: Type[T],
        unique_id: str,
        version: int
    ) -> List[Dict]:
        """Load forecast data for a specific version.
        
        Args:
            session: Database session
            model_class: The model class
            unique_id: The unique identifier
            version: Version number
            
        Returns:
            List of forecast records as dictionaries
        """
        records = session.exec(
            select(model_class).where(
                model_class.UniqueId == unique_id,
                model_class.Version == version
            ).order_by(model_class.Date)
        ).all()
        
        return [
            {
                "date": rec.Date.strftime("%Y-%m-%d") if isinstance(rec.Date, datetime) else str(rec.Date),
                "oilRate": rec.OilRate,
                "liqRate": rec.LiqRate,
                "qOil": rec.Qoil,
                "qLiq": rec.Qliq,
                "wc": rec.WC
            }
            for rec in records
        ]
    
    @staticmethod
    def check_record_exists(
        session,
        model_class: Type[T],
        conditions: Dict[str, Any]
    ) -> bool:
        """Check if a record exists matching conditions.
        
        Args:
            session: Database session
            model_class: The model class
            conditions: Dictionary of field -> value conditions
            
        Returns:
            True if record exists
        """
        query = select(model_class)
        for field, value in conditions.items():
            query = query.where(getattr(model_class, field) == value)
        
        result = session.exec(query.limit(1)).first()
        return result is not None
    
    @staticmethod
    def get_record_count(
        session,
        model_class: Type[T],
        conditions: Dict[str, Any] = None
    ) -> int:
        """Get count of records matching conditions.
        
        Args:
            session: Database session
            model_class: The model class
            conditions: Optional dictionary of conditions
            
        Returns:
            Count of matching records
        """
        query = select(func.count()).select_from(model_class)
        
        if conditions:
            for field, value in conditions.items():
                query = query.where(getattr(model_class, field) == value)
        
        return session.exec(query).one()
    
    @staticmethod
    def get_latest_record(
        session,
        model_class: Type[T],
        unique_id: str,
        date_field: str = "Date"
    ) -> Optional[T]:
        """Get the latest record by date for a unique ID.
        
        Args:
            session: Database session
            model_class: The model class
            unique_id: The unique identifier
            date_field: Name of the date field
            
        Returns:
            Latest record or None
        """
        from sqlmodel import desc
        
        return session.exec(
            select(model_class).where(
                model_class.UniqueId == unique_id
            ).order_by(desc(getattr(model_class, date_field))).limit(1)
        ).first()
    
    @staticmethod
    def bulk_load_history(
        session,
        model_class: Type[T],
        unique_ids: List[str] = None,
        cutoff_date: datetime = None
    ) -> Dict[str, List[Dict]]:
        """Bulk load history data for multiple unique IDs.
        
        Args:
            session: Database session
            model_class: The model class (e.g., HistoryProd)
            unique_ids: Optional list of IDs to filter
            cutoff_date: Optional cutoff date
            
        Returns:
            Dictionary mapping unique_id to list of records
        """
        from sqlmodel import desc
        from ..utils.dca_utils import calculate_water_cut
        
        query = select(model_class)
        
        if unique_ids:
            query = query.where(model_class.UniqueId.in_(unique_ids))
        
        if cutoff_date:
            query = query.where(model_class.Date >= cutoff_date)
        
        query = query.order_by(desc(model_class.Date))
        
        records = session.exec(query).all()
        
        # Group by UniqueId
        result = {}
        for rec in records:
            uid = rec.UniqueId
            if uid not in result:
                result[uid] = []
            
            oil_rate = rec.OilRate if rec.OilRate else 0.0
            liq_rate = rec.LiqRate if rec.LiqRate else 0.0
            
            result[uid].append({
                "Date": rec.Date,
                "OilRate": oil_rate,
                "LiqRate": liq_rate,
                "WC": round(calculate_water_cut(oil_rate, liq_rate), 2)
            })
        
        return result