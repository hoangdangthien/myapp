"""State management for Well Intervention (GTM) operations."""
import reflex as rx
from collections import Counter
from typing import Optional
from datetime import datetime, timedelta
import numpy as np
from sqlmodel import String, asc, cast, desc, func, or_, select

from ..models import Intervention, InterventionProd


class GTMState(rx.State):
    """State for managing Well Intervention (GTM) data.
    
    Handles CRUD operations, Excel import, forecasting, and data transformations.
    """
    
    # List of all interventions
    GTM: list[Intervention] = []
    
    # Production data for selected intervention
    intervention_prod: list[InterventionProd] = []
    
    # Data transformed for graph visualization
    gtms_for_graph: list[dict] = []
    
    # Currently selected intervention for editing/viewing
    current_gtm: Optional[Intervention] = None
    
    # Selected ID for chart display
    selected_id: str = ""
    
    # Available IDs for selection
    available_ids: list[str] = []
    
    # Forecast parameters
    forecast_end_date: str = ""
    
    # Forecast results
    forecast_data: list[dict] = []
    
    # Chart data combining actual + forecast
    chart_data: list[dict] = []
    
    # Intervention date for vertical line
    intervention_date: str = ""
    
    # Search/filter state
    search_value: str = ""
    selected_field: str = ""
    selected_status: str = ""
    
    # File upload state
    upload_progress: int = 0
    upload_status: str = ""
    
    # Dialog control state
    add_dialog_open: bool = False
    
    def set_add_dialog_open(self, is_open: bool):
        """Control add dialog open state."""
        self.add_dialog_open = is_open

    def load_gtms(self):
        """Load all GTMs from database."""
        try:
            with rx.session() as session:
                query = select(Intervention)
                if self.search_value:
                    search_value = f"%{str(self.search_value).lower()}%"
                    query = query.where(
                        or_(
                            *[
                                getattr(Intervention,field).ilike(search_value)
                                for field in Intervention.model_fields.keys()
                            ]
                        )
                    )
                self.GTM = session.exec(
                   query
                ).all()
            self.transform_data()
            self.available_ids = [gtm.UniqueId for gtm in self.GTM]
            if self.available_ids and not self.selected_id:
                self.selected_id = self.available_ids[0]
                self.load_production_data()
        except Exception as e:
            print(f"Error loading GTMs: {e}")
            self.GTM = []

    def load_production_data(self):
        """Load production data for selected intervention."""
        if not self.selected_id:
            self.intervention_prod = []
            self.chart_data = []
            return
            
        try:
            with rx.session() as session:
                self.intervention_prod = session.exec(
                    InterventionProd.select().where(
                        InterventionProd.UniqueId == self.selected_id
                    )
                ).all()
            
            # Get intervention date
            selected_gtm = next(
                (g for g in self.GTM if g.UniqueId == self.selected_id), None
            )
            if selected_gtm:
                self.intervention_date = selected_gtm.PlanningDate
                self.current_gtm = selected_gtm
            
            # Transform to chart data
            self.update_chart_data()
            
        except Exception as e:
            print(f"Error loading production data: {e}")
            self.intervention_prod = []
    def filter_intervention(self,search_value):
        self.search_value = search_value
        self.load_gtms()
    def update_chart_data(self):
        """Update chart data combining actual and forecast."""
        chart_points = []
        
        # Add actual production data
        for prod in sorted(self.intervention_prod, key=lambda x: x.Date):
            chart_points.append({
                "date": prod.Date,
                "oilRate": prod.OilRate,
                "liqRate": prod.LiqRate,
                "type": "actual"
            })
        
        # Add forecast data if available
        for fc in self.forecast_data:
            chart_points.append({
                "date": fc["date"],
                "oilRateForecast": fc["oilRate"],
                "liqRateForecast": fc["liqRate"],
                "type": "forecast"
            })
        
        self.chart_data = chart_points

    def set_selected_id(self, id_value: str):
        """Set selected intervention ID and load its data."""
        self.selected_id = id_value
        self.forecast_data = []
        self.load_production_data()

    def set_forecast_end_date(self, date: str):
        """Set the forecast end date."""
        self.forecast_end_date = date

    def run_forecast(self):
        """Run Arps decline curve forecast for selected intervention."""
        if not self.current_gtm or not self.forecast_end_date:
            return rx.toast.error("Please select an intervention and set forecast end date")
        
        if not self.intervention_prod:
            return rx.toast.error("No production data available for forecasting")
        
        try:
            # Get last production date
            sorted_prod = sorted(self.intervention_prod, key=lambda x: x.Date)
            last_prod = sorted_prod[-1]
            last_date = datetime.strptime(last_prod.Date, "%Y-%m-%d")
            end_date = datetime.strptime(self.forecast_end_date, "%Y-%m-%d")
            
            if end_date <= last_date:
                return rx.toast.error("Forecast end date must be after last production date")
            
            # Arps decline parameters from current GTM
            qi_oil = self.current_gtm.InitialORate
            b_oil = self.current_gtm.bo
            di_oil = self.current_gtm.Dio
            
            qi_liq = self.current_gtm.InitialLRate
            b_liq = self.current_gtm.bl
            di_liq = self.current_gtm.Dil
            
            # Use last actual rates as starting point if available
            qi_oil = last_prod.OilRate if last_prod.OilRate > 0 else qi_oil
            qi_liq = last_prod.LiqRate if last_prod.LiqRate > 0 else qi_liq
            
            # Generate forecast
            forecast_points = []
            current_date = last_date + timedelta(days=30)  # Monthly forecast
            t = 1  # Time in months
            
            while current_date <= end_date:
                # Arps hyperbolic decline: q(t) = qi / (1 + b*Di*t)^(1/b)
                if b_oil > 0 and di_oil > 0:
                    oil_rate = qi_oil / ((1 + b_oil * di_oil * t) ** (1/b_oil))
                else:
                    oil_rate = qi_oil * np.exp(-di_oil * t) if di_oil > 0 else qi_oil
                
                if b_liq > 0 and di_liq > 0:
                    liq_rate = qi_liq / ((1 + b_liq * di_liq * t) ** (1/b_liq))
                else:
                    liq_rate = qi_liq * np.exp(-di_liq * t) if di_liq > 0 else qi_liq
                
                forecast_points.append({
                    "date": current_date.strftime("%Y-%m-%d"),
                    "oilRate": max(0, round(oil_rate, 2)),
                    "liqRate": max(0, round(liq_rate, 2))
                })
                
                current_date += timedelta(days=30)
                t += 1
            
            self.forecast_data = forecast_points
            self.update_chart_data()
            return rx.toast.success(f"Forecast generated with {len(forecast_points)} points")
            
        except Exception as e:
            print(f"Forecast error: {e}")
            return rx.toast.error(f"Forecast failed: {str(e)}")

    async def handle_excel_upload(self, files: list[rx.UploadFile]):
        """Handle Excel file upload for interventions."""
        if not files:
            return rx.toast.error("No file selected")
        
        try:
            import pandas as pd
            
            file = files[0]
            upload_data = await file.read()
            
            # Read Excel file
            import io
            df = pd.read_excel(io.BytesIO(upload_data))
            
            # Required columns
            required_cols = [
                'UniqueId', 'Field', 'Platform', 'Reservoir', 'TypeGTM',
                'PlanningDate', 'Status', 'InitialORate', 'bo', 'Dio',
                'InitialLRate', 'bl', 'Dil'
            ]
            
            # Check for required columns
            missing_cols = [c for c in required_cols if c not in df.columns]
            if missing_cols:
                return rx.toast.error(f"Missing columns: {', '.join(missing_cols)}")
            
            # Insert records
            added_count = 0
            with rx.session() as session:
                for _, row in df.iterrows():
                    # Check if exists
                    existing = session.exec(
                        Intervention.select().where(
                            Intervention.UniqueId == str(row['UniqueId'])
                        )
                    ).first()
                    
                    if not existing:
                        new_gtm = Intervention(
                            UniqueId=str(row['UniqueId']),
                            Field=str(row['Field']),
                            Platform=str(row['Platform']),
                            Reservoir=str(row['Reservoir']),
                            TypeGTM=str(row['TypeGTM']),
                            PlanningDate=str(row['PlanningDate'])[:10],
                            Status=str(row['Status']),
                            InitialORate=float(row['InitialORate']),
                            bo=float(row['bo']),
                            Dio=float(row['Dio']),
                            InitialLRate=float(row['InitialLRate']),
                            bl=float(row['bl']),
                            Dil=float(row['Dil'])
                        )
                        session.add(new_gtm)
                        added_count += 1
                
                session.commit()
            
            self.load_gtms()
            return rx.toast.success(f"Added {added_count} interventions from Excel")
            
        except Exception as e:
            print(f"Excel upload error: {e}")
            return rx.toast.error(f"Failed to load Excel: {str(e)}")

    def add_gtm(self, form_data: dict):
        """Add new GTM to database using Reflex/SQLModel."""
        try:
            # Ensure all required fields have values
            if not form_data.get("UniqueId"):
                return rx.toast.error("UniqueId is required!")
            
            if not form_data.get("PlanningDate"):
                return rx.toast.error("Planning Date is required!")
            
            # Convert numeric fields with defaults
            form_data["InitialORate"] = float(form_data.get("InitialORate") or 0)
            form_data["bo"] = float(form_data.get("bo") or 0)
            form_data["Dio"] = float(form_data.get("Dio") or 0)
            form_data["InitialLRate"] = float(form_data.get("InitialLRate") or 0)
            form_data["bl"] = float(form_data.get("bl") or 0)
            form_data["Dil"] = float(form_data.get("Dil") or 0)
            
            # Set default status if not provided
            if not form_data.get("Status"):
                form_data["Status"] = "Plan"
            
            with rx.session() as session:
                existing = session.exec(
                    Intervention.select().where(
                        Intervention.UniqueId == form_data["UniqueId"]
                    )
                ).first()
                
                if existing:
                    return rx.toast.error(
                        f"UniqueId '{form_data['UniqueId']}' already exists!"
                    )
                
                new_gtm = Intervention(**form_data)
                session.add(new_gtm)
                session.commit()
                session.refresh(new_gtm)
            
            # Close dialog and reload data
            #self.add_dialog_open = False
            self.load_gtms()
            return rx.toast.success("GTM added successfully!")
            
        except Exception as e:
            print(f"Database error: {e}")
            return rx.toast.error(f"Failed to save GTM: {str(e)}")

    def get_gtm(self, gtm: Intervention):
        """Set the current GTM for editing."""
        self.current_gtm = gtm

    def update_gtm(self, form_data: dict):
        """Update existing GTM in database with partial update support.
        
        Only updates fields that have non-empty values in form_data.
        Empty strings or None values are ignored, keeping existing values.
        """
        try:
            with rx.session() as session:
                gtm_to_update = session.exec(
                    Intervention.select().where(
                        Intervention.UniqueId == self.current_gtm.UniqueId
                    )
                ).first()
                
                if gtm_to_update:
                    # Update string fields only if non-empty value provided
                    string_fields = ["Field", "Platform", "Reservoir", "TypeGTM", "PlanningDate", "Status"]
                    for field in string_fields:
                        value = form_data.get(field)
                        if value and str(value).strip():  # Check for non-empty string
                            setattr(gtm_to_update, field, value)
                    
                    # Update numeric fields only if valid value provided
                    numeric_fields = [
                        ("InitialORate", "InitialORate"),
                        ("bo", "bo"),
                        ("Dio", "Dio"),
                        ("InitialLRate", "InitialLRate"),
                        ("bl", "bl"),
                        ("Dil", "Dil"),
                    ]
                    for form_key, model_field in numeric_fields:
                        value = form_data.get(form_key)
                        if value is not None and str(value).strip():
                            try:
                                numeric_value = float(value)
                                setattr(gtm_to_update, model_field, numeric_value)
                            except (ValueError, TypeError):
                                # Keep existing value if conversion fails
                                pass
                    
                    session.add(gtm_to_update)
                    session.commit()
                    
            self.load_gtms()
            return rx.toast.success("GTM updated successfully!")
            
        except Exception as e:
            print(f"Update error: {e}")
            return rx.toast.error(f"Failed to update GTM: {str(e)}")

    def delete_gtm(self, unique_id: str):
        """Delete GTM from database."""
        try:
            with rx.session() as session:
                gtm_to_delete = session.exec(
                    Intervention.select().where(
                        Intervention.UniqueId == unique_id
                    )
                ).first()
                
                if gtm_to_delete:
                    session.delete(gtm_to_delete)
                    session.commit()
                    
            self.load_gtms()
            return rx.toast.success("GTM deleted successfully!")
            
        except Exception as e:
            print(f"Delete error: {e}")
            return rx.toast.error(f"Failed to delete GTM: {str(e)}")

    def transform_data(self):
        """Transform GTM type data for visualization."""
        type_counts = Counter(gtm.TypeGTM for gtm in self.GTM)
        self.gtms_for_graph = [
            {"name": gtm_group, "value": count}
            for gtm_group, count in type_counts.items()
        ]
    
    @rx.var
    def total_interventions(self) -> int:
        """Get total count of interventions."""
        return len(self.GTM)
    
    @rx.var
    def planned_interventions(self) -> int:
        """Get count of planned interventions."""
        return sum(1 for gtm in self.GTM if gtm.Status == "Plan")
    
    @rx.var
    def completed_interventions(self) -> int:
        """Get count of completed interventions."""
        return sum(1 for gtm in self.GTM if gtm.Status == "Done")
    
    @rx.var
    def production_table_data(self) -> list[dict]:
        """Get production data formatted for table display."""
        return [
            {
                "Date": p.Date,
                "OilRate": f"{p.OilRate:.1f}",
                "LiqRate": f"{p.LiqRate:.1f}",
                "WC": f"{p.WC:.1f}"
            }
            for p in sorted(self.intervention_prod, key=lambda x: x.Date, reverse=True)[:10]
        ]
    
    @rx.var
    def forecast_table_data(self) -> list[dict]:
        """Get forecast data formatted for table display."""
        return [
            {
                "Date": f["date"],
                "OilRate": f"{f['oilRate']:.1f}",
                "LiqRate": f"{f['liqRate']:.1f}"
            }
            for f in self.forecast_data[:10]
        ]