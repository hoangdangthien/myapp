"""Database models for Well Intervention Management."""
import reflex as rx
import sqlmodel
import sqlalchemy as sa
from datetime import datetime


class Intervention(rx.Model, table=True):
    """The intervention ID information - stores well intervention records."""
    __tablename__ = "InterventionID"
    
    UniqueId: str = sqlmodel.Field(primary_key=True, max_length=255)
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
    """The intervention production information - stores production history and forecasts.
    
    Version field:
        - 0: Actual production data
        - 1, 2, 3: Forecast versions (FIFO - max 3 versions kept)
    
    DataType field:
        - "Actual": Real production measurements
        - "Forecast": Predicted values from Arps decline model
    """
    __tablename__ = "InterventionProd"
    
    UniqueId: str = sqlmodel.Field(primary_key=True, max_length=255)
    Date: datetime = sqlmodel.Field(primary_key=True)
    Version: int = sqlmodel.Field(default=0, primary_key=True)
    OilRate: float      # Oil production rate (bbl/day)
    OilProd: float      # Cumulative oil production (bbl)
    LiqRate: float      # Liquid production rate (bbl/day)
    LiqProd: float      # Cumulative liquid production (bbl)
    WC: float           # Water cut (%)
    CreatedAt: datetime = sqlmodel.Field(default_factory=datetime.now)


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
    Oilrate: float
    Liqrate: float
    Gasrate: float
    Note: str


class Master(rx.Model, table=True):
    __tablename__ = "Master"
    UniqueId: str = sqlmodel.Field(primary_key=True, max_length=255)
    Wellname: str
    X_top: float
    Y_top: float
    X_bot: float
    Y_bot: float
    

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
    "Infill well",           # ВНС - Ввод новой скважины
    "Hydraulic Fracturing",      # ГРП - Гидроразрыв пласта
    "Perforation",               # ПВЛГ - Перфорация
    "ESP Installation",          # УЭЦН - Установка ЭЦН
    "Sidetrack",                 # ЗБС - Зарезка бокового ствола
    "Workover",                  # РИР - Ремонтно-изоляционные работы
    "Stimulation",               # ОПЗ - Обработка призабойной зоны
    "Perforation Through Tubing", # ПВР (через НКТ)
    "Routine Maintenance",       # TPO - Текущий подземный ремонт
    "Equipment Change",          # Смена ВСО
    "Injection to Production",   # Перевод в добычу из ППД
    "Bottomhole Normalization",  # Нормализация забоя
    "Acidizing",                 # Кислотная обработка
    "Sand Control",              # Противопесочные мероприятия
]

# Status options
STATUS_OPTIONS = ["Plan", "Done", "Cancelled"]


# Mapping between Russian and English GTM types (for migration/reference)
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