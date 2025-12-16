"""Database models for Well Intervention Management."""
import reflex as rx
import sqlmodel
import sqlalchemy as sa
from datetime import datetime


class Intervention(rx.Model, table=True):
    """The intervention ID information - stores well intervention records."""
    __tablename__ = "InterventionID"
    
    UniqueId: str = sqlmodel.Field(primary_key=True,max_length=255)
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
    
    UniqueId: str = sqlmodel.Field(primary_key=True,max_length=255)
    Date: datetime = sqlmodel.Field(primary_key=True)
    OilRate: float      # Oil production rate (bbl/day)
    OilProd: float      # Cumulative oil production (bbl)
    LiqRate: float      # Liquid production rate (bbl/day)
    LiqProd: float      # Cumulative liquid production (bbl)
    WC: float           # Water cut (%)

class HistoryProd(rx.Model,table=True):
    __tablename__="HistoryProd"
    UniqueId: str = sqlmodel.Field(primary_key=True,max_length=255)
    Date : datetime = sqlmodel.Field(primary_key=True)
    Dayon : float
    Method: str
    Qoil:float
    Qgas:float
    Qwater:float
    GOR:float
    ChokeSize:float
    Press_WH:float
    Oilrate:float
    Liqrate:float
    Gasrate:float
    Note:str
class Master(rx.Model,table=True):
    __tablename__="Master"
    UniqueId:str=sqlmodel.Field(primary_key=True,max_length=255)
    Wellname:str
    X_top:float
    Y_top:float
    X_bot:float
    Y_bot:float
    

# Field options for dropdown selections
FIELD_OPTIONS = [
    "BACHHO", "RONG", "RONG_GAS", "NR-DOIMOI", 
    "GAUTRANG", "THOTRANG", "KINHNGU", "CATAM"
]

# Platform options
PLATFORM_OPTIONS = [
    "MSP-01", "MSP-02", "MSP-03", "MSP-04", 
    "MSP-05", "MSP-06", "MSP-07","MSP-08","MSP-09","MSP-10","MSP-11",
    "BK-01","BK-03","BK-04","BK-04A","BK-05","BK-06","BK-07","BK-08","BK-09","BK-10",
    "BK-14","BK-15","BK-16","BK-17","BK-18A","BK-19","BK-20","BK-21","BK-22","BK-23","BK-24","BK-25","BK-26","BT-07",
    "GTC-01","RC-04","RC-DM","RC-01","RC-02","RC-05","RC-06","RC-08","RC-09","RC-10","RC-11","RC-12","RC-RB1",'RP-01',"RP-02","RP-03",
    "ThTC-01","ThTC-02","ThTC-03","WHP-KTN","CPP-KNT","CTC-01","CTC-02"
]

# Reservoir options
RESERVOIR_OPTIONS = [
    "Lower Miocene","Middle Miocene", "Oligocene C", "Upper Oligocene", 
    "Lower Oligocene", "Basement"
]

# GTM Type options (Russian abbreviations for well interventions)
GTM_TYPE_OPTIONS = [
    "ВНС",
    "ГРП",   # Hydraulic Fracturing
    "ПВЛГ",  # Perforation 
    "УЭЦН",  # ESP (Electric Submersible Pump)
    "ЗБС" ,   # Sidetrack
    "РИР",
    "ОПЗ",
    "ПВР (через НКТ)",
    "TPO",
    "Смена ВСО",
    "Перевод в добычу из ППД",
    "Нормализация забоя",
]

# Status options
STATUS_OPTIONS = ["Plan", "Done", "Cancelled"]
