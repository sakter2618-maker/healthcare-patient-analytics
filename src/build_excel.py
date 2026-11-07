"""
build_excel.py — excel/Healthcare_Patient_Data_Cleaning.xlsx

The Excel part of the project: a raw-export sample with every problem highlighted, the
cleaning log, the cleaned tables, and a summary sheet where every KPI and answer is a live
formula (COUNTIFS / AVERAGEIFS / SUMPRODUCT / INDEX-MATCH) over the cleaned data.

Run:  python src/build_excel.py   (then recalculate: python <xlsx skill>/scripts/recalc.py <file>)
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.formatting.rule import ColorScaleRule, DataBarRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
RAW, CLEAN = ROOT / "data" / "raw", ROOT / "data" / "clean"
OUT = ROOT / "excel" / "Healthcare_Patient_Data_Cleaning.xlsx"

FONT = "Arial"
TEAL, TEAL_L, ZEBRA, ISSUE = "0F766E", "CCFBF1", "F5FAFA", "FDE2E1"
thin = Side(style="thin", color="D9D9D9")
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)
AGE = ["0-17", "18-30", "31-45", "46-60", "60+"]
BANDS = ["Same day", "1-7 days", "8-14 days", "15-30 days", "31-60 days", "60+ days"]


def f(bold=False, color="000000", size=10, italic=False):
    return Font(name=FONT, bold=bold, color=color, size=size, italic=italic)


def header(ws, row, cols, widths=None, start_col=1):
    for j, h in enumerate(cols):
        c = ws.cell(row=row, column=start_col + j, value=h)
        c.font = f(True, "FFFFFF")
        c.fill = PatternFill("solid", fgColor=TEAL)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = BORDER
        if widths:
            ws.column_dimensions[get_column_letter(start_col + j)].width = widths[j]
    ws.row_dimensions[row].height = 30


def title(ws, text, sub):
    ws["A1"], ws["A2"] = text, sub
    ws["A1"].font = f(True, TEAL, 16)
    ws["A2"].font = f(False, "52514E", 10, True)


def write_df(ws, df, start_row, widths):
    header(ws, start_row, list(df.columns), widths)
    for i, row in enumerate(df.itertuples(index=False), start=start_row + 1):
        for j, v in enumerate(row, start=1):
            c = ws.cell(row=i, column=j, value=None if (isinstance(v, float) and pd.isna(v)) else v)
            c.font = f()
    ws.freeze_panes = ws.cell(row=start_row + 1, column=1)
    ws.auto_filter.ref = f"A{start_row}:{get_column_letter(df.shape[1])}{start_row + len(df)}"


def raw_issue_cells(df: pd.DataFrame) -> dict[tuple[int, str], str]:
    """Find the problems a cleaner has to fix, so they can be highlighted in the raw sample."""
    issues = {}
    valid_dept = {"Cardiology", "General Medicine", "Orthopedics", "Neurology", "Pediatrics", "Oncology"}
    dups = df.duplicated(keep="first")
    for i, r in df.iterrows():
        if dups[i]:
            issues[(i, "admission_id")] = "Exact duplicate of an earlier row"
        if r.department not in valid_dept:
            issues[(i, "department")] = "Non-standard department label"
        if r.gender not in ("Male", "Female"):
            issues[(i, "gender")] = "Gender coded M/F, lower case or blank"
        for c in ("admit_datetime", "discharge_datetime"):
            if isinstance(r[c], str) and "/" in r[c]:
                issues[(i, c)] = "US date format (MM/DD/YYYY)"
        if isinstance(r.treatment_cost, str) and re.search(r"[$,]", r.treatment_cost):
            issues[(i, "treatment_cost")] = "Cost stored as text with $ and commas"
        if pd.isna(r.treatment_cost) or r.treatment_cost == "":
            issues[(i, "treatment_cost")] = "Missing cost"
        if r.length_of_stay_days < 0:
            issues[(i, "length_of_stay_days")] = "Negative stay: admit/discharge swapped"
        if r.readmission_risk > 1:
            issues[(i, "readmission_risk")] = "Risk typed as a percentage"
        if pd.isna(r.age_group) or r.age_group == "":
            issues[(i, "age_group")] = "Missing age group"
        if r.department == "Pediatrics" and r.age_group == "60+":
            issues[(i, "age_group")] = "Pediatrics patient coded 60+"
        if pd.isna(r.recovery_score):
            issues[(i, "recovery_score")] = "Missing recovery score"
    return issues


def main():
    OUT.parent.mkdir(exist_ok=True)
    wb = Workbook()

    # ---------------------------------------------------------------- README
    ws = wb.active
    ws.title = "README"
    title(ws, "Healthcare Patient Analytics — Data Cleaning Workbook",
          "Synthetic, de-identified data. patient_key values are random IDs, not people.")
    lines = [
        ("Sheet", "What it contains"),
        ("Summary", "KPIs and the 5 business questions. Every number is a live formula over the clean sheets."),
        ("Raw_Sample", "First 400 rows of the raw hospital export. Red cells = problems the cleaning fixed (hover for the note)."),
        ("Cleaning_Log", "Every cleaning step, the rows it touched and what was done (same log as the Python pipeline)."),
        ("Admissions", "21,700+ cleaned inpatient stays (1 = yes / 0 = no for flags)."),
        ("Appointments", "48,000 cleaned outpatient appointments."),
        ("Hospitals", "The 5 fictional hospitals."),
        ("", ""),
        ("How to use", "Filter or edit the clean sheets and the Summary updates. Colors: white = formula, "
                       "teal header = table, red fill = data problem in the raw export."),
    ]
    for i, (a, b) in enumerate(lines, start=4):
        ws.cell(row=i, column=1, value=a).font = f(i == 4 or a == "How to use", TEAL if i == 4 else "000000")
        ws.cell(row=i, column=2, value=b).font = f(i == 4)
    ws.column_dimensions["A"].width, ws.column_dimensions["B"].width = 16, 110

    # ---------------------------------------------------------------- data sheets
    adm = pd.read_csv(CLEAN / "admissions.csv", parse_dates=["admit_datetime"])
    hosp = pd.read_csv(CLEAN / "hospitals.csv")
    appt = pd.read_csv(CLEAN / "appointments.csv", parse_dates=["appointment_datetime"])
    adm = adm.merge(hosp[["hospital_id", "hospital_name"]], on="hospital_id")
    appt = appt.merge(hosp[["hospital_id", "hospital_name"]], on="hospital_id")
    a = pd.DataFrame({
        "admission_id": adm.admission_id, "patient_key": adm.patient_key, "hospital": adm.hospital_name,
        "department": adm.department, "age_group": adm.age_group, "gender": adm.gender,
        "visit_type": adm.visit_type, "treatment_type": adm.treatment_type,
        "admit_date": adm.admit_datetime.dt.date, "length_of_stay_days": adm.length_of_stay_days,
        "treatment_cost": adm.treatment_cost, "recovery_score": adm.recovery_score,
        "readmission_risk": adm.readmission_risk, "readmitted_30d": adm.readmitted_30d.map({True: 1, False: 0, "True": 1, "False": 0}),
        "cost_imputed": adm.cost_imputed.astype(int)})
    p = pd.DataFrame({
        "appointment_id": appt.appointment_id, "hospital": appt.hospital_name, "department": appt.department,
        "age_group": appt.age_group, "appointment_date": appt.appointment_datetime.dt.date,
        "lead_time_days": appt.lead_time_days, "lead_time_band": appt.lead_time_band,
        "sms_reminder": appt.sms_reminder, "weekday": appt.weekday, "status": appt.status,
        "no_show": appt.no_show.astype(int)})
    na, npt = len(a) + 1, len(p) + 1   # last data row (header in row 1)

    # ---------------------------------------------------------------- Summary (formulas)
    s = wb.create_sheet("Summary", 1)
    title(s, "Healthcare KPIs & Business Questions",
          "All values below are formulas over the Admissions / Appointments sheets.")
    A, P = "Admissions", "Appointments"
    rngA = lambda col: f"{A}!${col}$2:${col}${na}"
    rngP = lambda col: f"{P}!${col}$2:${col}${npt}"
    kpis = [
        ("Admissions", f"=COUNTA({rngA('A')})", "#,##0"),
        ("Unique patients", f"=SUMPRODUCT(1/COUNTIF({rngA('B')},{rngA('B')}))", "#,##0"),
        ("Average length of stay (days)", f"=AVERAGE({rngA('J')})", "0.00"),
        ("Average treatment cost ($)", f"=AVERAGE({rngA('K')})", "$#,##0"),
        ("30-day readmission rate", f"=AVERAGE({rngA('N')})", "0.0%"),
        ("Emergency share of admissions", f"=COUNTIF({rngA('G')},\"Emergency\")/COUNTA({rngA('A')})", "0.0%"),
        ("Appointments", f"=COUNTA({rngP('A')})", "#,##0"),
        ("No-show rate", f"=AVERAGE({rngP('K')})", "0.0%"),
        ("Cancellation rate", f"=COUNTIF({rngP('J')},\"Cancelled\")/COUNTA({rngP('A')})", "0.0%"),
    ]
    header(s, 4, ["KPI", "Value"], [36, 16])
    for i, (k, formula, fmt) in enumerate(kpis, start=5):
        s.cell(row=i, column=1, value=k).font = f()
        c = s.cell(row=i, column=2, value=formula)
        c.font, c.number_format, c.border = f(True), fmt, BORDER

    # Q1 + Q3: departments
    r0 = 16
    s.cell(row=r0 - 1, column=1, value="Q1 / Q3 — Admissions and average treatment cost by department").font = f(True, TEAL, 12)
    header(s, r0, ["Department", "Admissions", "Share", "Avg cost ($)", "Avg LOS (days)", "Readmission rate"],
           [36, 16, 12, 16, 16, 18])
    depts = a.department.value_counts().index.tolist()
    for i, d in enumerate(depts, start=r0 + 1):
        s.cell(row=i, column=1, value=d)
        s.cell(row=i, column=2, value=f"=COUNTIF({rngA('D')},A{i})").number_format = "#,##0"
        s.cell(row=i, column=3, value=f"=B{i}/SUM($B${r0 + 1}:$B${r0 + len(depts)})").number_format = "0.0%"
        s.cell(row=i, column=4, value=f"=AVERAGEIF({rngA('D')},A{i},{rngA('K')})").number_format = "$#,##0"
        s.cell(row=i, column=5, value=f"=AVERAGEIF({rngA('D')},A{i},{rngA('J')})").number_format = "0.00"
        s.cell(row=i, column=6, value=f"=AVERAGEIF({rngA('D')},A{i},{rngA('N')})").number_format = "0.0%"
    last = r0 + len(depts)
    s.conditional_formatting.add(f"B{r0 + 1}:B{last}", DataBarRule(start_type="min", end_type="max", color="14B8A6"))
    s.conditional_formatting.add(f"D{r0 + 1}:D{last}", ColorScaleRule(start_type="min", start_color="FFFFFF",
                                                                      end_type="max", end_color="F59E0B"))
    ans = last + 1
    s.cell(row=ans, column=1, value="Most admissions →").font = f(True)
    s.cell(row=ans, column=2, value=f"=INDEX(A{r0 + 1}:A{last},MATCH(MAX(B{r0 + 1}:B{last}),B{r0 + 1}:B{last},0))").font = f(True, TEAL)
    s.cell(row=ans + 1, column=1, value="Highest average cost →").font = f(True)
    s.cell(row=ans + 1, column=2, value=f"=INDEX(A{r0 + 1}:A{last},MATCH(MAX(D{r0 + 1}:D{last}),D{r0 + 1}:D{last},0))").font = f(True, TEAL)

    # Q2: age groups
    r1 = ans + 4
    s.cell(row=r1 - 1, column=1, value="Q2 — Which age group uses healthcare services the most?").font = f(True, TEAL, 12)
    header(s, r1, ["Age group", "Admissions", "Appointments", "Total services", "Share of services", "Readmission rate"])
    for i, g in enumerate(AGE, start=r1 + 1):
        s.cell(row=i, column=1, value=g)
        s.cell(row=i, column=2, value=f"=COUNTIF({rngA('E')},A{i})").number_format = "#,##0"
        s.cell(row=i, column=3, value=f"=COUNTIF({rngP('D')},A{i})").number_format = "#,##0"
        s.cell(row=i, column=4, value=f"=B{i}+C{i}").number_format = "#,##0"
        s.cell(row=i, column=5, value=f"=D{i}/SUM($D${r1 + 1}:$D${r1 + 5})").number_format = "0.0%"
        s.cell(row=i, column=6, value=f"=AVERAGEIF({rngA('E')},A{i},{rngA('N')})").number_format = "0.0%"
    s.cell(row=r1 + 6, column=1, value="Most services →").font = f(True)
    s.cell(row=r1 + 6, column=2, value=f"=INDEX(A{r1 + 1}:A{r1 + 5},MATCH(MAX(D{r1 + 1}:D{r1 + 5}),D{r1 + 1}:D{r1 + 5},0))").font = f(True, TEAL)

    # Q4 / hospitals
    r2 = r1 + 10
    s.cell(row=r2 - 1, column=1, value="Q4 — 30-day readmission rate by hospital").font = f(True, TEAL, 12)
    header(s, r2, ["Hospital", "Admissions", "Readmission rate", "Avg LOS (days)", "Avg recovery score", "No-show rate"])
    for i, h in enumerate(hosp.hospital_name, start=r2 + 1):
        s.cell(row=i, column=1, value=h)
        s.cell(row=i, column=2, value=f"=COUNTIF({rngA('C')},A{i})").number_format = "#,##0"
        s.cell(row=i, column=3, value=f"=AVERAGEIF({rngA('C')},A{i},{rngA('N')})").number_format = "0.0%"
        s.cell(row=i, column=4, value=f"=AVERAGEIF({rngA('C')},A{i},{rngA('J')})").number_format = "0.00"
        s.cell(row=i, column=5, value=f"=AVERAGEIF({rngA('C')},A{i},{rngA('L')})").number_format = "0.0"
        s.cell(row=i, column=6, value=f"=AVERAGEIF({rngP('B')},A{i},{rngP('K')})").number_format = "0.0%"
    hl = r2 + len(hosp)
    s.conditional_formatting.add(f"C{r2 + 1}:C{hl}", ColorScaleRule(start_type="min", start_color="D1FAE5",
                                                                    end_type="max", end_color="FCA5A5"))

    # Q5: no-show by lead time + SMS
    r3 = hl + 4
    s.cell(row=r3 - 1, column=1, value="Q5 — Appointment no-show rate by booking lead time").font = f(True, TEAL, 12)
    header(s, r3, ["Lead time", "Appointments", "No-show rate"])
    for i, b in enumerate(BANDS, start=r3 + 1):
        s.cell(row=i, column=1, value=b)
        s.cell(row=i, column=2, value=f"=COUNTIF({rngP('G')},A{i})").number_format = "#,##0"
        s.cell(row=i, column=3, value=f"=AVERAGEIF({rngP('G')},A{i},{rngP('K')})").number_format = "0.0%"
    r4 = r3 + 8
    header(s, r4, ["SMS reminder", "Appointments", "No-show rate"])
    for i, v in enumerate(["Yes", "No", "Unknown"], start=r4 + 1):
        s.cell(row=i, column=1, value=v)
        s.cell(row=i, column=2, value=f"=COUNTIF({rngP('H')},A{i})").number_format = "#,##0"
        s.cell(row=i, column=3, value=f"=AVERAGEIF({rngP('H')},A{i},{rngP('K')})").number_format = "0.0%"
    for row in s.iter_rows(min_row=5, max_row=r4 + 4, max_col=6):
        for c in row:
            if c.value is not None and c.row not in (r0, r1, r2, r3, r4):
                c.border = BORDER
                if not c.font.bold:
                    c.font = f()

    ch = BarChart()
    ch.type, ch.style, ch.title = "bar", 10, "Admissions by department"
    ch.add_data(Reference(s, min_col=2, min_row=r0, max_row=last), titles_from_data=True)
    ch.set_categories(Reference(s, min_col=1, min_row=r0 + 1, max_row=last))
    ch.height, ch.width, ch.legend = 7, 14, None
    s.add_chart(ch, "H4")
    ch2 = BarChart()
    ch2.style, ch2.title = 10, "No-show rate by lead time"
    ch2.add_data(Reference(s, min_col=3, min_row=r3, max_row=r3 + 6), titles_from_data=True)
    ch2.set_categories(Reference(s, min_col=1, min_row=r3 + 1, max_row=r3 + 6))
    ch2.height, ch2.width, ch2.legend = 7, 14, None
    ch2.y_axis.numFmt = "0%"
    s.add_chart(ch2, "H20")

    # ---------------------------------------------------------------- Raw sample
    raw = pd.read_csv(RAW / "admissions_raw.csv", dtype={"treatment_cost": str}, keep_default_na=False,
                      na_values={"recovery_score": [""], "readmission_risk": [""]})
    sample = raw.head(400).copy()
    issues = raw_issue_cells(raw.head(400))
    ws = wb.create_sheet("Raw_Sample")
    write_df(ws, sample, 1, [11, 11, 9, 9, 18, 9, 18, 11, 12, 10, 18, 13, 10, 10])
    from openpyxl.comments import Comment
    cols = list(sample.columns)
    for (i, col), note in issues.items():
        c = ws.cell(row=i + 2, column=cols.index(col) + 1)
        c.fill = PatternFill("solid", fgColor=ISSUE)
        c.comment = Comment(note, "Data check")

    # ---------------------------------------------------------------- log + data
    ws = wb.create_sheet("Cleaning_Log")
    write_df(ws, pd.read_csv(ROOT / "docs" / "cleaning_log.csv"), 1, [14, 22, 14, 90])
    ws = wb.create_sheet(A)
    write_df(ws, a, 1, [12, 11, 28, 17, 9, 9, 11, 13, 12, 12, 13, 12, 12, 13, 11])
    for r in range(2, na + 1):
        ws.cell(row=r, column=11).number_format = "$#,##0"
    ws = wb.create_sheet(P)
    write_df(ws, p, 1, [13, 28, 17, 9, 14, 12, 12, 12, 11, 11, 9])
    ws = wb.create_sheet("Hospitals")
    write_df(ws, hosp, 1, [11, 30, 9, 8, 13])

    wb.save(OUT)
    print(f"saved {OUT.relative_to(ROOT)} · {len(issues)} raw problems highlighted")


if __name__ == "__main__":
    main()
