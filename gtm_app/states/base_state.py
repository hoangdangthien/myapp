"""Base state for the GTM App - handles common app-wide state."""
import reflex as rx
from sqlalchemy import create_engine
import pandas as pd
import urllib
import os
from typing import Optional


class BaseState(rx.State):
    """The base state for the application.
    
    Contains common state variables and methods used across multiple pages.
    Includes MSSQL Server connection for Production monitoring.
    """
    
    # Sidebar toggle state
    sidebar_open: bool = True
    
    # ========== MSSQL Production Data ==========
    # Master table data
    master_data: list[dict] = []
    
    # Connection parameters (loaded from environment variables)
    server: str = os.getenv("MSSQL_SERVER", "")
    database: str = os.getenv("MSSQL_DATABASE", "")
    username: str = os.getenv("MSSQL_USERNAME", "")
    password: str = os.getenv("MSSQL_PASSWORD", "")
    driver: str = os.getenv("MSSQL_DRIVER", "{ODBC Driver 17 for SQL Server}")
    
    # Connection status
    connection_status: str = "Not connected"
    error_message: str = ""
    
    # Filter/search state
    search_value: str = ""
    selected_platform: str = ""
    
    # Available filter options (cached in backend)
    available_platforms: list[str] = []
    
    # Cached computed values (updated in backend)
    _total_wells: int = 0
    _unique_platforms: int = 0
    
    def toggle_sidebar(self):
        """Toggle the sidebar visibility."""
        self.sidebar_open = not self.sidebar_open
    
    # ========== MSSQL Connection Methods ==========
    
    def get_engine(self):
        """Create SQLAlchemy engine for MSSQL Server connection.
        
        Returns:
            SQLAlchemy engine object or None if connection fails
        """
        try:
            conn = f"""Driver={self.driver};Server={self.server};Database={self.database};
                       Uid={self.username};Pwd={self.password};Encrypt=yes;TrustServerCertificate=yes;"""
            
            params = urllib.parse.quote_plus(conn)
            conn_str = f'mssql+pyodbc:///?autocommit=true&odbc_connect={params}'
            engine = create_engine(conn_str, echo=False)
            
            return engine
        except Exception as e:
            self.error_message = str(e)
            self.connection_status = f"Connection failed: {str(e)}"
            return None
    
    def load_master_data(self):
        """Load Master table data from MSSQL Server database."""
        try:
            self.connection_status = "Connecting..."
            
            engine = self.get_engine()
            if not engine:
                return rx.toast.error("Failed to connect to database")
            
            # Build query with filters
            query = "SELECT UniqueId, Wellname, Platform FROM Master"
            conditions = []
            
            if self.search_value:
                conditions.append(
                    f"(UniqueId LIKE '%{self.search_value}%' OR Wellname LIKE '%{self.search_value}%')"
                )
            
            if self.selected_platform and self.selected_platform != "All Platforms":
                conditions.append(f"Platform = '{self.selected_platform}'")
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            # Execute query
            df = pd.read_sql(query, engine)
            
            # Convert to list of dicts for Reflex
            self.master_data = df.to_dict('records')
            
            # Update computed values
            self._total_wells = len(self.master_data)
            
            # Extract unique platforms for filters
            if not self.selected_platform and 'Platform' in df.columns:
                self.available_platforms = sorted(df['Platform'].unique().tolist())
                self._unique_platforms = len(df['Platform'].unique())
            
            self.connection_status = f"Connected - {self._total_wells} wells loaded"
            engine.dispose()
            
            return rx.toast.success(f"Loaded {self._total_wells} wells from Master table")
            
        except Exception as e:
            self.error_message = str(e)
            self.connection_status = f"Error: {str(e)}"
            self._total_wells = 0
            self._unique_platforms = 0
            print(f"Error loading master data: {e}")
            return rx.toast.error(f"Failed to load data: {str(e)}")
    
    def filter_master_data(self, search_value: str):
        """Filter master data by search term."""
        self.search_value = search_value
        self.load_master_data()
    
    def filter_by_platform(self, platform: str):
        """Filter by selected platform."""
        if platform == "All Platforms":
            self.selected_platform = ""
        else:
            self.selected_platform = platform
        self.load_master_data()
    
    def clear_filters(self):
        """Clear all filters and reload data."""
        self.search_value = ""
        self.selected_platform = ""
        self.load_master_data()
    
    def update_connection_params(self, form_data: dict):
        """Update database connection parameters."""
        self.server = form_data.get("server", self.server)
        self.database = form_data.get("database", self.database)
        self.username = form_data.get("username", self.username)
        self.password = form_data.get("password", self.password)
        
        return rx.toast.info("Connection parameters updated. Click 'Connect' to load data.")
    
    # ========== Computed Properties ==========
    
    @rx.var
    def total_wells(self) -> int:
        """Get total count of wells in Master table."""
        return self._total_wells
    
    @rx.var
    def unique_platforms(self) -> int:
        """Get count of unique platforms."""
        return self._unique_platforms
    
    @rx.var
    def connection_indicator_color(self) -> str:
        """Get color for connection status indicator."""
        if "Connected" in self.connection_status:
            return "green"
        elif "Connecting" in self.connection_status:
            return "yellow"
        else:
            return "red"
    
    @rx.var
    def platform_filter_options(self) -> list[str]:
        """Get platform filter options with 'All Platforms' prepended."""
        return ["All Platforms"] + self.available_platforms