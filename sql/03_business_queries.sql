-- ============================================================================
-- Healthcare Patient Analytics — business questions in SQL (PostgreSQL)
-- Run:  psql -d healthcare -f sql/03_business_queries.sql
-- ============================================================================
SET search_path TO healthcare;

-- ---------------------------------------------------------------------------
-- Q1. Which department has the most admissions?
-- ---------------------------------------------------------------------------
SELECT d.department,
       count(*)                                              AS admissions,
       round(100.0 * count(*) / sum(count(*)) OVER (), 1)    AS share_pct,
       round(100.0 * avg((a.visit_type = 'Emergency')::int), 1) AS emergency_pct
FROM fact_admission a JOIN dim_department d USING (department_id)
GROUP BY d.department
ORDER BY admissions DESC;

-- ---------------------------------------------------------------------------
-- Q2. Which age group uses healthcare services the most? (stays + appointments)
-- ---------------------------------------------------------------------------
WITH stays AS (
    SELECT age_group, count(*) AS admissions, count(DISTINCT patient_key) AS patients
    FROM fact_admission GROUP BY age_group
), visits AS (
    SELECT p.age_group, count(*) AS appointments
    FROM fact_appointment f JOIN dim_patient p USING (patient_key) GROUP BY p.age_group
)
SELECT s.age_group, s.admissions, v.appointments,
       s.admissions + v.appointments                                         AS services,
       round(100.0 * (s.admissions + v.appointments) / sum(s.admissions + v.appointments) OVER (), 1) AS service_share_pct,
       round(s.admissions::numeric / s.patients, 2)                          AS admissions_per_patient
FROM stays s JOIN visits v USING (age_group)
ORDER BY services DESC;

-- ---------------------------------------------------------------------------
-- Q3. Which department has the highest average treatment cost?
-- ---------------------------------------------------------------------------
SELECT d.department,
       round(avg(treatment_cost), 0)                                   AS avg_cost,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY treatment_cost)::numeric, 0) AS median_cost,
       round(sum(treatment_cost) / nullif(sum(length_of_stay_days), 0), 0) AS cost_per_bed_day,
       round(sum(treatment_cost) / 1e6, 2)                             AS total_cost_musd
FROM fact_admission a JOIN dim_department d USING (department_id)
GROUP BY d.department
ORDER BY avg_cost DESC;

-- ---------------------------------------------------------------------------
-- Q4. What is the 30-day readmission rate?
-- Recomputed here from the stay sequence with LEAD(), independent of the Python flag.
-- ---------------------------------------------------------------------------
WITH seq AS (
    SELECT admission_id, patient_key, discharge_datetime, readmitted_30d,
           LEAD(admit_datetime) OVER (PARTITION BY patient_key ORDER BY admit_datetime) AS next_admit
    FROM fact_admission
)
SELECT count(*)                                                                      AS stays,
       -- COALESCE: a patient with no later stay was NOT readmitted (NULL would drop them from AVG)
       sum(coalesce(next_admit - discharge_datetime BETWEEN interval '0' AND interval '30 days', false)::int)
                                                                                     AS readmissions_sql,
       round(100.0 * avg(coalesce(next_admit - discharge_datetime BETWEEN interval '0' AND interval '30 days',
                                  false)::int), 1)                                   AS readmission_rate_pct,
       sum(readmitted_30d::int)                                                      AS readmissions_python  -- must match
FROM seq
-- the last 30 days of data are excluded: their readmission window is not yet complete
WHERE discharge_datetime <= (SELECT max(admit_datetime) FROM fact_admission) - interval '30 days';

-- ---------------------------------------------------------------------------
-- Q5. What is the appointment no-show rate?
-- ---------------------------------------------------------------------------
SELECT count(*)                                                        AS appointments,
       sum((status = 'No-show')::int)                                  AS no_shows,
       round(100.0 * avg((status = 'No-show')::int), 1)                AS noshow_rate_pct,
       round(100.0 * avg((status = 'Cancelled')::int), 1)              AS cancel_rate_pct
FROM fact_appointment;

-- ===========================================================================
-- Deeper analysis
-- ===========================================================================

-- 6. Monthly admissions with month-over-month change and a 3-month moving average
WITH m AS (
    SELECT date_trunc('month', admit_datetime)::date AS month, count(*) AS admissions
    FROM fact_admission GROUP BY 1
)
SELECT month, admissions,
       admissions - LAG(admissions) OVER (ORDER BY month)                       AS mom_change,
       round(avg(admissions) OVER (ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 0) AS moving_avg_3m
FROM m ORDER BY month;

-- 7. Seasonality: average admissions per month by season
SELECT dt.season, round(count(*)::numeric / count(DISTINCT date_trunc('month', a.admit_datetime)), 0) AS admissions_per_month
FROM fact_admission a JOIN dim_date dt ON dt.date_key = a.admit_date
GROUP BY dt.season ORDER BY admissions_per_month DESC;

-- 8. Hospital performance scorecard with a rank on each measure
SELECT h.hospital_name, h.hospital_type, count(*) AS admissions,
       round(avg(a.length_of_stay_days), 2)                              AS avg_los,
       round(100.0 * avg(a.readmitted_30d::int), 1)                      AS readmission_pct,
       round(avg(a.recovery_score), 1)                                   AS avg_recovery,
       round(avg(a.treatment_cost), 0)                                   AS avg_cost,
       RANK() OVER (ORDER BY avg(a.readmitted_30d::int))                 AS readmission_rank,
       RANK() OVER (ORDER BY avg(a.length_of_stay_days))                 AS los_rank
FROM fact_admission a JOIN dim_hospital h USING (hospital_id)
GROUP BY h.hospital_name, h.hospital_type
ORDER BY readmission_pct;

-- 9. Length of stay: average, median and 90th percentile by department
SELECT d.department,
       round(avg(length_of_stay_days), 2) AS avg_los,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY length_of_stay_days) AS median_los,
       percentile_cont(0.9) WITHIN GROUP (ORDER BY length_of_stay_days) AS p90_los
FROM fact_admission a JOIN dim_department d USING (department_id)
GROUP BY d.department ORDER BY avg_los DESC;

-- 10. Long stays (> 10 days): where do they happen?
SELECT h.hospital_name, d.department, count(*) AS long_stays,
       round(100.0 * count(*) / sum(count(*)) OVER (), 1) AS share_of_long_stays
FROM fact_admission a JOIN dim_hospital h USING (hospital_id) JOIN dim_department d USING (department_id)
WHERE length_of_stay_days > 10
GROUP BY h.hospital_name, d.department
ORDER BY long_stays DESC LIMIT 10;

-- 11. Cost by department and treatment type (pivot with FILTER)
SELECT d.department,
       round(avg(treatment_cost) FILTER (WHERE treatment_type = 'Surgery'), 0)     AS surgery,
       round(avg(treatment_cost) FILTER (WHERE treatment_type = 'Therapy'), 0)     AS therapy,
       round(avg(treatment_cost) FILTER (WHERE treatment_type = 'Medication'), 0)  AS medication,
       round(avg(treatment_cost) FILTER (WHERE treatment_type = 'Observation'), 0) AS observation
FROM fact_admission a JOIN dim_department d USING (department_id)
GROUP BY d.department ORDER BY surgery DESC NULLS LAST;

-- 12. Readmission rate by age group and visit type
SELECT age_group, visit_type, count(*) AS stays,
       round(100.0 * avg(readmitted_30d::int), 1) AS readmission_pct
FROM fact_admission GROUP BY age_group, visit_type ORDER BY age_group, visit_type;

-- 13. Does the risk score work? Actual readmission rate by predicted risk band
SELECT CASE WHEN readmission_risk < 0.10 THEN '1. <10%'
            WHEN readmission_risk < 0.20 THEN '2. 10-20%'
            WHEN readmission_risk < 0.30 THEN '3. 20-30%'
            ELSE '4. 30%+' END                         AS risk_band,
       count(*)                                         AS stays,
       round(100.0 * avg(readmitted_30d::int), 1)       AS actual_readmission_pct
FROM fact_admission GROUP BY 1 ORDER BY 1;

-- 14. Frequent patients: 3+ stays (candidates for care management)
SELECT p.age_group, count(*) AS patients, round(avg(n_stays), 1) AS avg_stays
FROM (SELECT patient_key, count(*) AS n_stays FROM fact_admission GROUP BY patient_key HAVING count(*) >= 3) f
JOIN dim_patient p USING (patient_key)
GROUP BY p.age_group ORDER BY patients DESC;

-- 15. No-show rate by booking lead time
SELECT CASE WHEN lead_time_days = 0 THEN '1. Same day'
            WHEN lead_time_days <= 7 THEN '2. 1-7 days'
            WHEN lead_time_days <= 14 THEN '3. 8-14 days'
            WHEN lead_time_days <= 30 THEN '4. 15-30 days'
            WHEN lead_time_days <= 60 THEN '5. 31-60 days' ELSE '6. 60+ days' END AS lead_time_band,
       count(*) AS appointments,
       round(100.0 * avg((status = 'No-show')::int), 1) AS noshow_pct
FROM fact_appointment GROUP BY 1 ORDER BY 1;

-- 16. Do SMS reminders reduce no-shows?
SELECT sms_reminder, count(*) AS appointments,
       round(100.0 * avg((status = 'No-show')::int), 1) AS noshow_pct
FROM fact_appointment WHERE sms_reminder <> 'Unknown'
GROUP BY sms_reminder;

-- 17. No-show rate by weekday and age group
SELECT dt.weekday, p.age_group,
       round(100.0 * avg((f.status = 'No-show')::int), 1) AS noshow_pct
FROM fact_appointment f JOIN dim_date dt ON dt.date_key = f.appointment_date
JOIN dim_patient p USING (patient_key)
GROUP BY dt.weekday, p.age_group
ORDER BY noshow_pct DESC LIMIT 10;

-- 18. Department summary combining inpatient and outpatient activity
SELECT d.department,
       coalesce(i.admissions, 0) AS admissions, coalesce(o.appointments, 0) AS appointments,
       i.readmission_pct, o.noshow_pct
FROM dim_department d
LEFT JOIN (SELECT department_id, count(*) AS admissions, round(100.0 * avg(readmitted_30d::int), 1) AS readmission_pct
           FROM fact_admission GROUP BY department_id) i USING (department_id)
LEFT JOIN (SELECT department_id, count(*) AS appointments, round(100.0 * avg((status = 'No-show')::int), 1) AS noshow_pct
           FROM fact_appointment GROUP BY department_id) o USING (department_id)
ORDER BY admissions DESC;
