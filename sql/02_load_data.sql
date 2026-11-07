-- ============================================================================
-- Load the cleaned CSVs (output of src/clean_data.py) into the star schema.
-- Run from the repository root so the relative paths work:
--     psql -d healthcare -f sql/02_load_data.sql
-- ============================================================================
SET search_path TO healthcare;

-- staging tables mirror the CSV files exactly
CREATE TEMP TABLE stg_hospitals (hospital_id text, hospital_name text, region text, beds int, hospital_type text);
CREATE TEMP TABLE stg_patients  (patient_key text, gender text, age_group text, region text, insurance_type text);
CREATE TEMP TABLE stg_admissions (
    admission_id text, patient_key text, age_group text, gender text, department text, hospital_id text,
    admit_datetime timestamp, visit_type text, treatment_type text, length_of_stay_days numeric,
    discharge_datetime timestamp, treatment_cost numeric, recovery_score numeric, readmission_risk numeric,
    cost_imputed boolean, region text, insurance_type text, is_readmission boolean, readmitted_30d boolean,
    admit_month text);
CREATE TEMP TABLE stg_appointments (
    appointment_id text, patient_key text, age_group text, gender text, insurance_type text, department text,
    hospital_id text, appointment_datetime timestamp, lead_time_days int, sms_reminder text,
    appointment_type text, booked_date date, status text, no_show boolean, lead_time_band text,
    weekday text, appt_month text);

\copy stg_hospitals    FROM 'data/clean/hospitals.csv'    WITH (FORMAT csv, HEADER true)
\copy stg_patients     FROM 'data/clean/patients.csv'     WITH (FORMAT csv, HEADER true)
\copy stg_admissions   FROM 'data/clean/admissions.csv'   WITH (FORMAT csv, HEADER true)
\copy stg_appointments FROM 'data/clean/appointments.csv' WITH (FORMAT csv, HEADER true)

INSERT INTO dim_hospital SELECT * FROM stg_hospitals;
INSERT INTO dim_patient  SELECT * FROM stg_patients;

INSERT INTO dim_department (department, service_line)
SELECT department,
       CASE department WHEN 'Orthopedics' THEN 'Surgical'
                       WHEN 'Pediatrics'  THEN 'Children'
                       WHEN 'General Medicine' THEN 'Medical'
                       ELSE 'Specialty' END
FROM (SELECT department FROM stg_admissions UNION SELECT department FROM stg_appointments) d
ORDER BY department;

INSERT INTO dim_date
SELECT d::date, EXTRACT(year FROM d), EXTRACT(quarter FROM d), EXTRACT(month FROM d),
       to_char(d, 'Mon'), to_char(d, 'FMDay'), EXTRACT(isodow FROM d) >= 6,
       CASE WHEN EXTRACT(month FROM d) IN (12,1,2) THEN 'Winter'
            WHEN EXTRACT(month FROM d) IN (3,4,5)  THEN 'Spring'
            WHEN EXTRACT(month FROM d) IN (6,7,8)  THEN 'Summer' ELSE 'Autumn' END
FROM generate_series('2024-01-01'::date, '2026-01-31'::date, interval '1 day') d;

INSERT INTO fact_admission
SELECT s.admission_id, s.patient_key, s.hospital_id, dd.department_id, s.admit_datetime::date,
       s.admit_datetime, s.discharge_datetime, s.age_group, s.visit_type, s.treatment_type,
       s.length_of_stay_days, s.treatment_cost, s.cost_imputed, s.recovery_score, s.readmission_risk,
       s.is_readmission, s.readmitted_30d
FROM stg_admissions s JOIN dim_department dd USING (department);

INSERT INTO fact_appointment
SELECT s.appointment_id, s.patient_key, s.hospital_id, dd.department_id, s.appointment_datetime::date,
       s.appointment_datetime, s.booked_date, s.lead_time_days, s.appointment_type, s.sms_reminder, s.status
FROM stg_appointments s JOIN dim_department dd USING (department);

ANALYZE;

-- row counts as a quick check
SELECT 'dim_hospital' AS table_name, count(*) FROM dim_hospital
UNION ALL SELECT 'dim_patient', count(*) FROM dim_patient
UNION ALL SELECT 'dim_department', count(*) FROM dim_department
UNION ALL SELECT 'fact_admission', count(*) FROM fact_admission
UNION ALL SELECT 'fact_appointment', count(*) FROM fact_appointment;
