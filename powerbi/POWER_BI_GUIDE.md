# Power BI Healthcare Dashboard — build guide

Everything you need is in this folder:

| File | Use |
|---|---|
| `data/*.csv` | the star schema: 4 dimension tables + 2 fact tables |
| `DAX_measures.md` | every measure, copy-paste ready |
| `healthcare_theme.json` | colors and fonts that match the web dashboard |

Alternative source: connect Power BI to PostgreSQL (`Get Data → PostgreSQL database`) and use the
views from `sql/04_views_for_power_bi.sql`.

---

## 1. Load the data (5 min)

1. **Home → Get Data → Text/CSV** → load each file in `powerbi/data/` (6 files).
2. In Power Query check the types: dates = *Date*, datetimes = *Date/Time*, `treatment_cost` =
   *Fixed decimal*, `readmitted_30d` / `is_readmission` / `cost_imputed` = *True/False*.
3. **Close & Apply.**

## 2. Model view — relationships (5 min)

Drag to create these (all *Many-to-one*, single direction, from fact → dimension):

| From (many) | To (one) |
|---|---|
| `fact_admission[hospital_id]` | `dim_hospital[hospital_id]` |
| `fact_admission[department_id]` | `dim_department[department_id]` |
| `fact_admission[patient_key]` | `dim_patient[patient_key]` |
| `fact_admission[admit_date]` | `dim_date[date]` |
| `fact_appointment[hospital_id]` | `dim_hospital[hospital_id]` |
| `fact_appointment[department_id]` | `dim_department[department_id]` |
| `fact_appointment[patient_key]` | `dim_patient[patient_key]` |
| `fact_appointment[appointment_date]` | `dim_date[date]` |

Then: select `dim_date` → **Table tools → Mark as date table** → column `date`.
Sort `dim_date[month]` by `month_num` (Column tools → Sort by column).

## 3. Theme and measures (10 min)

* **View → Themes → Browse for themes** → `healthcare_theme.json`.
* Create the measures from `DAX_measures.md`.

## 4. Pages

Canvas 1280 × 720. Every page: title text box at the top-left, slicers for **Hospital**,
**Department** and **Year** across the top right (sync them: View → Sync slicers).

### Page 1 — Executive Overview
* 6 KPI cards: `Admissions`, `Patients`, `Avg LOS (days)`, `Avg Cost per Stay`, `Readmission Rate`, `No-show Rate`
* Line chart: `dim_date[year_month]` × `Admissions` (add `Admissions 3M Avg` as a second line)
* Bar chart: `dim_department[department]` × `Admissions` (sorted descending) — answers **Q1**
* Donut: `fact_admission[visit_type]` × `Admissions`
* Text box with the 3 headline insights from `reports/Healthcare_Insights_Report.md`

### Page 2 — Hospital Performance
* Table: `dim_hospital[hospital_name]`, `Admissions`, `Avg LOS (days)`, `Readmission Rate`,
  `Avg Recovery Score`, `Avg Cost per Stay`, `No-show Rate`; conditional formatting
  (background color scale, green = good) on Readmission Rate and Avg LOS
* Clustered bar: hospital × `Readmission Rate` with a constant line at 14% (Analytics pane)
* Scatter: X = `Avg LOS (days)`, Y = `Readmission Rate`, size = `Admissions`, legend = hospital

### Page 3 — Length of Stay & Cost
* Bar: department × `Avg Cost per Stay` — answers **Q3**
* Matrix: rows = department, columns = `fact_admission[treatment_type]`, values = `Avg Cost per Stay`
* Column chart: department × `Avg LOS (days)`
* Card: `Long Stays (>10 days)`; card: `Cost per Bed Day`

### Page 4 — Readmissions
* Big KPI card: `Readmission Rate` (**Q4**) with `Readmission Rate vs Target` as a subtitle
* Bar: `dim_patient[age_group]` × `Readmission Rate`
* Bar: department × `Readmission Rate`
* Column chart: risk band × `Readmission Rate` (add a calculated column
  `Risk Band = SWITCH(TRUE(), [readmission_risk] < 0.1, "<10%", [readmission_risk] < 0.2, "10-20%", [readmission_risk] < 0.3, "20-30%", "30%+")`)

### Page 5 — Patient Demographics
* Column chart: `fact_admission[age_group]` × `Admissions` — answers **Q2**
* Donut: `dim_patient[gender]`; bar: `dim_patient[insurance_type]` × `Admissions`
* Card: `Admissions per Patient` by age group (small multiples or a table)

### Page 6 — Appointments & No-shows
* KPI cards: `Appointments`, `No-show Rate` (**Q5**), `Cancellation Rate`
* Column chart: `fact_appointment[lead_time_band]` × `No-show Rate`
  (sort lead_time_band in the right order with a helper column)
* Clustered bar: `fact_appointment[sms_reminder]` × `No-show Rate`
* Matrix heatmap: rows = `dim_date[weekday]`, columns = `dim_patient[age_group]`, values = `No-show Rate`

## 5. Finishing touches
* Add a **Reset filters** bookmark button on every page.
* Tooltips: show `Admissions`, `Avg Cost per Stay`, `Readmission Rate` on hover.
* Publish to Power BI Service (File → Publish) and use *Publish to web* only because the data is synthetic.
* Export a PDF of the pages and add screenshots to `reports/figures/` for the README.
