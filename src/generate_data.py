"""
generate_data.py — builds the synthetic hospital dataset used by the whole project.

NO REAL PATIENT DATA. Every row is generated here from a fixed random seed, so anyone can
reproduce the exact same files. Patient keys (P000001…) are random identifiers, not people.

The columns of the original sample file are kept (age_group, gender, region, department,
treatment_type, visit_type, length_of_stay_days, treatment_cost, recovery_score,
readmission_risk). The sample had no hospital, appointment or no-show fields and its
numbers were uniform noise, so this generator adds those tables and realistic patterns.

Outputs (data/raw/ = what a hospital export typically looks like, with quality problems):
    hospitals.csv          5 fictional hospitals
    patients_raw.csv       ~14,000 de-identified patients
    admissions_raw.csv     ~21,000 inpatient stays (incl. real 30-day readmissions)
    appointments_raw.csv   ~48,000 outpatient appointments (Attended / No-show / Cancelled)

Run:  python src/generate_data.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
START, END = pd.Timestamp("2024-01-01"), pd.Timestamp("2025-12-31 23:00")

HOSPITALS = pd.DataFrame([
    # id, name, region, beds, type, LOS factor, readmission factor, cost factor
    ("H01", "Northgate Medical Center", "North", 420, "Teaching", 1.00, 1.00, 1.06),
    ("H02", "Lakeside General Hospital", "East", 310, "General", 0.97, 0.92, 0.98),
    ("H03", "Riverside Community Hospital", "South", 220, "Community", 1.24, 1.45, 0.93),
    ("H04", "Westbrook Specialty Hospital", "West", 260, "Specialty", 0.90, 0.72, 1.15),
    ("H05", "Eastview Regional Hospital", "East", 180, "Regional", 1.05, 1.08, 0.95),
], columns=["hospital_id", "hospital_name", "region", "beds", "hospital_type",
            "los_f", "readm_f", "cost_f"])

DEPTS = ["General Medicine", "Cardiology", "Orthopedics", "Pediatrics", "Neurology", "Oncology"]
DEPT_SHARE = [0.27, 0.20, 0.17, 0.14, 0.12, 0.10]
DEPT = pd.DataFrame({
    "department": DEPTS,
    "cost_base": [9500, 26000, 21000, 8200, 19500, 31000],
    "los_base": [3.6, 4.4, 3.5, 2.4, 5.0, 5.8],
    "readm_base": [0.088, 0.112, 0.056, 0.046, 0.090, 0.128],
    "recovery_base": [76, 72, 81, 84, 68, 66],
}).set_index("department")
TREAT = {"Surgery": 1.85, "Therapy": 1.0, "Medication": 0.78, "Observation": 0.55}
TREAT_MIX = {  # which treatments each department uses
    "General Medicine": [0.05, 0.20, 0.50, 0.25], "Cardiology": [0.30, 0.15, 0.40, 0.15],
    "Orthopedics": [0.55, 0.30, 0.10, 0.05], "Pediatrics": [0.08, 0.17, 0.45, 0.30],
    "Neurology": [0.15, 0.35, 0.35, 0.15], "Oncology": [0.25, 0.45, 0.25, 0.05],
}
AGE_GROUPS = ["0-17", "18-30", "31-45", "46-60", "60+"]
INSURANCE = ["Private", "Medicare", "Medicaid", "Self-pay"]


def make_patients(rng, n=14_000) -> pd.DataFrame:
    age = rng.choice(AGE_GROUPS, n, p=[0.14, 0.17, 0.22, 0.22, 0.25])
    ins = np.where(age == "60+", rng.choice(INSURANCE, n, p=[0.18, 0.72, 0.07, 0.03]),
                   np.where(age == "0-17", rng.choice(INSURANCE, n, p=[0.55, 0.0, 0.42, 0.03]),
                            rng.choice(INSURANCE, n, p=[0.66, 0.02, 0.20, 0.12])))
    return pd.DataFrame({
        "patient_key": [f"P{i:06d}" for i in range(1, n + 1)],
        "gender": rng.choice(["Female", "Male"], n, p=[0.52, 0.48]),
        "age_group": age,
        "region": rng.choice(["North", "South", "East", "West"], n, p=[0.30, 0.22, 0.28, 0.20]),
        "insurance_type": ins,
    })


def seasonal_times(rng, n, dept) -> pd.Series:
    """Admission timestamps with a winter peak (respiratory season) and an Orthopedics summer bump."""
    hours = pd.date_range(START, END, freq="h")
    month = hours.month.values
    w = np.ones(len(hours))
    w *= np.where(np.isin(month, [12, 1, 2]), 1.22, 1.0)
    w *= np.where(np.isin(month, [6, 7, 8]), 0.92, 1.0)
    w *= np.where(hours.dayofweek.values >= 5, 0.78, 1.0)          # fewer weekend admissions
    w *= np.where((hours.hour.values >= 8) & (hours.hour.values <= 20), 1.6, 0.6)
    w *= 1 + 0.06 * (hours.year.values - 2024)                     # +6% growth in 2025
    out = np.empty(n, dtype="datetime64[ns]")
    for d in np.unique(dept):
        idx = np.where(dept == d)[0]
        wd = w.copy()
        if d in ("General Medicine", "Pediatrics"):
            wd *= np.where(np.isin(month, [12, 1, 2]), 1.25, 1.0)
        if d == "Orthopedics":
            wd *= np.where(np.isin(month, [6, 7, 8]), 1.30, 1.0)
        out[idx] = rng.choice(hours.values, len(idx), p=wd / wd.sum())
    return pd.Series(out)


def make_admissions(rng, patients: pd.DataFrame, n_index=19_500) -> pd.DataFrame:
    p = patients.sample(n_index, replace=True, random_state=SEED,
                        weights=np.where(patients.age_group == "60+", 1.9,
                                         np.where(patients.age_group == "0-17", 0.8, 1.0))).reset_index(drop=True)
    age = p.age_group.values
    dept = np.where(age == "0-17", np.where(rng.random(n_index) < 0.86, "Pediatrics", "Orthopedics"),
                    rng.choice(DEPTS[:3] + DEPTS[4:], n_index, p=np.array([0.27, 0.20, 0.17, 0.12, 0.10]) / 0.86))
    # 60+ lean to Cardiology / Oncology / Neurology
    old = (age == "60+") & (rng.random(n_index) < 0.22)
    dept = np.where(old, rng.choice(["Cardiology", "Oncology", "Neurology"], n_index, p=[0.4, 0.3, 0.3]), dept)
    # hospital: mostly the patient's region, Westbrook takes complex specialty cases
    region_h = {"North": ["H01"], "East": ["H02", "H05"], "South": ["H03"], "West": ["H04"]}
    hosp = np.array([rng.choice(region_h[r]) if rng.random() < 0.78 else rng.choice(HOSPITALS.hospital_id)
                     for r in p.region.values])
    hosp = np.where(np.isin(dept, ["Oncology", "Neurology"]) & (rng.random(n_index) < 0.22), "H04", hosp)
    adm = pd.DataFrame({"patient_key": p.patient_key, "age_group": age, "gender": p.gender,
                        "region": p.region, "insurance_type": p.insurance_type,
                        "department": dept, "hospital_id": hosp})
    adm["admit_datetime"] = seasonal_times(rng, n_index, dept).values
    adm["visit_type"] = np.where(rng.random(n_index) < np.where(age == "60+", 0.48, 0.36), "Emergency", "Routine")
    adm["treatment_type"] = [rng.choice(list(TREAT), p=TREAT_MIX[d]) for d in dept]
    adm["is_readmission"] = False
    return adm


def add_outcomes(rng, adm: pd.DataFrame) -> pd.DataFrame:
    n = len(adm)
    h = HOSPITALS.set_index("hospital_id").loc[adm.hospital_id]
    d = DEPT.loc[adm.department]
    old, kid = (adm.age_group == "60+").values, (adm.age_group == "0-17").values
    emer = (adm.visit_type == "Emergency").values
    surg = (adm.treatment_type == "Surgery").values
    los = (d.los_base.values * h.los_f.values + 1.3 * old - 0.4 * kid + 0.6 * emer + 0.9 * surg)
    los = np.clip(rng.gamma(shape=4.0, scale=los / 4.0), 0.2, 30).round(1)
    adm["length_of_stay_days"] = los
    adm["discharge_datetime"] = adm.admit_datetime + pd.to_timedelta(los * 24, unit="h")
    cost = (d.cost_base.values * np.array([TREAT[t] for t in adm.treatment_type]) * h.cost_f.values
            * (1 + 0.12 * emer) + 1850 * los) * rng.lognormal(0, 0.22, n)
    adm["treatment_cost"] = cost.round(2)
    rec = d.recovery_base.values - 6 * old - 4 * emer + 3 * (adm.treatment_type == "Surgery").values * (
        adm.department == "Orthopedics").values - 1.2 * (h.readm_f.values - 1) * 10 + rng.normal(0, 8, n)
    adm["recovery_score"] = np.clip(rec, 20, 100).round(0)
    # true 30-day readmission probability, and the model's risk score (noisy but informative)
    p = (d.readm_base.values * h.readm_f.values * (1 + 0.55 * old - 0.35 * kid + 0.25 * emer)
         * (1 + 0.35 * (los < 1.5)) * (1 + (70 - adm.recovery_score.values) / 120))
    p = np.clip(p, 0.01, 0.65)
    adm["_p_readm"] = p
    adm["readmission_risk"] = np.clip(p * rng.lognormal(0, 0.22, n) + rng.normal(0, 0.015, n), 0.01, 0.95).round(2)
    return adm


def make_readmissions(rng, adm: pd.DataFrame) -> pd.DataFrame:
    """Create the actual return stays: same patient, 1-30 days after discharge."""
    hit = rng.random(len(adm)) < adm._p_readm.values
    src = adm[hit & (adm.discharge_datetime < END - pd.Timedelta(days=31))].copy()
    gap = rng.gamma(2.2, 4.5, len(src)).clip(0.5, 29.5)
    re = src[["patient_key", "age_group", "gender", "region", "insurance_type", "department", "hospital_id"]].copy()
    re["admit_datetime"] = (src.discharge_datetime + pd.to_timedelta(gap, unit="D")).dt.floor("h").values
    re["visit_type"] = np.where(rng.random(len(re)) < 0.82, "Emergency", "Routine")
    re["treatment_type"] = rng.choice(["Medication", "Observation", "Therapy", "Surgery"], len(re), p=[0.45, 0.3, 0.15, 0.1])
    re["is_readmission"] = True
    re = add_outcomes(rng, re.reset_index(drop=True))
    return pd.concat([adm, re], ignore_index=True)


def make_appointments(rng, patients: pd.DataFrame, n=48_000) -> pd.DataFrame:
    p = patients.sample(n, replace=True, random_state=SEED + 1).reset_index(drop=True)
    age = p.age_group.values
    dept = np.where(age == "0-17", "Pediatrics",
                    rng.choice(["General Medicine", "Cardiology", "Orthopedics", "Neurology", "Oncology"], n,
                               p=[0.38, 0.22, 0.20, 0.12, 0.08]))
    days = pd.date_range("2024-01-02", "2025-12-30", freq="D")
    days = days[days.dayofweek < 5]
    appt_day = rng.choice(days.values, n)
    slot = rng.choice(np.arange(8, 17), n) * 60 + rng.choice([0, 15, 30, 45], n)
    appt_dt = pd.to_datetime(appt_day) + pd.to_timedelta(slot, unit="m")
    lead = np.clip(rng.gamma(1.4, 13, n), 0, 120).round().astype(int)
    lead = np.where(rng.random(n) < 0.12, 0, lead)                  # same-day bookings
    sms = rng.random(n) < np.where(age == "60+", 0.62, 0.74)
    region_h = {"North": "H01", "East": "H02", "South": "H03", "West": "H04"}
    hosp = np.where(rng.random(n) < 0.8, p.region.map(region_h).values, rng.choice(HOSPITALS.hospital_id, n))
    hosp = np.where((p.region.values == "East") & (rng.random(n) < 0.4), "H05", hosp)
    a = pd.DataFrame({"patient_key": p.patient_key, "age_group": age, "gender": p.gender,
                      "insurance_type": p.insurance_type, "department": dept, "hospital_id": hosp,
                      "appointment_datetime": appt_dt, "lead_time_days": lead, "sms_reminder": sms,
                      "appointment_type": rng.choice(["New patient", "Follow-up"], n, p=[0.38, 0.62])})
    a["booked_date"] = (a.appointment_datetime.dt.normalize() - pd.to_timedelta(a.lead_time_days, unit="D")).dt.date
    dow = a.appointment_datetime.dt.dayofweek.values
    pr = (0.085 + 0.0022 * np.minimum(lead, 60) + 0.07 * (~sms)
          + np.select([age == "18-30", age == "31-45", age == "60+", age == "0-17"], [0.07, 0.03, -0.035, -0.03], 0)
          + 0.035 * (p.insurance_type.values == "Self-pay") + 0.02 * (p.insurance_type.values == "Medicaid")
          + np.select([dow == 0, dow == 4], [0.025, 0.03], 0) - 0.03 * (a.appointment_type.values == "Follow-up")
          + 0.02 * (hosp == "H03") - 0.07 * (lead == 0))
    pr = np.clip(pr, 0.01, 0.6)
    u = rng.random(n)
    canc = 0.05 + 0.0008 * np.minimum(lead, 60)
    a["status"] = np.where(u < pr, "No-show", np.where(u < pr + canc, "Cancelled", "Attended"))
    return a.sort_values("appointment_datetime").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Raw export: the same data with the problems real hospital exports have
# ---------------------------------------------------------------------------
def dirty_admissions(rng, adm: pd.DataFrame) -> pd.DataFrame:
    d = adm.drop(columns=["_p_readm", "is_readmission", "region", "insurance_type"]).copy()
    n = len(d)
    d["admit_datetime"] = d.admit_datetime.dt.strftime("%Y-%m-%d %H:%M")
    d["discharge_datetime"] = d.discharge_datetime.dt.strftime("%Y-%m-%d %H:%M")
    us = rng.random(n) < 0.18                                   # a second system exports US-style dates
    for c in ["admit_datetime", "discharge_datetime"]:
        d.loc[us, c] = pd.to_datetime(d.loc[us, c]).dt.strftime("%m/%d/%Y %H:%M")
    swap = rng.random(n) < 0.004                                # admit/discharge entered the wrong way round
    d.loc[swap, ["admit_datetime", "discharge_datetime"]] = d.loc[swap, ["discharge_datetime", "admit_datetime"]].values
    d.loc[swap, "length_of_stay_days"] *= -1
    variants = {"Cardiology": ["cardiology", "CARDIOLOGY", "Cardio"], "General Medicine": ["Gen Med", "general medicine"],
                "Orthopedics": ["Orthopaedics", "orthopedics"], "Neurology": ["neurology "], "Pediatrics": ["Paediatrics"],
                "Oncology": ["oncology"]}
    m = rng.random(n) < 0.07
    d.loc[m, "department"] = [rng.choice(variants[x]) for x in d.loc[m, "department"]]
    g = rng.random(n)
    d["gender"] = np.where(g < 0.05, d.gender.str[0], np.where(g < 0.07, d.gender.str.lower(),
                           np.where(g < 0.075, "", d.gender)))
    txt = rng.random(n) < 0.10
    cost = d.treatment_cost.map(lambda v: f"{v:.2f}")
    cost[txt] = d.treatment_cost[txt].map(lambda v: f"${v:,.2f}")
    cost[rng.random(n) < 0.015] = ""
    d["treatment_cost"] = cost
    pct = rng.random(n) < 0.006                                 # risk typed as a percentage
    d.loc[pct, "readmission_risk"] = (d.loc[pct, "readmission_risk"] * 100).round(0)
    d.loc[rng.random(n) < 0.008, "age_group"] = ""
    kids = (d.department == "Pediatrics") & (rng.random(n) < 0.02)
    d.loc[kids, "age_group"] = "60+"                            # impossible combination to catch
    d.loc[rng.random(n) < 0.01, "recovery_score"] = np.nan
    d = d.sample(frac=1, random_state=SEED).reset_index(drop=True)
    d.insert(0, "admission_id", [f"A{i:06d}" for i in range(1, len(d) + 1)])
    dup = d.sample(frac=0.012, random_state=SEED)               # exact duplicate rows from a double export
    return pd.concat([d, dup]).sample(frac=1, random_state=SEED + 2).reset_index(drop=True)


def dirty_appointments(rng, a: pd.DataFrame) -> pd.DataFrame:
    d = a.copy()
    n = len(d)
    d.insert(0, "appointment_id", [f"AP{i:06d}" for i in range(1, n + 1)])
    d["appointment_datetime"] = d.appointment_datetime.dt.strftime("%Y-%m-%d %H:%M")
    st = rng.random(n)
    d["status"] = np.where((d.status == "No-show") & (st < 0.25), rng.choice(["No Show", "no-show", "NS"], n),
                           np.where((d.status == "Attended") & (st < 0.05), "attended", d.status))
    d["sms_reminder"] = np.where(rng.random(n) < 0.02, "", np.where(d.sms_reminder, "Yes", "No"))
    neg = rng.random(n) < 0.004                                  # booking date after the appointment
    d.loc[neg, "lead_time_days"] = -d.loc[neg, "lead_time_days"] - 1
    dup = d.sample(frac=0.01, random_state=SEED)
    return pd.concat([d, dup]).sample(frac=1, random_state=SEED + 3).reset_index(drop=True)


def main():
    rng = np.random.default_rng(SEED)
    RAW.mkdir(parents=True, exist_ok=True)
    patients = make_patients(rng)
    adm = add_outcomes(rng, make_admissions(rng, patients))
    adm = make_readmissions(rng, adm)
    adm = adm[adm.admit_datetime <= END].sort_values("admit_datetime").reset_index(drop=True)
    appts = make_appointments(rng, patients)

    HOSPITALS.drop(columns=["los_f", "readm_f", "cost_f"]).to_csv(RAW / "hospitals.csv", index=False)
    pr = patients.copy()
    pr.loc[rng.random(len(pr)) < 0.03, "insurance_type"] = pr.insurance_type.str.upper()
    pd.concat([pr, pr.sample(60, random_state=SEED)]).to_csv(RAW / "patients_raw.csv", index=False)
    dirty_admissions(rng, adm).to_csv(RAW / "admissions_raw.csv", index=False)
    dirty_appointments(rng, appts).to_csv(RAW / "appointments_raw.csv", index=False)
    print(f"patients {len(patients):,} · admissions {len(adm):,} (readmissions {adm.is_readmission.sum():,}) "
          f"· appointments {len(appts):,}")


if __name__ == "__main__":
    main()
