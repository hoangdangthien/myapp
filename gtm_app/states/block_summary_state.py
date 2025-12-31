"""Block Summary State for Block 09-1 Production Summary.

Aggregates production forecast data by intervention category for Block 09-1.
Categories:
- Carryover wells (Quỹ giếng chuyển tiếp)
- New wells (Quỹ giếng mới / Infill)
- Sidetrack wells (Quỹ giếng cắt thân)
- Reservoir conversion (Quỹ giếng chuyển đổi tượng)
- Hydraulic fracturing (Nứt vỉa thủy lực)
- ESP pumps (Bơm điện chìm)
- Other workover solutions (Các giải pháp ĐC-KT khác)

Mapping from GTM_TYPE_OPTIONS to categories:
- "Infill well" → New wells
- "Sidetrack" → Sidetrack wells
- "Hydraulic Fracturing" → Hydraulic fracturing
- "ESP Installation" → ESP pumps
- "Injection to Production" → Reservoir conversion
- Others → Other workover
"""
import reflex as rx
from typing import List, Dict, Optional, Any
from datetime import datetime
from sqlmodel import select
import pandas as pd
import numpy as np
import io

from ..models import (
    InterventionID,
    InterventionForecast,
    CompletionID,
    ProductionForecast,
    HistoryProd,
)


# Category mapping for intervention types
GTM_TO_CATEGORY_MAP = {
    "Infill well": "new_wells",
    "Sidetrack": "sidetrack",
    "Hydraulic Fracturing": "hydraulic_frac",
    "ESP Installation": "esp",
    "Injection to Production": "reservoir_conversion",
    "Perforation": "other",
    "Workover": "other",
    "Stimulation": "other",
    "Perforation Through Tubing": "other",
    "Routine Maintenance": "other",
    "Equipment Change": "other",
    "Bottomhole Normalization": "other",
    "Acidizing": "other",
    "Sand Control": "other",
}

CATEGORY_LABELS = {
    "carryover": "Sản lượng theo quỹ giếng chuyển tiếp",
    "new_wells": "Sản lượng theo quỹ giếng mới",
    "sidetrack": "Sản lượng theo quỹ giếng cắt thân",
    "reservoir_conversion": "Sản lượng theo quỹ giếng chuyển đổi tượng",
    "hydraulic_frac": "Sản lượng từ nứt vỉa thủy lực",
    "esp": "Sản lượng từ bơm điện chìm",
    "other": "Sản lượng từ các giải pháp ĐC-KT khác",
}

CATEGORY_COLORS = {
    "carryover": "white",
    "new_wells": "yellow",
    "sidetrack": "cyan",
    "reservoir_conversion": "orange",
    "hydraulic_frac": "green",
    "esp": "purple",
    "other": "pink",
}

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", 
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


class BlockSummaryState(rx.State):
    """State for Block 09-1 production summary with category breakdown."""
    
    # Year selection
    current_year: int = datetime.now().year
    next_year: int = datetime.now().year + 1
    selected_current_year: int = datetime.now().year
    selected_next_year: int = datetime.now().year + 1
    
    # Phase selection (oil or liquid)
    selected_phase: str = "oil"
    is_oil_phase: bool = True
    
    # Technical loss factor (%)
    technical_loss_percent: float = 0.0
    
    # Loading state
    is_loading: bool = False
    
    # Summary data for current year (Table 1)
    current_year_summary: List[dict] = []
    
    # Summary data for next year (Table 2)
    next_year_summary: List[dict] = []
    
    # Detailed breakdown table (Table 3 - like the image)
    detailed_summary: List[dict] = []
    
    # Chart data - store as dict for proper serialization
    block_chart_data: Dict[str, Any] = {}
    
    # Computed properties
    @rx.var
    def current_year_total_q(self) -> float:
        """Total Q for current year."""
        if not self.current_year_summary:
            return 0.0
        total_row = next((r for r in self.current_year_summary if r.get("category") == "total"), None)
        return total_row.get("Total", 0.0) if total_row else 0.0
    
    @rx.var
    def next_year_total_q(self) -> float:
        """Total Q for next year."""
        if not self.next_year_summary:
            return 0.0
        total_row = next((r for r in self.next_year_summary if r.get("category") == "total"), None)
        return total_row.get("Total", 0.0) if total_row else 0.0
    
    @rx.var
    def available_years(self) -> List[str]:
        """List of available years for selection."""
        return [str(y) for y in range(2024, 2051)]
    
    # Event handlers
    def set_selected_phase(self, phase: str):
        """Set selected phase and reload data."""
        self.selected_phase = phase
        self.is_oil_phase = phase == "oil"
        self.load_block_summary()
    
    def set_current_year(self, year: str):
        """Set current year for Table 1."""
        self.selected_current_year = int(year)
        self.load_block_summary()
    
    def set_next_year(self, year: str):
        """Set next year for Table 2."""
        self.selected_next_year = int(year)
        self.load_block_summary()
    
    def set_technical_loss(self, value: str):
        """Set technical loss percentage."""
        try:
            self.technical_loss_percent = float(value)
        except ValueError:
            self.technical_loss_percent = 0.0
        self.load_block_summary()
    
    def load_block_summary(self):
        """Load and aggregate production data by category."""
        self.is_loading = True
        
        try:
            with rx.session() as session:
                # Determine which field to use based on phase
                q_field = "Qoil" if self.is_oil_phase else "Qliq"
                rate_field = "OilRate" if self.is_oil_phase else "LiqRate"
                
                # ===== Load Carryover (Base Production from CompletionID) =====
                carryover_data = self._load_carryover_production(
                    session, q_field, self.selected_current_year, self.selected_next_year
                )
                
                # ===== Load Intervention Production =====
                intervention_data = self._load_intervention_production(
                    session, q_field, self.selected_current_year, self.selected_next_year
                )
                
                # ===== Build Summary Tables =====
                self.current_year_summary = self._build_summary_table(
                    carryover_data.get("current_year", {}),
                    intervention_data.get("current_year", {}),
                    self.selected_current_year
                )
                
                self.next_year_summary = self._build_summary_table(
                    carryover_data.get("next_year", {}),
                    intervention_data.get("next_year", {}),
                    self.selected_next_year
                )
                
                # ===== Build Detailed Summary (Table 3) =====
                self.detailed_summary = self._build_detailed_summary(
                    carryover_data, intervention_data
                )
                
                
        except Exception as e:
            print(f"Error loading block summary: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.is_loading = False
    
    def _load_carryover_production(
        self, session, q_field: str, year1: int, year2: int
    ) -> Dict:
        """Load production from carryover wells (base production without intervention)."""
        result = {
            "current_year": {m: 0.0 for m in range(1, 13)},
            "next_year": {m: 0.0 for m in range(1, 13)},
        }
        
        # Load ProductionForecast data for completions
        query = select(ProductionForecast).where(
            ProductionForecast.Version >= 1
        )
        forecasts = session.exec(query).all()
        
        # Group by UniqueId and get latest version
        forecast_by_id: Dict[str, Dict[int, List]] = {}
        for rec in forecasts:
            uid = rec.UniqueId
            ver = rec.Version
            if uid not in forecast_by_id:
                forecast_by_id[uid] = {}
            if ver not in forecast_by_id[uid]:
                forecast_by_id[uid][ver] = []
            forecast_by_id[uid][ver].append(rec)
        
        # Get list of UniqueIds that have interventions this year
        intervention_query = select(InterventionID.UniqueId).where(
            InterventionID.InterventionYear.in_([year1, year2])
        ).distinct()
        intervention_ids = set(session.exec(intervention_query).all())
        
        # Sum up production from completions WITHOUT interventions
        for uid, versions in forecast_by_id.items():
            if uid in intervention_ids:
                continue  # Skip wells with interventions
            
            if not versions:
                continue
            
            latest_ver = max(versions.keys())
            records = versions[latest_ver]
            
            for rec in records:
                rec_date = rec.Date if isinstance(rec.Date, datetime) else datetime.strptime(str(rec.Date), "%Y-%m-%d")
                rec_year = rec_date.year
                rec_month = rec_date.month
                
                q_value = getattr(rec, q_field, 0) or 0.0
                q_value = q_value / 1000  # Convert to thousand tons
                
                if rec_year == year1:
                    result["current_year"][rec_month] += q_value
                elif rec_year == year2:
                    result["next_year"][rec_month] += q_value
        
        return result
    
    def _load_intervention_production(
        self, session, q_field: str, year1: int, year2: int
    ) -> Dict:
        """Load production from intervention wells, grouped by category."""
        # Initialize result structure
        categories = list(GTM_TO_CATEGORY_MAP.values())
        result = {
            "current_year": {cat: {m: 0.0 for m in range(1, 13)} for cat in set(categories)},
            "next_year": {cat: {m: 0.0 for m in range(1, 13)} for cat in set(categories)},
        }
        
        # Load all interventions
        intv_query = select(InterventionID)
        interventions = session.exec(intv_query).all()
        
        # Map intervention ID to category
        intv_id_to_category = {}
        for intv in interventions:
            category = GTM_TO_CATEGORY_MAP.get(intv.TypeGTM, "other")
            intv_id_to_category[intv.ID] = category
        
        # Load InterventionForecast data
        forecast_query = select(InterventionForecast).where(
            InterventionForecast.Version >= 1
        )
        forecasts = session.exec(forecast_query).all()
        
        # Group by ID and get latest version
        forecast_by_id: Dict[int, Dict[int, List]] = {}
        for rec in forecasts:
            intv_id = rec.ID
            ver = rec.Version
            if intv_id not in forecast_by_id:
                forecast_by_id[intv_id] = {}
            if ver not in forecast_by_id[intv_id]:
                forecast_by_id[intv_id][ver] = []
            forecast_by_id[intv_id][ver].append(rec)
        
        # Sum up production by category
        for intv_id, versions in forecast_by_id.items():
            if intv_id not in intv_id_to_category:
                continue
            
            category = intv_id_to_category[intv_id]
            
            if not versions:
                continue
            
            latest_ver = max(versions.keys())
            records = versions[latest_ver]
            
            for rec in records:
                rec_date = rec.Date if isinstance(rec.Date, datetime) else datetime.strptime(str(rec.Date), "%Y-%m-%d")
                rec_year = rec_date.year
                rec_month = rec_date.month
                
                q_value = getattr(rec, q_field, 0) or 0.0
                q_value = q_value / 1000  # Convert to thousand tons
                
                if rec_year == year1 and category in result["current_year"]:
                    result["current_year"][category][rec_month] += q_value
                elif rec_year == year2 and category in result["next_year"]:
                    result["next_year"][category][rec_month] += q_value
        
        return result
    
    def _build_summary_table(
        self, carryover: Dict, intervention_data: Dict, year: int
    ) -> List[dict]:
        """Build summary table with category breakdown."""
        rows = []
        
        # Category order
        category_order = [
            "carryover", "new_wells", "sidetrack", "reservoir_conversion",
            "hydraulic_frac", "esp", "other"
        ]
        
        # Totals for intervention gains
        intervention_totals = {m: 0.0 for m in range(1, 13)}
        grand_totals = {m: 0.0 for m in range(1, 13)}
        
        # Add carryover row
        carryover_row = {
            "category": "carryover",
            "label": CATEGORY_LABELS["carryover"],
            "color": CATEGORY_COLORS["carryover"],
        }
        for i, m_name in enumerate(MONTH_NAMES, 1):
            val = round(carryover.get(i, 0.0), 3)
            carryover_row[m_name] = val
            grand_totals[i] += val
        carryover_row["Total"] = round(sum(carryover.get(m, 0.0) for m in range(1, 13)), 3)
        rows.append(carryover_row)
        
        # Add intervention category rows
        for cat in category_order[1:]:  # Skip carryover
            cat_data = intervention_data.get(cat, {})
            row = {
                "category": cat,
                "label": CATEGORY_LABELS.get(cat, cat),
                "color": CATEGORY_COLORS.get(cat, "gray"),
            }
            for i, m_name in enumerate(MONTH_NAMES, 1):
                val = round(cat_data.get(i, 0.0), 3)
                row[m_name] = val
                intervention_totals[i] += val
                grand_totals[i] += val
            row["Total"] = round(sum(cat_data.get(m, 0.0) for m in range(1, 13)), 3)
            rows.append(row)
        
        # Add intervention subtotal row
        intv_subtotal_row = {
            "category": "intervention_total",
            "label": "Tổng sản lượng dầu gia tăng từ giải pháp ĐC-KT",
            "color": "blue",
        }
        for i, m_name in enumerate(MONTH_NAMES, 1):
            intv_subtotal_row[m_name] = round(intervention_totals[i], 3)
        intv_subtotal_row["Total"] = round(sum(intervention_totals.values()), 3)
        rows.append(intv_subtotal_row)
        
        # Add grand total row (before technical loss)
        total_row = {
            "category": "total",
            "label": "Tổng lưu lượng dầu, t/ngày" if "Rate" in self.selected_phase else "Tổng sản lượng dầu, ng.tấn",
            "color": "green",
        }
        for i, m_name in enumerate(MONTH_NAMES, 1):
            total_row[m_name] = round(grand_totals[i], 3)
        total_row["Total"] = round(sum(grand_totals.values()), 3)
        rows.append(total_row)
        
        # Add technical loss row
        loss_factor = self.technical_loss_percent / 100.0
        loss_row = {
            "category": "tech_loss",
            "label": "Hao hụt kỹ thuật, ng.tấn",
            "color": "red",
        }
        for i, m_name in enumerate(MONTH_NAMES, 1):
            loss_row[m_name] = round(grand_totals[i] * loss_factor, 3)
        loss_row["Total"] = round(sum(grand_totals.values()) * loss_factor, 3)
        rows.append(loss_row)
        
        # Add net total (after technical loss)
        net_row = {
            "category": "net_total",
            "label": "Tổng sản lượng dầu sau hao hụt kỹ thuật",
            "color": "darkgreen",
        }
        for i, m_name in enumerate(MONTH_NAMES, 1):
            net_row[m_name] = round(grand_totals[i] * (1 - loss_factor), 3)
        net_row["Total"] = round(sum(grand_totals.values()) * (1 - loss_factor), 3)
        rows.append(net_row)
        
        return rows
    
    def _build_detailed_summary(
        self, carryover_data: Dict, intervention_data: Dict
    ) -> List[dict]:
        """Build detailed summary table matching the image format."""
        rows = []
        year = self.selected_next_year
        
        # Build rows similar to the Excel image structure
        category_order = [
            ("carryover", "Sản lượng theo quỹ giếng chuyển tiếp"),
            ("new_wells", "Sản lượng theo quỹ giếng mới"),
            ("sidetrack", "Sản lượng theo quỹ giếng cắt thân"),
            ("reservoir_conversion", "Sản lượng theo quỹ giếng chuyển đổi tượng"),
            ("hydraulic_frac", "Sản lượng từ nứt vỉa thủy lực"),
            ("esp", "Sản lượng từ bơm điện chìm"),
            ("other", "Sản lượng từ các giải pháp ĐC-KT khác"),
        ]
        
        next_year_carryover = carryover_data.get("next_year", {})
        next_year_intv = intervention_data.get("next_year", {})
        
        grand_totals = {m: 0.0 for m in range(1, 13)}
        intv_totals = {m: 0.0 for m in range(1, 13)}
        
        for cat_key, cat_label in category_order:
            # Header row (category label with color)
            header_row = {
                "row_type": "header",
                "label": cat_label,
                "color": CATEGORY_COLORS.get(cat_key, "white"),
            }
            for m_name in MONTH_NAMES:
                header_row[m_name] = ""
            header_row["Total"] = ""
            rows.append(header_row)
            
            # Data for this category
            if cat_key == "carryover":
                cat_data = next_year_carryover
            else:
                cat_data = next_year_intv.get(cat_key, {})
            
            # Q row (Sản lượng dầu, ng.tấn)
            q_row = {
                "row_type": "data",
                "label": "Sản lượng dầu, ng.tấn",
                "color": "white",
            }
            row_total = 0.0
            for i, m_name in enumerate(MONTH_NAMES, 1):
                val = round(cat_data.get(i, 0.0), 3)
                q_row[m_name] = val
                row_total += val
                grand_totals[i] += val
                if cat_key != "carryover":
                    intv_totals[i] += val
            q_row["Total"] = round(row_total, 3)
            rows.append(q_row)
            
            # Rate row (Tổng lưu lượng dầu, t/ngày) - placeholder
            rate_row = {
                "row_type": "data",
                "label": "Tổng lưu lượng dầu, t/ngày",
                "color": "white",
            }
            for m_name in MONTH_NAMES:
                rate_row[m_name] = 0
            rate_row["Total"] = 0
            rows.append(rate_row)
        
        # Intervention subtotal
        rows.append({
            "row_type": "subtotal",
            "label": "Tổng sản lượng dầu gia tăng từ giải pháp ĐC-KT, ng.tấn",
            "color": "lightblue",
            **{m_name: round(intv_totals[i], 3) for i, m_name in enumerate(MONTH_NAMES, 1)},
            "Total": round(sum(intv_totals.values()), 3),
        })
        
        # Intervention rate subtotal
        rows.append({
            "row_type": "subtotal",
            "label": "Tổng lưu lượng dầu gia tăng từ giải pháp ĐC-KT, t/ngày",
            "color": "lightblue",
            **{m_name: 0 for m_name in MONTH_NAMES},
            "Total": 0,
        })
        
        # Grand totals
        rows.append({
            "row_type": "total",
            "label": "Tổng lưu lượng dầu, t/ngày",
            "color": "yellow",
            **{m_name: 0 for m_name in MONTH_NAMES},
            "Total": 0,
        })
        
        rows.append({
            "row_type": "total",
            "label": "Tổng sản lượng dầu, ng.tấn",
            "color": "yellow",
            **{m_name: round(grand_totals[i], 3) for i, m_name in enumerate(MONTH_NAMES, 1)},
            "Total": round(sum(grand_totals.values()), 3),
        })
        
        # Technical loss
        loss_factor = self.technical_loss_percent / 100.0
        rows.append({
            "row_type": "loss",
            "label": "Hao hụt kỹ thuật, ng.tấn",
            "color": "orange",
            **{m_name: round(grand_totals[i] * loss_factor, 3) for i, m_name in enumerate(MONTH_NAMES, 1)},
            "Total": round(sum(grand_totals.values()) * loss_factor, 3),
        })
        
        # Net production
        rows.append({
            "row_type": "net",
            "label": "Tổng sản lượng dầu sau hao hụt kỹ thuật, ngh.tấn",
            "color": "lightgreen",
            **{m_name: round(grand_totals[i] * (1 - loss_factor) / 1000, 4) for i, m_name in enumerate(MONTH_NAMES, 1)},
            "Total": round(sum(grand_totals.values()) * (1 - loss_factor) / 1000, 4),
        })
        
        # Average daily rate
        rows.append({
            "row_type": "avg",
            "label": "Sản lượng ngày trung bình sau hao hụt kỹ thuật, t/ngày",
            "color": "lightgreen",
            **{m_name: 0 for m_name in MONTH_NAMES},
            "Total": 0,
        })
        
        return rows
    
    
    
    def download_current_year_excel(self):
        """Download current year summary as Excel."""
        return self._download_excel(self.current_year_summary, self.selected_current_year)
    
    def download_next_year_excel(self):
        """Download next year summary as Excel."""
        return self._download_excel(self.next_year_summary, self.selected_next_year)
    
    def download_detailed_excel(self):
        """Download detailed summary as Excel (like the image format)."""
        if not self.detailed_summary:
            return rx.toast.error("No data available")
        
        try:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Convert to DataFrame
                df = pd.DataFrame(self.detailed_summary)
                columns = ["label"] + MONTH_NAMES + ["Total"]
                df = df[columns]
                df.columns = ["Thông số"] + MONTH_NAMES + [str(self.selected_next_year)]
                df.to_excel(writer, sheet_name=f'Block_091_{self.selected_next_year}', index=False)
            
            output.seek(0)
            phase_label = "Qoil" if self.is_oil_phase else "Qliq"
            return rx.download(
                data=output.getvalue(),
                filename=f"Block091_{phase_label}_{self.selected_next_year}.xlsx",
            )
        except Exception as e:
            return rx.toast.error(f"Download failed: {str(e)}")
    
    def _download_excel(self, data: List[dict], year: int):
        """Generic Excel download for summary data."""
        if not data:
            return rx.toast.error("No data available")
        
        try:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df = pd.DataFrame(data)
                columns = ["label"] + MONTH_NAMES + ["Total"]
                df = df[[c for c in columns if c in df.columns]]
                df.to_excel(writer, sheet_name=f'Summary_{year}', index=False)
            
            output.seek(0)
            phase_label = "Qoil" if self.is_oil_phase else "Qliq"
            return rx.download(
                data=output.getvalue(),
                filename=f"Block091_{phase_label}_Summary_{year}.xlsx",
            )
        except Exception as e:
            return rx.toast.error(f"Download failed: {str(e)}")