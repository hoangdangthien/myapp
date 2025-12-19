"""Database models for Well Intervention Management."""
import reflex as rx
import sqlmodel
import sqlalchemy as sa
from datetime import datetime


class Intervention(rx.Model, table=True):
    """The intervention ID information - stores well intervention records."""
    __tablename__ = "InterventionID"
    ID : int = sqlmodel.Field(primary_key=True)
    UniqueId: str 
    Field: str
    Platform: str
    Reservoir: str
    TypeGTM: str
    Category: str        #using drilling platform, not using platform
    PlanningDate: str
    Status: str
    InitialORate: float  # Initial Oil Rate (bbl/day)
    bo: float            # Arps decline parameter b for oil
    Dio: float           # Initial decline rate for oil
    InitialLRate: float  # Initial Liquid Rate (bbl/day)
    bl: float            # Arps decline parameter b for liquid
    Dil: float           # Initial decline rate for liquid
    Describe : str       # Describe Intervention activity


class InterventionForecast(rx.Model, table=True):
    """The intervention production information - stores production history and forecasts.
    
    Version field:
        - 0: Base case forecast from the last record of history before Intervention date and cannot delete by button
        - 1, 2, 3: Forecast versions (FIFO - max 3 versions kept)
    
    DataType field:
        - "Actual": Real production measurements
        - "Forecast": Predicted values from Arps decline model
    """
    __tablename__ = "InterventionForecast"
    
    UniqueId: str = sqlmodel.Field(primary_key=True, max_length=255)
    Date: datetime = sqlmodel.Field(primary_key=True)
    Version: int = sqlmodel.Field(default=0, primary_key=True)
    DataType: str = sqlmodel.Field(default="Forecast")
    OilRate: float      # Oil production rate (ton/day)
    LiqRate: float      # Liquid production rate (ton/day)
    Qoil: float      # Cumulative oil production in month (ton) : OilProd = K_int*Dayon*OilRate
    Qliq: float      # Cumulative liquid production in month (ton): LiqProd = K_int*Dayon*LiqRate
    WC: float           # Water cut (%) = (Qliq-Qoil)/Qliq*100
    CreatedAt: datetime = sqlmodel.Field(default_factory=datetime.now)


class CompletionID(rx.Model, table=True):
    __tablename__ = "CompletionID"
    UniqueId: str = sqlmodel.Field(primary_key=True, max_length=255)
    WellName: str 
    X_top: float
    Y_top: float
    Z_top :float
    X_bot: float
    Y_bot: float
    Z_bot : float
    Reservoir : str
    Completion: str
    KH : float
    Do : float  # Di for Exponential DCA for oil phase
    Dl : float # Di for Exponential DCA for liquid phase


class WellID(rx.Model,table=True):
    __tablename__ = "WellID"
    WellName : str = sqlmodel.Field(primary_key=True,max_length=255)
    X_coord : float
    Y_coord : float
    Platform : str
    Region : str
    Field : str
    Block : str
    VSPShare : float
    WellCategory : str      #OIL,GAS,COND,INJ
    WellStatus : str        #Working, Abandone        


class HistoryProd(rx.Model, table=True):
    __tablename__ = "HistoryProd"
    UniqueId: str = sqlmodel.Field(primary_key=True, max_length=255)
    Date: datetime = sqlmodel.Field(primary_key=True)
    Dayon: float
    Method: str
    Qoil: float
    Qgas: float
    Qwater: float
    GOR: float
    ChokeSize: float
    Press_WH: float
    OilRate: float
    LiqRate: float
    GasRate: float
    Note: str


class ProductionForecast(rx.Model, table=True):
    """Production forecast table for storing DCA forecasts.
    
    Version field:
        - 1, 2, 3, 4: Forecast versions (FIFO - max 4 versions kept)
    """
    __tablename__ = "ProductionForecast"
    UniqueId: str = sqlmodel.Field(primary_key=True, max_length=255)
    Date: datetime = sqlmodel.Field(primary_key=True)
    Version: int = sqlmodel.Field(default=1, primary_key=True)
    OilRate: float
    LiqRate: float
    Qoil: float         # Cumulative oil in month Qoil = K_oil*Dayon*Oilrate
    Qliq: float         # Cumulative liquid in month Qliq = K_liq*Dayon*Liqrate
    WC: float           # WC = (Qliq-Qoil)/Qoil*100
    CreatedAt: datetime = sqlmodel.Field(default_factory=datetime.now)


class KMonth(rx.Model, table=True):
    __tablename__ = "KMonth"
    MonthID: int = sqlmodel.Field(primary_key=True)
    K_oil: float        #uptime for oil phase
    K_liq: float        #uptime for liquid phase
    K_int : float       #uptime for intervention
    K_inj : float       #uptime for injection


# Field options for dropdown selections
FIELD_OPTIONS = [
    "BACHHO", "RONG", "RONG_GAS", "NR-DOIMOI", 
    "GAUTRANG", "THOTRANG", "KINHNGU", "CATAM"
]

# Platform options
PLATFORM_OPTIONS = [
    "MSP-01", "MSP-02", "MSP-03", "MSP-04", 
    "MSP-05", "MSP-06", "MSP-07", "MSP-08", "MSP-09", "MSP-10", "MSP-11",
    "BK-01", "BK-03", "BK-04", "BK-04A", "BK-05", "BK-06", "BK-07", "BK-08", "BK-09", "BK-10",
    "BK-14", "BK-15", "BK-16", "BK-17", "BK-18A", "BK-19", "BK-20", "BK-21", "BK-22", "BK-23", 
    "BK-24", "BK-25", "BK-26", "BT-07",
    "GTC-01", "RC-04", "RC-DM", "RC-01", "RC-02", "RC-05", "RC-06", "RC-08", "RC-09", "RC-10", 
    "RC-11", "RC-12", "RC-RB1", 'RP-01', "RP-02", "RP-03",
    "ThTC-01", "ThTC-02", "ThTC-03", "WHP-KTN", "CPP-KNT", "CTC-01", "CTC-02"
]

# Reservoir options
RESERVOIR_OPTIONS = [
    "Lower Miocene", "Middle Miocene", "Oligocene C", "Upper Oligocene", 
    "Lower Oligocene", "Basement"
]

# GTM Type options - English well intervention types
GTM_TYPE_OPTIONS = [
    "Infill well",
    "Hydraulic Fracturing",
    "Perforation",
    "ESP Installation",
    "Sidetrack",
    "Workover",
    "Stimulation",
    "Perforation Through Tubing",
    "Routine Maintenance",
    "Equipment Change",
    "Injection to Production",
    "Bottomhole Normalization",
    "Acidizing",
    "Sand Control",
]
GTM_CATEGORY_OPTIONS = [
    "Using drilling Platform",
    "Not using drilling Platform"
]
# Status options
STATUS_OPTIONS = ["Plan", "Done", "Cancelled"]

# GTM Type mapping for reference
GTM_TYPE_MAPPING = {
    "ВНС": "Well Completion",
    "ГРП": "Hydraulic Fracturing",
    "ПВЛГ": "Perforation",
    "УЭЦН": "ESP Installation",
    "ЗБС": "Sidetrack",
    "РИР": "Workover",
    "ОПЗ": "Stimulation",
    "ПВР (через НКТ)": "Perforation Through Tubing",
    "TPO": "Routine Maintenance",
    "Смена ВСО": "Equipment Change",
    "Перевод в добычу из ППД": "Injection to Production",
    "Нормализация забоя": "Bottomhole Normalization",
}

MAX_FORECAST_VERSIONS = 3
MAX_PRODUCTION_FORECAST_VERSIONS = 4  # For ProductionForecast table