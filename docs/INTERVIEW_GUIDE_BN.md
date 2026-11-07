# ইন্টারভিউ গাইড — Healthcare Patient Analytics (বাংলা)

এই গাইড পড়ে আপনি নিজের ভাষায় পুরো প্রজেক্ট বুঝিয়ে বলতে পারবেন। ইন্টারভিউতে উত্তর দেবেন **ইংরেজিতে**,
তাই প্রতিটা অংশে একটা ছোট ইংরেজি উত্তরও দেওয়া আছে।

---

## ১. ৩০ সেকেন্ডে প্রজেক্ট পরিচয় (Elevator pitch)

**বাংলায় ধারণা:** ৫টা হাসপাতালের ২ বছরের ডেটা নিয়ে কাজ করেছি। Python দিয়ে নোংরা ডেটা পরিষ্কার
করেছি, PostgreSQL-এ ডেটাবেস বানিয়েছি, Excel আর Power BI-এর জন্য রিপোর্ট বানিয়েছি, আর একটা লাইভ
ড্যাশবোর্ড বানিয়েছি। ডেটা পুরোপুরি synthetic, কোনো আসল রোগীর তথ্য নেই।

**English:**
> "I built an end-to-end healthcare analytics project on a synthetic, de-identified dataset of 5 hospitals
> over two years — about 21,700 inpatient stays and 48,000 appointments. I cleaned the raw export in Python,
> modelled it as a PostgreSQL star schema, answered the business questions in SQL, built an Excel cleaning
> workbook and a Power BI kit, and published a 7-page interactive dashboard. The main findings were that one
> hospital readmits patients far more often than the others, patients over 60 drive almost a third of all
> activity, and no-shows climb steeply when appointments are booked far in advance."

---

## ২. কেন synthetic ডেটা? (প্রায়ই জিজ্ঞেস করে)

* আসল রোগীর ডেটা **HIPAA** আইনের অধীনে সুরক্ষিত, পোর্টফোলিওতে ব্যবহার করা যায় না।
* তাই একটা Python স্ক্রিপ্ট (`generate_data.py`) দিয়ে বাস্তবসম্মত প্যাটার্নওয়ালা ডেটা বানিয়েছি। নির্দিষ্ট seed
  ব্যবহার করেছি, তাই যে কেউ চালালে হুবহু একই ডেটা পাবে।
* যে নমুনা ফাইল ছিল, তাতে Hospital বা Appointment-এর কোনো কলাম ছিল না, আর সংখ্যাগুলো ছিল এলোমেলো।
  তাই ওই ফাইলের কলামগুলো রেখে বাকি টেবিলগুলো যোগ করেছি।

**English:** "Real patient data is protected under HIPAA, so I generated a synthetic, de-identified dataset
with a fixed random seed. It keeps realistic relationships — older patients stay longer, long booking lead
times increase no-shows — so the analysis techniques are the same as on real data."

---

## ৩. ডেটা ক্লিনিং — কী কী সমস্যা ছিল

| সমস্যা | কী করেছি | কেন |
|---|---|---|
| একই রো দুবার (double export) | মুছে দিয়েছি | না মুছলে admission বেশি গোনা হতো |
| Department-এর বানান আলাদা (Cardio, Gen Med) | একটা নামে মিলিয়েছি | না হলে একই বিভাগ দুবার দেখাত |
| দুই রকম তারিখ (2024-03-05 আর 03/05/2024) | দুটোই পড়ে এক ফরম্যাটে এনেছি | দুটো সিস্টেম থেকে ডেটা আসে |
| Discharge-এর তারিখ Admit-এর আগে | তারিখ দুটো উল্টে ঠিক করেছি | থাকার দিন নেগেটিভ হচ্ছিল |
| খরচ লেখা "$12,345.00" (text) | সংখ্যায় রূপান্তর | text-এর গড় বের করা যায় না |
| খরচ ফাঁকা | একই department + treatment-এর median দিয়ে পূরণ, আর flag দিয়ে রেখেছি | গড় না নিয়ে median, কারণ বড় বিল গড়কে টেনে তোলে |
| Risk 34 লেখা (0.34-এর বদলে) | ১০০ দিয়ে ভাগ | risk ০–১ এর মধ্যে হতে হবে |
| Pediatrics রোগীর বয়স 60+ | patient master টেবিল থেকে আসল বয়স নিয়েছি | শিশু বিভাগে বয়স্ক রোগী অসম্ভব |
| Gender ফাঁকা | "Unknown" রেখেছি, অনুমান করিনি | অনুমান করলে ভুল ডেটা তৈরি হয় |

**মনে রাখার কথা:** প্রতিটা পরিবর্তন `cleaning_log.csv`-এ লেখা আছে, কতগুলো রো বদলেছে সহ।

**English:** "I logged every cleaning step with the number of rows affected. I imputed missing costs with the
median of the same department and treatment, and flagged them, rather than dropping rows. Where a value
couldn't be recovered, like a blank gender, I set it to 'Unknown' instead of guessing."

---

## ৪. Readmission — সবচেয়ে গুরুত্বপূর্ণ অংশ

**সংজ্ঞা:** একজন রোগী হাসপাতাল থেকে ছাড়া পাওয়ার ৩০ দিনের মধ্যে আবার ভর্তি হলে, সেটা readmission।

**কীভাবে বের করেছি:** প্রতিটা রোগীর ভর্তিগুলো তারিখ অনুযায়ী সাজিয়ে দেখেছি, পরের ভর্তি ৩০ দিনের
মধ্যে কিনা। SQL-এ এটা `LEAD()` window function দিয়ে করেছি, আর ফল Python-এর সাথে হুবহু মিলেছে (৩,৩৩১টা)।

**একটা সূক্ষ্ম বিষয় (ইন্টারভিউয়ার মুগ্ধ হবে):** ডেটার শেষ ৩০ দিনে যারা ছাড়া পেয়েছে, তারা আবার ভর্তি
হয়েছে কিনা আমরা এখনো জানি না, কারণ ডেটা ওখানেই শেষ। তাদের "ভর্তি হয়নি" ধরলে রেট কৃত্রিমভাবে কম
দেখাত। তাই তাদের হিসাব থেকে বাদ দিয়েছি। একে বলে **right-censoring**।

**English:** "Readmission is derived from each patient's sequence of stays using LEAD() in SQL, and the result
matches the Python flag exactly. One subtle point: stays discharged in the last 30 days of the data can't show
a readmission yet, so I excluded them. Counting them as 'not readmitted' would have made the rate look better
than it really is."

**ফলাফল:** 16.2% (লক্ষ্য 14%)। 60+ রোগী 21.8%। Riverside হাসপাতাল 20.8%, Westbrook 13.5%।

---

## ৫. মূল ফলাফল আর সুপারিশ

1. **Riverside Community Hospital:** readmission সবচেয়ে বেশি, থাকার দিনও সবচেয়ে বেশি, recovery score সবচেয়ে কম।
   → সুপারিশ: discharge checklist আর ৭ দিনের মধ্যে follow-up clinic।
2. **60+ বয়স:** মোট সেবার ২৯.৭%, readmission ২১.৮%।
   → সুপারিশ: বয়স্কদের জন্য আলাদা discharge planning, ওষুধ রিভিউ।
3. **No-show:** একই দিনে বুক করলে ৫.৩%, ৩০ দিনের বেশি আগে বুক করলে ২১%। SMS ছাড়া ১৮.৫%, SMS দিলে ১২.৬%।
   → সুপারিশ: সবাইকে SMS reminder, দূরের অ্যাপয়েন্টমেন্টে দ্বিতীয় reminder।
4. **শীতকাল:** ডিসেম্বর–ফেব্রুয়ারিতে ভর্তি ২৫% বেশি।
   → সুপারিশ: General Medicine আর Pediatrics-এ শীতকালে বাড়তি স্টাফ।

---

## ৬. সম্ভাব্য প্রশ্ন ও উত্তর

**Q: Why median instead of mean for imputing cost?**
A: "Treatment costs are right-skewed — a few very expensive surgeries pull the mean up. The median of the same
department and treatment type is a more typical value, and I flagged imputed rows so they can be excluded."

**Q: How did you validate your numbers?**
A: "Three ways: the readmission rate is computed independently in Python and SQL and matches exactly; the
Excel workbook recalculates every KPI with formulas and agrees with both; and I have automated tests that
check the cleaned data — no negative stays, valid categories, unique IDs."

**Q: What is the risk score and how good is it?**
A: "It's a predicted probability of readmission at discharge. Patients scored 25% or more were readmitted
26% of the time versus 15% for the rest, so it's useful for targeting follow-up calls. Its AUC is about 0.61 —
a screening tool, not a diagnosis, which is typical for real readmission scores."

**Q: What would you do with real data?**
A: "Connect to the EHR or data warehouse instead of CSVs, schedule the cleaning in n8n or Airflow, add
diagnosis codes to separate planned from unplanned readmissions, and set up row-level security in Power BI
so each hospital sees only its own data."

**Q: Why a star schema?**
A: "Facts (stays, appointments) in the middle, descriptions (hospital, department, patient, date) around them.
It makes SQL joins simple and it's exactly the model Power BI works best with."

**Q: Which tool for what?**
A: "Excel for a quick, formula-based check of the cleaning that a manager can open; Python for repeatable
cleaning and analysis; PostgreSQL as the single source of truth; Power BI and Streamlit for interactive
dashboards — Power BI for internal business users, Streamlit for a public web demo."

---

## ৭. শেখা SQL কৌশল (নাম মনে রাখবেন)

`LEAD()` / `LAG()` · `RANK()` · moving average (`ROWS BETWEEN 2 PRECEDING`) · `percentile_cont` (median, P90) ·
`FILTER` দিয়ে pivot · CTE (`WITH`) · `COALESCE` দিয়ে NULL সামলানো · CHECK constraint আর foreign key।
