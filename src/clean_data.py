"""
clean_data.py — Python (pandas / NumPy) cleaning of the raw hospital export.

Every fix is written to docs/cleaning_log.csv (table, step, rows affected, what was done),
so the cleaning can be explained line by line in an interview.

    data/raw/*.csv  ──▶  clean  ──▶  data/clean/{hospitals,patients,admissions,appointments}.csv

Admissions get two derived fields that the analysis needs:
    readmitted_30d   the patient came back to any hospital within 30 days of this discharge
    is_readmission   this stay itself is a return within 30 days of an earlier discharge

Run:  python src/clean_data.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, CLEAN, DOCS = ROOT / "data" / "raw", ROOT / "data" / "clean", ROOT / "docs"

DEPT_MAP = {"cardiology": "Cardiology", "cardio": "Cardiology", "gen med": "General Medicine",
            "general medicine": "General Medicine", "orthopaedics": "Orthopedics", "orthopedics": "Orthopedics",
            "neurology": "Neurology", "paediatrics": "Pediatrics", "pediatrics": "Pediatrics", "oncology": "Oncology"}
STATUS_MAP = {"attended": "Attended", "no-show": "No-show", "no show": "No-show", "ns": "No-show",
              "cancelled": "Cancelled"}
AGE_ORDER = ["0-17", "18-30", "31-45", "46-60", "60+"]

LOG: list[dict] = []


def log(table, step, rows, action):
    rows = int(rows)
    if rows:
        LOG.append(dict(table=table, step=step, rows_affected=rows, action=action))


def parse_dt(s: pd.Series) -> pd.Series:
    """Two date formats arrive from two source systems: ISO and US (MM/DD/YYYY)."""
    iso = pd.to_datetime(s, format="%Y-%m-%d %H:%M", errors="coerce")
    us = pd.to_datetime(s, format="%m/%d/%Y %H:%M", errors="coerce")
    return iso.fillna(us)


def clean_patients() -> pd.DataFrame:
    p = pd.read_csv(RAW / "patients_raw.csv")
    upper = p.insurance_type.str.isupper() & (p.insurance_type.str.len() > 0)
    p["insurance_type"] = p.insurance_type.str.title().str.replace("Self-Pay", "Self-pay")
    log("patients", "Standardise labels", upper.sum(), "Insurance type in capitals -> title case")
    dup = p.duplicated()
    log("patients", "Duplicates", dup.sum(), "Removed exact duplicate patient rows")
    p = p[~dup]
    p["age_group"] = pd.Categorical(p.age_group, AGE_ORDER, ordered=True)
    return p.reset_index(drop=True)


def clean_admissions(patients: pd.DataFrame) -> pd.DataFrame:
    a = pd.read_csv(RAW / "admissions_raw.csv", dtype={"treatment_cost": str})
    t = "admissions"
    dup = a.duplicated()
    log(t, "1. Duplicates", dup.sum(), "Removed exact duplicate rows (double export)")
    a = a[~dup].copy()

    dkey = a.department.str.strip().str.lower()
    fixed = a.department != dkey.map(DEPT_MAP)
    a["department"] = dkey.map(DEPT_MAP)
    log(t, "2. Standardise labels", fixed.sum(), "Unified department spellings (Cardio, Gen Med, Paediatrics…)")

    g = a.gender.fillna("").str.strip().str.lower().map({"m": "Male", "male": "Male", "f": "Female", "female": "Female"})
    log(t, "2. Standardise labels", (a.gender.fillna("") != g.fillna("")).sum() - g.isna().sum(),
        "Gender M/F/lower case -> Male/Female")
    log(t, "2. Standardise labels", g.isna().sum(), "Blank gender -> 'Unknown' (not guessed)")
    a["gender"] = g.fillna("Unknown")

    for c in ["admit_datetime", "discharge_datetime"]:
        us = a[c].str.contains("/", na=False)
        log(t, "3. Fix types", us.sum(), f"{c}: US date format MM/DD/YYYY converted")
        a[c] = parse_dt(a[c])

    swapped = a.discharge_datetime < a.admit_datetime
    a.loc[swapped, ["admit_datetime", "discharge_datetime"]] = a.loc[swapped, ["discharge_datetime", "admit_datetime"]].values
    log(t, "4. Invalid values", swapped.sum(), "Discharge before admission: dates were swapped -> corrected")
    los = ((a.discharge_datetime - a.admit_datetime).dt.total_seconds() / 86400).round(1)
    bad_los = (a.length_of_stay_days - los).abs() > 0.15
    log(t, "4. Invalid values", bad_los.sum(), "Length of stay recalculated from the corrected dates")
    a["length_of_stay_days"] = los

    txt = a.treatment_cost.str.contains(r"[$,]", na=False)
    a["treatment_cost"] = pd.to_numeric(a.treatment_cost.str.replace(r"[$,]", "", regex=True), errors="coerce")
    log(t, "3. Fix types", txt.sum(), "Treatment cost stored as text ($12,345.00) -> number")

    pct = a.readmission_risk > 1
    a.loc[pct, "readmission_risk"] = a.loc[pct, "readmission_risk"] / 100
    log(t, "4. Invalid values", pct.sum(), "Readmission risk entered as a percentage (34) -> 0.34")

    blank_age = a.age_group.isna() | (a.age_group.astype(str).str.strip() == "")
    kid_bad = (a.department == "Pediatrics") & (a.age_group == "60+")
    ref = patients.set_index("patient_key").age_group.astype(str)
    a.loc[blank_age | kid_bad, "age_group"] = a.loc[blank_age | kid_bad, "patient_key"].map(ref)
    log(t, "5. Missing values", blank_age.sum(), "Missing age group filled from the patient master table")
    log(t, "4. Invalid values", kid_bad.sum(), "Pediatrics stay coded as 60+ -> age taken from patient master")

    miss_cost = a.treatment_cost.isna()
    med = a.groupby(["department", "treatment_type"]).treatment_cost.transform("median")
    a.loc[miss_cost, "treatment_cost"] = med[miss_cost].round(2)
    a["cost_imputed"] = miss_cost
    log(t, "5. Missing values", miss_cost.sum(),
        "Missing cost filled with the median of the same department + treatment (flagged cost_imputed)")
    miss_rec = a.recovery_score.isna()
    a.loc[miss_rec, "recovery_score"] = a.groupby("department").recovery_score.transform("median")[miss_rec]
    log(t, "5. Missing values", miss_rec.sum(), "Missing recovery score filled with the department median")

    a = a.merge(patients[["patient_key", "region", "insurance_type"]], on="patient_key", how="left")
    a["age_group"] = pd.Categorical(a.age_group, AGE_ORDER, ordered=True)

    # readmission flags from the actual sequence of stays per patient
    a = a.sort_values(["patient_key", "admit_datetime"]).reset_index(drop=True)
    prev_dis = a.groupby("patient_key").discharge_datetime.shift()
    next_adm = a.groupby("patient_key").admit_datetime.shift(-1)
    a["is_readmission"] = (a.admit_datetime - prev_dis).dt.total_seconds().between(0, 30 * 86400)
    a["readmitted_30d"] = (next_adm - a.discharge_datetime).dt.total_seconds().between(0, 30 * 86400)
    log(t, "6. Derived fields", a.readmitted_30d.sum(), "readmitted_30d: patient returned within 30 days of discharge")
    # Stays discharged in the last 30 days of the data can't show a readmission yet (we can't see the
    # future), so counting them as "not readmitted" would flatter the rate. Leave them blank instead.
    data_end = a.admit_datetime.max()
    censored = a.discharge_datetime > data_end - pd.Timedelta(days=30)
    a["readmitted_30d"] = a.readmitted_30d.astype("boolean").mask(censored)
    log(t, "6. Derived fields", censored.sum(),
        "Discharged in the last 30 days of data: readmission not yet observable -> left blank, excluded from the rate")
    a["admit_month"] = a.admit_datetime.dt.to_period("M").astype(str)
    return a.sort_values("admit_datetime").reset_index(drop=True)


def clean_appointments() -> pd.DataFrame:
    a = pd.read_csv(RAW / "appointments_raw.csv")
    t = "appointments"
    dup = a.duplicated()
    log(t, "1. Duplicates", dup.sum(), "Removed exact duplicate appointment rows")
    a = a[~dup].copy()
    s = a.status.str.strip().str.lower().map(STATUS_MAP)
    log(t, "2. Standardise labels", (a.status != s).sum(), "Status variants (No Show, NS, no-show, attended) unified")
    a["status"] = s
    blank = a.sms_reminder.isna() | (a.sms_reminder.astype(str).str.strip() == "")
    log(t, "5. Missing values", blank.sum(), "Blank SMS reminder flag -> 'Unknown' (not counted as yes or no)")
    a["sms_reminder"] = a.sms_reminder.fillna("").replace("", "Unknown")
    a["appointment_datetime"] = pd.to_datetime(a.appointment_datetime)
    neg = a.lead_time_days < 0
    a["booked_date"] = pd.to_datetime(a.booked_date)
    a["lead_time_days"] = (a.appointment_datetime.dt.normalize() - a.booked_date).dt.days
    log(t, "4. Invalid values", neg.sum(), "Negative lead time (sign error) -> recalculated from booked date")
    a["no_show"] = a.status == "No-show"
    a["lead_time_band"] = pd.cut(a.lead_time_days, [-1, 0, 7, 14, 30, 60, 999],
                                 labels=["Same day", "1-7 days", "8-14 days", "15-30 days", "31-60 days", "60+ days"])
    a["weekday"] = a.appointment_datetime.dt.day_name()
    a["age_group"] = pd.Categorical(a.age_group, AGE_ORDER, ordered=True)
    a["appt_month"] = a.appointment_datetime.dt.to_period("M").astype(str)
    return a.sort_values("appointment_datetime").reset_index(drop=True)


def main():
    CLEAN.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(exist_ok=True)
    hospitals = pd.read_csv(RAW / "hospitals.csv")
    patients = clean_patients()
    adm = clean_admissions(patients)
    appts = clean_appointments()
    hospitals.to_csv(CLEAN / "hospitals.csv", index=False)
    patients.to_csv(CLEAN / "patients.csv", index=False)
    adm.to_csv(CLEAN / "admissions.csv", index=False, date_format="%Y-%m-%d %H:%M")
    appts.to_csv(CLEAN / "appointments.csv", index=False, date_format="%Y-%m-%d %H:%M")
    pd.DataFrame(LOG).to_csv(DOCS / "cleaning_log.csv", index=False)
    assert adm.department.notna().all() and adm.treatment_cost.notna().all()
    assert (adm.length_of_stay_days >= 0).all() and adm.readmission_risk.between(0, 1).all()
    assert appts.status.notna().all() and (appts.lead_time_days >= 0).all()
    print(f"clean: patients {len(patients):,} · admissions {len(adm):,} · appointments {len(appts):,} "
          f"· {len(LOG)} logged fixes")


if __name__ == "__main__":
    main()
