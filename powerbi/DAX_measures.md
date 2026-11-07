# DAX measures — Healthcare Dashboard

Create a table called **_Measures** (Home → Enter data → empty table) and add each measure below
(Modeling → New measure). Format % measures as Percentage with 1 decimal.

## Volume
```DAX
Admissions = COUNTROWS ( fact_admission )
Patients = DISTINCTCOUNT ( fact_admission[patient_key] )
Emergency Admissions = CALCULATE ( [Admissions], fact_admission[visit_type] = "Emergency" )
Emergency % = DIVIDE ( [Emergency Admissions], [Admissions] )
Admissions per Patient = DIVIDE ( [Admissions], [Patients] )
```

## Length of stay and cost
```DAX
Avg LOS (days) = AVERAGE ( fact_admission[length_of_stay_days] )
Median LOS (days) = MEDIAN ( fact_admission[length_of_stay_days] )
Long Stays (>10 days) = CALCULATE ( [Admissions], fact_admission[length_of_stay_days] > 10 )
Total Cost = SUM ( fact_admission[treatment_cost] )
Avg Cost per Stay = DIVIDE ( [Total Cost], [Admissions] )
Cost per Bed Day = DIVIDE ( [Total Cost], SUM ( fact_admission[length_of_stay_days] ) )
```

## Readmissions
```DAX
Readmissions (30d) = CALCULATE ( [Admissions], fact_admission[readmitted_30d] = TRUE () )
Observable Stays = CALCULATE ( [Admissions], NOT ISBLANK ( fact_admission[readmitted_30d] ) )   -- excludes the last 30 days
Readmission Rate = DIVIDE ( [Readmissions (30d)], [Observable Stays] )
Avg Predicted Risk = AVERAGE ( fact_admission[readmission_risk] )
High-Risk Stays = CALCULATE ( [Admissions], fact_admission[readmission_risk] >= 0.25 )
Readmission Rate vs Target = [Readmission Rate] - 0.14        -- 14% target; change to your own
```

## Recovery
```DAX
Avg Recovery Score = AVERAGE ( fact_admission[recovery_score] )
```

## Appointments
```DAX
Appointments = COUNTROWS ( fact_appointment )
No-shows = CALCULATE ( [Appointments], fact_appointment[status] = "No-show" )
No-show Rate = DIVIDE ( [No-shows], [Appointments] )
Cancellation Rate = DIVIDE ( CALCULATE ( [Appointments], fact_appointment[status] = "Cancelled" ), [Appointments] )
No-show Rate (SMS) = CALCULATE ( [No-show Rate], fact_appointment[sms_reminder] = "Yes" )
No-show Rate (no SMS) = CALCULATE ( [No-show Rate], fact_appointment[sms_reminder] = "No" )
```

## Time intelligence (needs dim_date marked as a date table)
```DAX
Admissions LY = CALCULATE ( [Admissions], SAMEPERIODLASTYEAR ( dim_date[date] ) )
Admissions YoY % = DIVIDE ( [Admissions] - [Admissions LY], [Admissions LY] )
Admissions MoM % =
VAR prev = CALCULATE ( [Admissions], DATEADD ( dim_date[date], -1, MONTH ) )
RETURN DIVIDE ( [Admissions] - prev, prev )
Admissions 3M Avg =
AVERAGEX ( DATESINPERIOD ( dim_date[date], MAX ( dim_date[date] ), -3, MONTH ), [Admissions] )
```

## Ranking & labels
```DAX
Hospital Rank (Readmission) = RANKX ( ALL ( dim_hospital[hospital_name] ), [Readmission Rate], , ASC )
Top Department =
FIRSTNONBLANK ( TOPN ( 1, VALUES ( dim_department[department] ), [Admissions] ), 1 )
KPI Title Readmission = "30-day readmission: " & FORMAT ( [Readmission Rate], "0.0%" )
```
