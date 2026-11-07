"""
build_powerbi_kit.py — everything needed to build the Power BI Healthcare Dashboard.

    powerbi/data/*.csv            star schema (dim_* + fact_*) ready for Get Data → Text/CSV
    powerbi/healthcare_theme.json colors + fonts matching the web dashboard
    powerbi/DAX_measures.md       every measure, copy-paste ready
    (the page-by-page build guide is powerbi/POWER_BI_GUIDE.md)

Run:  python src/build_powerbi_kit.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CLEAN, OUT = ROOT / "data" / "clean", ROOT / "powerbi"

THEME = {
    "name": "Healthcare Analytics",
    "dataColors": ["#0E7490", "#14B8A6", "#6366F1", "#F59E0B", "#EC4899", "#0EA5E9", "#84CC16", "#EF4444"],
    "background": "#FFFFFF", "foreground": "#0F172A", "tableAccent": "#0E7490",
    "good": "#16A34A", "neutral": "#F59E0B", "bad": "#DC2626",
    "textClasses": {
        "title": {"fontFace": "Segoe UI Semibold", "fontSize": 14, "color": "#0F172A"},
        "header": {"fontFace": "Segoe UI Semibold", "fontSize": 12, "color": "#0F172A"},
        "label": {"fontFace": "Segoe UI", "fontSize": 10, "color": "#475569"},
        "callout": {"fontFace": "Segoe UI Semibold", "fontSize": 28, "color": "#0E7490"},
    },
}

DAX = """# DAX measures — Healthcare Dashboard

Create a table called **_Measures** (Home → Enter data → empty table) and add each measure below
(Modeling → New measure). Format % measures as Percentage with 1 decimal.

## Volume
```DAX
Admissions = COUNTROWS ( fact_admission )
Patients = DISTINCTCOUNT ( fact_admission[patient_key] )
Emergency Admissions = CALCULATE ( [Admissions], fact_admission[visit_type] = "Emergency" )
Emergency % = DIVIDE ( [Emergency Admissions], [Admissions] )
Admissions per Patient = DIVIDE ( [Admissions], [Patients] )
```

## Length of stay and cost
```DAX
Avg LOS (days) = AVERAGE ( fact_admission[length_of_stay_days] )
Median LOS (days) = MEDIAN ( fact_admission[length_of_stay_days] )
Long Stays (>10 days) = CALCULATE ( [Admissions], fact_admission[length_of_stay_days] > 10 )
Total Cost = SUM ( fact_admission[treatment_cost] )
Avg Cost per Stay = DIVIDE ( [Total Cost], [Admissions] )
Cost per Bed Day = DIVIDE ( [Total Cost], SUM ( fact_admission[length_of_stay_days] ) )
```

## Readmissions
```DAX
Readmissions (30d) = CALCULATE ( [Admissions], fact_admission[readmitted_30d] = TRUE () )
Observable Stays = CALCULATE ( [Admissions], NOT ISBLANK ( fact_admission[readmitted_30d] ) )   -- excludes the last 30 days
Readmission Rate = DIVIDE ( [Readmissions (30d)], [Observable Stays] )
Avg Predicted Risk = AVERAGE ( fact_admission[readmission_risk] )
High-Risk Stays = CALCULATE ( [Admissions], fact_admission[readmission_risk] >= 0.25 )
Readmission Rate vs Target = [Readmission Rate] - 0.14        -- 14% target; change to your own
```

## Recovery
```DAX
Avg Recovery Score = AVERAGE ( fact_admission[recovery_score] )
```

## Appointments
```DAX
Appointments = COUNTROWS ( fact_appointment )
No-shows = CALCULATE ( [Appointments], fact_appointment[status] = "No-show" )
No-show Rate = DIVIDE ( [No-shows], [Appointments] )
Cancellation Rate = DIVIDE ( CALCULATE ( [Appointments], fact_appointment[status] = "Cancelled" ), [Appointments] )
No-show Rate (SMS) = CALCULATE ( [No-show Rate], fact_appointment[sms_reminder] = "Yes" )
No-show Rate (no SMS) = CALCULATE ( [No-show Rate], fact_appointment[sms_reminder] = "No" )
```

## Time intelligence (needs dim_date marked as a date table)
```DAX
Admissions LY = CALCULATE ( [Admissions], SAMEPERIODLASTYEAR ( dim_date[date] ) )
Admissions YoY % = DIVIDE ( [Admissions] - [Admissions LY], [Admissions LY] )
Admissions MoM % =
VAR prev = CALCULATE ( [Admissions], DATEADD ( dim_date[date], -1, MONTH ) )
RETURN DIVIDE ( [Admissions] - prev, prev )
Admissions 3M Avg =
AVERAGEX ( DATESINPERIOD ( dim_date[date], MAX ( dim_date[date] ), -3, MONTH ), [Admissions] )
```

## Ranking & labels
```DAX
Hospital Rank (Readmission) = RANKX ( ALL ( dim_hospital[hospital_name] ), [Readmission Rate], , ASC )
Top Department =
FIRSTNONBLANK ( TOPN ( 1, VALUES ( dim_department[department] ), [Admissions] ), 1 )
KPI Title Readmission = "30-day readmission: " & FORMAT ( [Readmission Rate], "0.0%" )
```
"""


def main():
    data = OUT / "data"
    data.mkdir(parents=True, exist_ok=True)
    h = pd.read_csv(CLEAN / "hospitals.csv")
    pt = pd.read_csv(CLEAN / "patients.csv")
    a = pd.read_csv(CLEAN / "admissions.csv", parse_dates=["admit_datetime", "discharge_datetime"])
    p = pd.read_csv(CLEAN / "appointments.csv", parse_dates=["appointment_datetime", "booked_date"])

    dept = pd.DataFrame({"department": sorted(set(a.department) | set(p.department))})
    dept.insert(0, "department_id", range(1, len(dept) + 1))
    dept["service_line"] = dept.department.map({"Orthopedics": "Surgical", "Pediatrics": "Children",
                                                "General Medicine": "Medical"}).fillna("Specialty")
    did = dict(zip(dept.department, dept.department_id))
    dates = pd.DataFrame({"date": pd.date_range("2024-01-01", "2025-12-31")})
    dates["year"], dates["quarter"] = dates.date.dt.year, "Q" + dates.date.dt.quarter.astype(str)
    dates["month_num"], dates["month"] = dates.date.dt.month, dates.date.dt.strftime("%b")
    dates["year_month"] = dates.date.dt.strftime("%Y-%m")
    dates["weekday"], dates["weekday_num"] = dates.date.dt.day_name(), dates.date.dt.dayofweek + 1
    dates["season"] = dates.month_num.map({12: "Winter", 1: "Winter", 2: "Winter", 3: "Spring", 4: "Spring",
                                           5: "Spring", 6: "Summer", 7: "Summer", 8: "Summer"}).fillna("Autumn")

    fa = a[["admission_id", "patient_key", "hospital_id"]].copy()
    fa["department_id"] = a.department.map(did)
    fa["admit_date"] = a.admit_datetime.dt.date
    fa = fa.join(a[["admit_datetime", "discharge_datetime", "age_group", "visit_type", "treatment_type",
                    "length_of_stay_days", "treatment_cost", "cost_imputed", "recovery_score",
                    "readmission_risk", "is_readmission", "readmitted_30d"]])
    fp = p[["appointment_id", "patient_key", "hospital_id"]].copy()
    fp["department_id"] = p.department.map(did)
    fp["appointment_date"] = p.appointment_datetime.dt.date
    fp = fp.join(p[["appointment_datetime", "lead_time_days", "lead_time_band", "appointment_type",
                    "sms_reminder", "status"]])

    h.to_csv(data / "dim_hospital.csv", index=False)
    pt.to_csv(data / "dim_patient.csv", index=False)
    dept.to_csv(data / "dim_department.csv", index=False)
    dates.to_csv(data / "dim_date.csv", index=False, date_format="%Y-%m-%d")
    fa.to_csv(data / "fact_admission.csv", index=False, date_format="%Y-%m-%d %H:%M")
    fp.to_csv(data / "fact_appointment.csv", index=False, date_format="%Y-%m-%d %H:%M")
    (OUT / "healthcare_theme.json").write_text(json.dumps(THEME, indent=2))
    (OUT / "DAX_measures.md").write_text(DAX)
    print("Power BI kit:", ", ".join(sorted(x.name for x in data.iterdir())))


if __name__ == "__main__":
    main()
