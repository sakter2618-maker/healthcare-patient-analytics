-- ============================================================================
-- Healthcare Patient Analytics — PostgreSQL schema (star schema)
-- Synthetic, de-identified data only. patient_key is a random ID, not a person.
--
--   dim_hospital ─┐                 ┌─ dim_patient
--   dim_department┼── fact_admission┤
--   dim_date ─────┘                 └─ (readmission flags derived from the stay sequence)
--   dim_hospital / dim_department / dim_patient ── fact_appointment
--
-- Run:  psql -d healthcare -f sql/01_schema.sql
-- ============================================================================
DROP SCHEMA IF EXISTS healthcare CASCADE;
CREATE SCHEMA healthcare;
SET search_path TO healthcare;

CREATE TABLE dim_hospital (
    hospital_id    varchar(4)  PRIMARY KEY,
    hospital_name  text        NOT NULL UNIQUE,
    region         text        NOT NULL CHECK (region IN ('North','South','East','West')),
    beds           int         NOT NULL CHECK (beds > 0),
    hospital_type  text        NOT NULL
);

CREATE TABLE dim_department (
    department_id  serial PRIMARY KEY,
    department     text   NOT NULL UNIQUE,
    service_line   text   NOT NULL            -- Medical / Surgical / Specialty / Children
);

CREATE TABLE dim_patient (
    patient_key    varchar(8) PRIMARY KEY,     -- synthetic, de-identified
    gender         text NOT NULL,
    age_group      text NOT NULL CHECK (age_group IN ('0-17','18-30','31-45','46-60','60+')),
    region         text NOT NULL,
    insurance_type text NOT NULL
);

CREATE TABLE dim_date (
    date_key     date PRIMARY KEY,
    year         int  NOT NULL,
    quarter      int  NOT NULL,
    month        int  NOT NULL,
    month_name   text NOT NULL,
    weekday      text NOT NULL,
    is_weekend   boolean NOT NULL,
    season       text NOT NULL
);

CREATE TABLE fact_admission (
    admission_id        varchar(8)  PRIMARY KEY,
    patient_key         varchar(8)  NOT NULL REFERENCES dim_patient,
    hospital_id         varchar(4)  NOT NULL REFERENCES dim_hospital,
    department_id       int         NOT NULL REFERENCES dim_department,
    admit_date          date        NOT NULL REFERENCES dim_date,
    admit_datetime      timestamp   NOT NULL,
    discharge_datetime  timestamp   NOT NULL,
    age_group           text        NOT NULL,          -- age at the time of the stay
    visit_type          text        NOT NULL CHECK (visit_type IN ('Emergency','Routine')),
    treatment_type      text        NOT NULL CHECK (treatment_type IN ('Surgery','Therapy','Medication','Observation')),
    length_of_stay_days numeric(5,1) NOT NULL CHECK (length_of_stay_days >= 0),
    treatment_cost      numeric(12,2) NOT NULL CHECK (treatment_cost >= 0),
    cost_imputed        boolean     NOT NULL DEFAULT false,
    recovery_score      numeric(5,1) CHECK (recovery_score BETWEEN 0 AND 100),
    readmission_risk    numeric(4,2) CHECK (readmission_risk BETWEEN 0 AND 1),
    is_readmission      boolean     NOT NULL,          -- this stay is a return within 30 days
    readmitted_30d      boolean,                       -- came back within 30 days; NULL = last 30 days of data (not yet observable)
    CHECK (discharge_datetime >= admit_datetime)
);

CREATE TABLE fact_appointment (
    appointment_id       varchar(8) PRIMARY KEY,
    patient_key          varchar(8) NOT NULL REFERENCES dim_patient,
    hospital_id          varchar(4) NOT NULL REFERENCES dim_hospital,
    department_id        int        NOT NULL REFERENCES dim_department,
    appointment_date     date       NOT NULL REFERENCES dim_date,
    appointment_datetime timestamp  NOT NULL,
    booked_date          date       NOT NULL,
    lead_time_days       int        NOT NULL CHECK (lead_time_days >= 0),
    appointment_type     text       NOT NULL,
    sms_reminder         text       NOT NULL CHECK (sms_reminder IN ('Yes','No','Unknown')),
    status               text       NOT NULL CHECK (status IN ('Attended','No-show','Cancelled'))
);

CREATE INDEX ix_adm_patient   ON fact_admission (patient_key, admit_datetime);
CREATE INDEX ix_adm_date      ON fact_admission (admit_date);
CREATE INDEX ix_adm_dept_hosp ON fact_admission (department_id, hospital_id);
CREATE INDEX ix_appt_date     ON fact_appointment (appointment_date);
CREATE INDEX ix_appt_status   ON fact_appointment (status);
