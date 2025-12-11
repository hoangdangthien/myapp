# GTM Dashboard - Well Intervention Management

A production analysis dashboard for monitoring production data and evaluating well intervention activities in oil & gas operations. Built with Reflex (Python web framework).

## Features

- **Production Monitoring** (Planned)
  - Real-time production rate monitoring
  - Decline curve analysis (DCA)
  - Production forecasting with Arps model
  - Field and well-level aggregation

- **Well Intervention (GTM) Management**
  - CRUD operations for intervention records
  - Intervention type tracking (ГРП, ПВЛГ, УЭЦН, ЗБС, etc.)
  - Status tracking (Plan, In Progress, Completed)
  - Decline curve parameters (Initial rates, b, Di)
  - Data visualization with charts

## Project Structure

```
├── rxconfig.py              # Reflex configuration
├── requirements.txt         # Python dependencies
└── gtm_app/
    ├── __init__.py
    ├── gtm_app.py           # Main application entry point
    ├── models.py            # Database models (Intervention, InterventionProd)
    ├── styles.py            # Global styles and theme
    ├── components/          # Reusable UI components
    │   ├── __init__.py
    │   ├── sidebar.py       # Navigation sidebar
    │   ├── form_fields.py   # Reusable form inputs
    │   ├── gtm_dialogs.py   # Add/Edit/Delete dialogs
    │   ├── gtm_table.py     # Data table component
    │   └── gtm_charts.py    # Visualization components
    ├── pages/               # Application pages
    │   ├── __init__.py
    │   ├── production.py    # Production monitoring page
    │   └── well_intervention.py  # GTM management page
    ├── states/              # State management
    │   ├── __init__.py
    │   ├── base_state.py    # Common app state
    │   └── gtm_state.py     # Well intervention state
    └── templates/           # Page layout templates
        ├── __init__.py
        └── template.py      # Template decorator
```

## Installation

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Initialize and run the app:
```bash
reflex init
reflex run
```

4. Open your browser at http://localhost:3000

## Database

The application uses SQLite with the database file `Production.db`. The database contains two tables:

- **InterventionID**: Stores well intervention records with decline curve parameters
- **InterventionProd**: Stores production history data

## Technology Stack

- **Reflex**: Python web framework for full-stack apps
- **SQLModel**: SQL database ORM
- **Pandas/NumPy/SciPy**: Data analysis and forecasting
- **Recharts**: Data visualization

## Usage

### Adding a New Intervention

1. Navigate to "Well Intervention" page
2. Click "Add Well Intervention" button
3. Fill in the form with:
   - UniqueId: Unique identifier for the well
   - Field, Platform, Reservoir: Location details
   - Type GTM: Intervention type
   - Planning Date and Status
   - Decline curve parameters (Initial rates, b, Di)
4. Click "Submit"

### Editing/Deleting Interventions

- Click the pencil icon to edit an intervention
- Click the trash icon to delete an intervention

## Future Enhancements

- [ ] Production monitoring with real-time data
- [ ] Decline curve analysis (Arps, harmonic, hyperbolic)
- [ ] Production forecasting
- [ ] Export to Excel/PDF
- [ ] Multi-user authentication
- [ ] API integration for external data sources
