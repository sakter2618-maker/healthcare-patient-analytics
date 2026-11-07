"""Checks that the cleaned data is valid and the business answers are consistent."""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import metrics as m  # noqa: E402

D = m.load()
A, P = D["admissions"], D["appointments"]


def test_clean_admissions_are_valid():
    assert A.admission_id.is_unique
    assert set(A.department) == {"General Medicine", "Cardiology", "Orthopedics", "Neurology", "Oncology", "Pediatrics"}
    assert set(A.gender) <= {"Male", "Female", "Unknown"}
    assert (A.discharge_datetime >= A.admit_datetime).all()
    assert (A.length_of_stay_days >= 0).all() and A.treatment_cost.gt(0).all()
    assert A.readmission_risk.between(0, 1).all()
    assert not ((A.department == "Pediatrics") & (A.age_group == "60+")).any()


def test_readmission_flag_matches_stay_sequence():
    s = A.sort_values(["patient_key", "admit_datetime"])
    nxt = s.groupby("patient_key").admit_datetime.shift(-1)
    flag = (nxt - s.discharge_datetime).dt.total_seconds().between(0, 30 * 86400)
    obs = s.readmitted_30d.notna()
    assert (flag[obs].astype(float) == s.loc[obs, "readmitted_30d"]).all()
    # the last 30 days are not observable yet and must be excluded
    assert s.loc[s.discharge_datetime > A.admit_datetime.max() - pd.Timedelta(days=30), "readmitted_30d"].isna().all()


def test_appointments_are_valid():
    assert P.appointment_id.is_unique
    assert set(P.status) == {"Attended", "No-show", "Cancelled"}
    assert (P.lead_time_days >= 0).all()


def test_business_answers():
    ans = m.business_answers(D)
    assert len(ans) == 5
    dep = m.admissions_by_department(A)
    assert ans[0]["a"].startswith(dep.department[0])
    assert 5 < m.readmission_summary(A)["rate"] < 30
    assert 5 < m.noshow_summary(P)["rate"] < 30


def test_filters_shrink_data():
    one = m.filt(A, hospitals=["Riverside Community Hospital"])
    assert 0 < len(one) < len(A) and set(one.hospital_name) == {"Riverside Community Hospital"}
    q = m.filt(A, start="2025-01-01", end="2025-03-31", date_col="admit_datetime")
    assert q.admit_datetime.min() >= pd.Timestamp("2025-01-01")
