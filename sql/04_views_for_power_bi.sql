-- ============================================================================
-- Reporting views (Power BI can connect to these directly with the PostgreSQL connector)
-- Run:  psql -d healthcare -f sql/04_views_for_power_bi.sql
-- ============================================================================
SET search_path TO healthcare;

CREATE OR REPLACE VIEW v_admissions AS
SELECT a.admission_id, a.patient_key, a.admit_date, a.admit_datetime, a.discharge_datetime,
       h.hospital_name, h.region AS hospital_region, h.hospital_type,
       d.department, d.service_line, a.age_group, p.gender, p.insurance_type,
       a.visit_type, a.treatment_type, a.length_of_stay_days, a.treatment_cost, a.cost_imputed,
       a.recovery_score, a.readmission_risk, a.is_readmission, a.readmitted_30d
FROM fact_admission a
JOIN dim_hospital h USING (hospital_id)
JOIN dim_department d USING (department_id)
JOIN dim_patient p USING (patient_key);

CREATE OR REPLACE VIEW v_appointments AS
SELECT f.appointment_id, f.patient_key, f.appointment_date, f.appointment_datetime, f.booked_date,
       f.lead_time_days, h.hospital_name, d.department, p.age_group, p.gender, p.insurance_type,
       f.appointment_type, f.sms_reminder, f.status, (f.status = 'No-show') AS no_show,
       dt.weekday
FROM fact_appointment f
JOIN dim_hospital h USING (hospital_id)
JOIN dim_department d USING (department_id)
JOIN dim_patient p USING (patient_key)
JOIN dim_date dt ON dt.date_key = f.appointment_date;

CREATE OR REPLACE VIEW v_hospital_scorecard AS
SELECT h.hospital_name, h.hospital_type, h.beds,
       count(*)                                   AS admissions,
       round(avg(a.length_of_stay_days), 2)       AS avg_los,
       round(100.0 * avg(a.readmitted_30d::int), 1) AS readmission_pct,
       round(avg(a.recovery_score), 1)            AS avg_recovery,
       round(avg(a.treatment_cost), 0)            AS avg_cost
FROM fact_admission a JOIN dim_hospital h USING (hospital_id)
GROUP BY h.hospital_name, h.hospital_type, h.beds;

CREATE OR REPLACE VIEW v_monthly_kpis AS
SELECT date_trunc('month', admit_datetime)::date      AS month,
       count(*)                                       AS admissions,
       round(avg(length_of_stay_days), 2)             AS avg_los,
       round(avg(treatment_cost), 0)                  AS avg_cost,
       round(100.0 * avg(readmitted_30d::int), 1)     AS readmission_pct
FROM fact_admission GROUP BY 1;

SELECT 'views created' AS status;
