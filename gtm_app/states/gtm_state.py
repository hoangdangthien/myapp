"""State management for Well Intervention (GTM) operations."""
import reflex as rx
from collections import Counter
from typing import Optional

from ..models import Intervention, InterventionProd


class GTMState(rx.State):
    """State for managing Well Intervention (GTM) data.
    
    Handles CRUD operations and data transformations for visualization.
    """
    
    # List of all interventions
    GTM: list[Intervention] = []
    
    # Data transformed for graph visualization
    gtms_for_graph: list[dict] = []
    
    # Currently selected intervention for editing
    current_gtm: Optional[Intervention] = None
    
    # Search/filter state
    search_query: str = ""
    selected_field: str = ""
    selected_status: str = ""
    
    def load_gtms(self):
        """Load all GTMs from database."""
        try:
            with rx.session() as session:
                self.GTM = session.exec(
                    Intervention.select()
                ).all()
            self.transform_data()
        except Exception as e:
            print(f"Error loading GTMs: {e}")
            self.GTM = []

    def add_gtm(self, form_data: dict):
        """Add new GTM to database using Reflex/SQLModel.
        
        Args:
            form_data: Dictionary containing intervention data from form
        """
        try:
            # Convert numeric fields
            form_data["InitialORate"] = float(form_data.get("InitialORate", 0))
            form_data["bo"] = float(form_data.get("bo", 0))
            form_data["Dio"] = float(form_data.get("Dio", 0))
            form_data["InitialLRate"] = float(form_data.get("InitialLRate", 0))
            form_data["bl"] = float(form_data.get("bl", 0))
            form_data["Dil"] = float(form_data.get("Dil", 0))
            
            with rx.session() as session:
                # Check if UniqueId already exists
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
                
            self.load_gtms()
            return rx.toast.success("GTM added successfully!")
            
        except Exception as e:
            print(f"Database error: {e}")
            return rx.toast.error(f"Failed to save GTM: {str(e)}")

    def get_gtm(self, gtm: Intervention):
        """Set the current GTM for editing.
        
        Args:
            gtm: The intervention to edit
        """
        self.current_gtm = gtm

    def update_gtm(self, form_data: dict):
        """Update existing GTM in database.
        
        Args:
            form_data: Dictionary containing updated intervention data
        """
        try:
            # Convert numeric fields
            form_data["InitialORate"] = float(form_data.get("InitialORate", 0))
            form_data["bo"] = float(form_data.get("bo", 0))
            form_data["Dio"] = float(form_data.get("Dio", 0))
            form_data["InitialLRate"] = float(form_data.get("InitialLRate", 0))
            form_data["bl"] = float(form_data.get("bl", 0))
            form_data["Dil"] = float(form_data.get("Dil", 0))
            
            with rx.session() as session:
                gtm_to_update = session.exec(
                    Intervention.select().where(
                        Intervention.UniqueId == self.current_gtm.UniqueId
                    )
                ).first()
                
                if gtm_to_update:
                    # Update all fields except UniqueId (primary key)
                    gtm_to_update.Field = form_data.get("Field", gtm_to_update.Field)
                    gtm_to_update.Platform = form_data.get("Platform", gtm_to_update.Platform)
                    gtm_to_update.Reservoir = form_data.get("Reservoir", gtm_to_update.Reservoir)
                    gtm_to_update.TypeGTM = form_data.get("TypeGTM", gtm_to_update.TypeGTM)
                    gtm_to_update.PlanningDate = form_data.get("PlanningDate", gtm_to_update.PlanningDate)
                    gtm_to_update.Status = form_data.get("Status", gtm_to_update.Status)
                    gtm_to_update.InitialORate = form_data["InitialORate"]
                    gtm_to_update.bo = form_data["bo"]
                    gtm_to_update.Dio = form_data["Dio"]
                    gtm_to_update.InitialLRate = form_data["InitialLRate"]
                    gtm_to_update.bl = form_data["bl"]
                    gtm_to_update.Dil = form_data["Dil"]
                    
                    session.add(gtm_to_update)
                    session.commit()
                    
            self.load_gtms()
            return rx.toast.success("GTM updated successfully!")
            
        except Exception as e:
            print(f"Update error: {e}")
            return rx.toast.error(f"Failed to update GTM: {str(e)}")

    def delete_gtm(self, unique_id: str):
        """Delete GTM from database.
        
        Args:
            unique_id: The UniqueId of the intervention to delete
        """
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
        """Transform GTM type data into a format suitable for visualization.
        
        Creates data for bar chart showing distribution of GTM types.
        """
        type_counts = Counter(gtm.TypeGTM for gtm in self.GTM)
        self.gtms_for_graph = [
            {"name": gtm_group, "value": count}
            for gtm_group, count in type_counts.items()
        ]
    
    def set_search_query(self, query: str):
        """Set search query for filtering interventions."""
        self.search_query = query
    
    def set_selected_field(self, field: str):
        """Set field filter."""
        self.selected_field = field
    
    def set_selected_status(self, status: str):
        """Set status filter."""
        self.selected_status = status
    
    @rx.var
    def filtered_gtms(self) -> list[Intervention]:
        """Get filtered list of interventions based on search criteria."""
        result = self.GTM
        
        if self.search_query:
            query = self.search_query.lower()
            result = [
                gtm for gtm in result 
                if query in gtm.UniqueId.lower() or 
                   query in gtm.Field.lower() or
                   query in gtm.Platform.lower()
            ]
        
        if self.selected_field:
            result = [gtm for gtm in result if gtm.Field == self.selected_field]
        
        if self.selected_status:
            result = [gtm for gtm in result if gtm.Status == self.selected_status]
        
        return result
    
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
        return sum(1 for gtm in self.GTM if gtm.Status == "Completed")
