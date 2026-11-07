"""
metrics.py — every number on the dashboard and in the report comes from these functions.

Business questions answered
    Q1  Which department has the most admissions?            admissions_by_department()
    Q2  Which age group uses healthcare services the most?    demographics()
    Q3  Which department has the highest average cost?        cost_by_department()
    Q4  What is the 30-day readmission rate?                  readmission_summary()
    Q5  What is the appointment no-show rate?                 noshow_summary()

Analyses: admissions trend, hospital performance, length of stay, treatment cost,
readmissions, department mix, demographics, appointments & no-shows.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "clean"
AGE_ORDER = ["0-17", "18-30", "31-45", "46-60", "60+"]
BAND_ORDER = ["Same day", "1-7 days", "8-14 days", "15-30 days", "31-60 days", "60+ days"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]


@lru_cache(maxsize=1)
def load() -> dict[str, pd.DataFrame]:
    h = pd.read_csv(CLEAN / "hospitals.csv")
    a = pd.read_csv(CLEAN / "admissions.csv", parse_dates=["admit_datetime", "discharge_datetime"])
    p = pd.read_csv(CLEAN / "appointments.csv", parse_dates=["appointment_datetime", "booked_date"])
    pt = pd.read_csv(CLEAN / "patients.csv")
    a = a.merge(h[["hospital_id", "hospital_name"]], on="hospital_id", how="left")
    p = p.merge(h[["hospital_id", "hospital_name"]], on="hospital_id", how="left")
    a["readmitted_30d"] = a.readmitted_30d.map({True: 1.0, False: 0.0, "True": 1.0, "False": 0.0})
    for df in (a, p, pt):
        df["age_group"] = pd.Categorical(df.age_group, AGE_ORDER, ordered=True)
    p["lead_time_band"] = pd.Categorical(p.lead_time_band, BAND_ORDER, ordered=True)
    return {"hospitals": h, "admissions": a, "appointments": p, "patients": pt}


def filt(df: pd.DataFrame, hospitals=None, departments=None, start=None, end=None, date_col=None) -> pd.DataFrame:
    m = pd.Series(True, index=df.index)
    if hospitals:
        m &= df.hospital_name.isin(hospitals)
    if departments:
        m &= df.department.isin(departments)
    if date_col and start is not None:
        m &= df[date_col] >= pd.Timestamp(start)
    if date_col and end is not None:
        m &= df[date_col] < pd.Timestamp(end) + pd.Timedelta(days=1)
    return df[m]


# --------------------------------------------------------------------------- KPIs
def kpis(a: pd.DataFrame, p: pd.DataFrame) -> dict:
    return dict(
        admissions=len(a), patients=a.patient_key.nunique(),
        avg_los=a.length_of_stay_days.mean(), median_los=a.length_of_stay_days.median(),
        avg_cost=a.treatment_cost.mean(), total_cost=a.treatment_cost.sum(),
        readmission_rate=100 * a.readmitted_30d.mean(), emergency_share=100 * (a.visit_type == "Emergency").mean(),
        avg_recovery=a.recovery_score.mean(),
        appointments=len(p), noshow_rate=100 * p.no_show.mean(),
        cancel_rate=100 * (p.status == "Cancelled").mean(),
    )


def monthly(a: pd.DataFrame) -> pd.DataFrame:
    g = a.groupby(a.admit_datetime.dt.to_period("M"))
    out = g.agg(admissions=("admission_id", "size"), emergency=("visit_type", lambda s: (s == "Emergency").sum()),
                readmission_rate=("readmitted_30d", "mean"), avg_los=("length_of_stay_days", "mean"),
                avg_cost=("treatment_cost", "mean")).reset_index()
    out["month"] = out.admit_datetime.dt.to_timestamp()
    out["readmission_rate"] *= 100
    return out.drop(columns="admit_datetime")


def seasonality(a: pd.DataFrame) -> pd.DataFrame:
    s = a.groupby(a.admit_datetime.dt.month).size()
    return pd.DataFrame({"month": s.index, "admissions_per_month": s.values / a.admit_datetime.dt.year.nunique()})


# --------------------------------------------------------------------------- departments
def admissions_by_department(a: pd.DataFrame) -> pd.DataFrame:
    g = a.groupby("department").agg(admissions=("admission_id", "size"),
                                    emergency_share=("visit_type", lambda s: 100 * (s == "Emergency").mean()),
                                    avg_los=("length_of_stay_days", "mean"), avg_cost=("treatment_cost", "mean"),
                                    readmission_rate=("readmitted_30d", lambda s: 100 * s.mean()),
                                    avg_recovery=("recovery_score", "mean"))
    g["share"] = 100 * g.admissions / g.admissions.sum()
    return g.sort_values("admissions", ascending=False).reset_index()


def cost_by_department(a: pd.DataFrame) -> pd.DataFrame:
    g = a.groupby("department").treatment_cost.agg(avg_cost="mean", median_cost="median",
                                                   total_cost="sum", stays="size")
    g["cost_per_day"] = (a.groupby("department").treatment_cost.sum()
                         / a.groupby("department").length_of_stay_days.sum().clip(lower=0.1))
    return g.sort_values("avg_cost", ascending=False).reset_index()


def cost_by_treatment(a: pd.DataFrame) -> pd.DataFrame:
    return (a.groupby(["department", "treatment_type"]).treatment_cost.mean().round(0)
            .unstack().reindex(columns=["Surgery", "Therapy", "Medication", "Observation"]))


# --------------------------------------------------------------------------- hospitals
def hospital_performance(a: pd.DataFrame, p: pd.DataFrame, h: pd.DataFrame) -> pd.DataFrame:
    g = a.groupby("hospital_name").agg(admissions=("admission_id", "size"),
                                       avg_los=("length_of_stay_days", "mean"),
                                       readmission_rate=("readmitted_30d", lambda s: 100 * s.mean()),
                                       avg_recovery=("recovery_score", "mean"),
                                       avg_cost=("treatment_cost", "mean"))
    g["noshow_rate"] = p.groupby("hospital_name").no_show.mean() * 100
    g = g.join(h.set_index("hospital_name")[["region", "beds", "hospital_type"]])
    # relative performance score (50 = weakest of the five, 100 = best): lower readmissions, LOS and
    # no-shows and higher recovery score are better
    def scaled(col, good_high):
        x = g[col]
        r = (x - x.min()) / (x.max() - x.min() or 1)
        return r if good_high else 1 - r
    g["performance_score"] = (50 + 50 * (0.35 * scaled("readmission_rate", False) + 0.25 * scaled("avg_los", False)
                                     + 0.25 * scaled("avg_recovery", True) + 0.15 * scaled("noshow_rate", False))).round(0)
    return g.sort_values("performance_score", ascending=False).reset_index()


# --------------------------------------------------------------------------- LOS
def los_distribution(a: pd.DataFrame) -> pd.DataFrame:
    bins = [-0.01, 1, 3, 5, 7, 10, 99]
    labels = ["≤1 day", "1-3 days", "3-5 days", "5-7 days", "7-10 days", "10+ days"]
    c = pd.cut(a.length_of_stay_days, bins, labels=labels).value_counts().reindex(labels)
    return pd.DataFrame({"band": labels, "stays": c.values, "share": 100 * c.values / len(a)})


def los_by(a: pd.DataFrame, col: str) -> pd.DataFrame:
    return (a.groupby(col, observed=True).length_of_stay_days.agg(avg_los="mean", median_los="median",
                                                                 p90_los=lambda s: s.quantile(0.9)).reset_index())


# --------------------------------------------------------------------------- readmissions
def readmission_summary(a: pd.DataFrame) -> dict:
    a = a[a.readmitted_30d.notna()]          # only stays whose 30-day window is fully observed
    hi = a.readmission_risk >= 0.25
    return dict(rate=100 * a.readmitted_30d.mean(), readmissions=int(a.readmitted_30d.sum()),
                high_risk_share=100 * hi.mean(),
                rate_high_risk=100 * a.loc[hi, "readmitted_30d"].mean(),
                rate_low_risk=100 * a.loc[~hi, "readmitted_30d"].mean(),
                emergency_rate=100 * a.loc[a.visit_type == "Emergency", "readmitted_30d"].mean(),
                routine_rate=100 * a.loc[a.visit_type == "Routine", "readmitted_30d"].mean())


def readmission_by(a: pd.DataFrame, col: str) -> pd.DataFrame:
    return (a.groupby(col, observed=True).agg(stays=("admission_id", "size"),
                                             readmission_rate=("readmitted_30d", lambda s: 100 * s.mean()),
                                             avg_risk=("readmission_risk", lambda s: 100 * s.mean()))
            .reset_index())


def risk_calibration(a: pd.DataFrame) -> pd.DataFrame:
    a = a[a.readmitted_30d.notna()]
    bands = pd.cut(a.readmission_risk, [0, 0.1, 0.2, 0.3, 0.4, 1.0],
                   labels=["<10%", "10-20%", "20-30%", "30-40%", "40%+"])
    g = a.groupby(bands, observed=True).agg(stays=("admission_id", "size"),
                                            actual=("readmitted_30d", lambda s: 100 * s.mean()))
    return g.reset_index().rename(columns={"readmission_risk": "risk_band"})


# --------------------------------------------------------------------------- demographics
def demographics(a: pd.DataFrame, p: pd.DataFrame) -> pd.DataFrame:
    g = a.groupby("age_group", observed=True).agg(admissions=("admission_id", "size"),
                                                  patients=("patient_key", "nunique"),
                                                  avg_cost=("treatment_cost", "mean"),
                                                  avg_los=("length_of_stay_days", "mean"),
                                                  readmission_rate=("readmitted_30d", lambda s: 100 * s.mean()))
    g["appointments"] = p.groupby("age_group", observed=True).size()
    g["services"] = g.admissions + g.appointments
    g["service_share"] = 100 * g.services / g.services.sum()
    g["admissions_per_patient"] = g.admissions / g.patients
    return g.reset_index()


def gender_split(a: pd.DataFrame) -> pd.DataFrame:
    return a.groupby("gender").size().rename("admissions").reset_index()


def insurance_mix(a: pd.DataFrame) -> pd.DataFrame:
    return (a.groupby("insurance_type").agg(admissions=("admission_id", "size"),
                                            avg_cost=("treatment_cost", "mean")).reset_index()
            .sort_values("admissions", ascending=False))


# --------------------------------------------------------------------------- appointments
def noshow_summary(p: pd.DataFrame) -> dict:
    sms = p[p.sms_reminder.isin(["Yes", "No"])]
    by = sms.groupby("sms_reminder").no_show.mean() * 100
    long = p.lead_time_days > 30
    return dict(rate=100 * p.no_show.mean(), no_shows=int(p.no_show.sum()),
                cancel_rate=100 * (p.status == "Cancelled").mean(),
                sms_yes=by.get("Yes", np.nan), sms_no=by.get("No", np.nan),
                long_lead=100 * p.loc[long, "no_show"].mean(), short_lead=100 * p.loc[~long, "no_show"].mean(),
                missed_slots_per_week=p.no_show.sum() / max(p.appointment_datetime.dt.to_period("W").nunique(), 1))


def noshow_by(p: pd.DataFrame, col: str, order=None) -> pd.DataFrame:
    g = (p.groupby(col, observed=True).agg(appointments=("appointment_id", "size"),
                                          noshow_rate=("no_show", lambda s: 100 * s.mean()))
         .reset_index())
    if order:
        g[col] = pd.Categorical(g[col], order, ordered=True)
        g = g.sort_values(col)
    return g


def status_mix(p: pd.DataFrame) -> pd.DataFrame:
    return p.status.value_counts().rename_axis("status").reset_index(name="appointments")


def appointments_monthly(p: pd.DataFrame) -> pd.DataFrame:
    g = p.groupby(p.appointment_datetime.dt.to_period("M")).agg(
        appointments=("appointment_id", "size"), noshow_rate=("no_show", lambda s: 100 * s.mean())).reset_index()
    g["month"] = g.appointment_datetime.dt.to_timestamp()
    return g.drop(columns="appointment_datetime")


# --------------------------------------------------------------------------- answers
def business_answers(d: dict | None = None) -> list[dict]:
    d = d or load()
    a, p = d["admissions"], d["appointments"]
    dep = admissions_by_department(a)
    cost = cost_by_department(a)
    demo = demographics(a, p).sort_values("services", ascending=False)
    r = readmission_summary(a)
    n = noshow_summary(p)
    top_age = demo.iloc[0]
    return [
        dict(q="Which department has the most admissions?",
             a=f"{dep.department[0]}: {dep.admissions[0]:,} stays ({dep.share[0]:.1f}%)",
             d=f"Then {dep.department[1]} ({dep.admissions[1]:,}) and {dep.department[2]} ({dep.admissions[2]:,})."),
        dict(q="Which age group uses healthcare services the most?",
             a=f"{top_age.age_group}: {top_age.service_share:.1f}% of all services",
             d=f"{int(top_age.admissions):,} admissions and {int(top_age.appointments):,} appointments; "
               f"{top_age.admissions_per_patient:.2f} admissions per patient."),
        dict(q="Which department has the highest average treatment cost?",
             a=f"{cost.department[0]}: ${cost.avg_cost[0]:,.0f} per stay",
             d=f"{cost.avg_cost[0] / cost.avg_cost.iloc[-1]:.1f}× the lowest ({cost.department.iloc[-1]}, "
               f"${cost.avg_cost.iloc[-1]:,.0f})."),
        dict(q="What is the 30-day readmission rate?",
             a=f"{r['rate']:.1f}% ({r['readmissions']:,} stays)",
             d=f"High-risk patients (score ≥ 25%) come back {r['rate_high_risk']:.1f}% of the time vs "
               f"{r['rate_low_risk']:.1f}% for the rest."),
        dict(q="What is the appointment no-show rate?",
             a=f"{n['rate']:.1f}% ({n['no_shows']:,} missed visits)",
             d=f"{n['sms_no']:.1f}% without an SMS reminder vs {n['sms_yes']:.1f}% with one; "
               f"{n['long_lead']:.1f}% when booked more than 30 days ahead."),
    ]
