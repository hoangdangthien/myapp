"""Database models for Well Intervention Management."""
import reflex as rx
import sqlmodel


class Intervention(rx.Model, table=True):
    """The intervention ID information - stores well intervention records."""
    __tablename__ = "InterventionID"
    
    UniqueId: str = sqlmodel.Field(primary_key=True)
    Field: str
    Platform: str
    Reservoir: str
    TypeGTM: str
    PlanningDate: str
    Status: str
    InitialORate: float  # Initial Oil Rate (bbl/day)
    bo: float            # Arps decline parameter b for oil
    Dio: float           # Initial decline rate for oil
    InitialLRate: float  # Initial Liquid Rate (bbl/day)
    bl: float            # Arps decline parameter b for liquid
    Dil: float           # Initial decline rate for liquid


class InterventionProd(rx.Model, table=True):
    """The intervention production information - stores production history."""
    __tablename__ = "InterventionProd"
    
    UniqueId: str = sqlmodel.Field(primary_key=True)
    Date: str = sqlmodel.Field(primary_key=True)
    OilRate: float      # Oil production rate (bbl/day)
    OilProd: float      # Cumulative oil production (bbl)
    LiqRate: float      # Liquid production rate (bbl/day)
    LiqProd: float      # Cumulative liquid production (bbl)
    WC: float           # Water cut (%)


# Field options for dropdown selections
FIELD_OPTIONS = [
    "BACHHO", "RONG", "RONG_GAS", "NR-DOIMOI", 
    "GAUTRANG", "THOTRANG", "KINHNGU", "CATAM"
]

# Platform options
PLATFORM_OPTIONS = [
    "MSP-01", "MSP-02", "MSP-03", "MSP-04", 
    "MSP-05", "MSP-06", "MSP-07"
]

# Reservoir options
RESERVOIR_OPTIONS = [
    "Lower Miocene", "Oligocene C", "Upper Oligocene", 
    "Lower Oligocene", "Basement"
]

# GTM Type options (Russian abbreviations for well interventions)
GTM_TYPE_OPTIONS = [
    "ГРП",   # Hydraulic Fracturing
    "ПВЛГ",  # Perforation 
    "ГРП",   # Hydraulic Fracturing
    "УЭЦН",  # ESP (Electric Submersible Pump)
    "ЗБС"    # Sidetrack
]

# Status options
STATUS_OPTIONS = ["Plan", "In Progress", "Completed", "Cancelled"]
