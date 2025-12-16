import reflex as rx
import urllib
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MSSQL Connection Configuration from environment
server = os.getenv('MSSQL_SERVER', '')
database = os.getenv('MSSQL_NAME', '')
username = os.getenv('MSSQL_USER', '')
password = os.getenv('MSSQL_PASSWORD', '')
driver = os.getenv('MSSQL_DRIVER', 'ODBC Driver 17 for SQL Server')

# Build connection string
conn = f"""Driver={{{driver}}};Server={server};Database={database};Uid={username};Pwd={password};Encrypt=yes;TrustServerCertificate=yes;"""

# URL encode the connection string
params = urllib.parse.quote_plus(conn)

# Create connection string with autocommit
db_url = f'mssql+pyodbc:///?autocommit=true&charset=utf8mb4&odbc_connect={params}'

config = rx.Config(
    app_name="production",
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ],
    db_url=db_url,
)

"""config = rx.Config(
    app_name="production",
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ],
    db_url="sqlite:///Production.db",
)"""
