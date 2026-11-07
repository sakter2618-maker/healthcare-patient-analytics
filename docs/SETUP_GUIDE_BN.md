# সেটআপ গাইড (বাংলা) — নিজের কম্পিউটারে প্রজেক্ট চালানো

## যা লাগবে
* **Python 3.11 বা তার পরের** (python.org থেকে ইনস্টল; ইনস্টলের সময় "Add Python to PATH"-এ টিক দেবেন)
* **PostgreSQL** (ঐচ্ছিক, SQL অংশের জন্য) — postgresql.org থেকে
* **Excel** আর **Power BI Desktop** (Power BI শুধু Windows-এ চলে)

## ধাপ ১: প্রজেক্ট ডাউনলোড
GitHub-এ repo খুলে সবুজ **Code** বাটন → **Download ZIP** → ZIP খুলে ফোল্ডারটা Desktop-এ রাখুন।

## ধাপ ২: Python প্যাকেজ ইনস্টল
ফোল্ডারের ভেতরে ঠিকানার ঘরে `cmd` লিখে Enter চাপুন। কালো জানালায় লিখুন:
```
pip install -r requirements.txt
```

## ধাপ ৩: ডেটা তৈরি ও পরিষ্কার (ঐচ্ছিক — ফাইলগুলো আগে থেকেই আছে)
```
python src/generate_data.py
python src/clean_data.py
```

## ধাপ ৪: ড্যাশবোর্ড চালানো
```
streamlit run streamlit_app.py
```
ব্রাউজারে আপনাআপনি ড্যাশবোর্ড খুলবে (http://localhost:8501)। বন্ধ করতে কালো জানালায় Ctrl + C।

## ধাপ ৫: PostgreSQL ডেটাবেস (ঐচ্ছিক)
pgAdmin খুলে `healthcare` নামে একটা ডেটাবেস বানান। তারপর cmd-তে (প্রজেক্ট ফোল্ডার থেকে):
```
psql -U postgres -d healthcare -f sql/01_schema.sql
psql -U postgres -d healthcare -f sql/02_load_data.sql
psql -U postgres -d healthcare -f sql/03_business_queries.sql
psql -U postgres -d healthcare -f sql/04_views_for_power_bi.sql
```

## ধাপ ৬: Excel
`excel/Healthcare_Patient_Data_Cleaning.xlsx` খুলুন:
* **Raw_Sample** — লাল ঘর = ডেটার সমস্যা (ঘরের ওপর মাউস রাখলে নোট দেখাবে)
* **Cleaning_Log** — কী কী ঠিক করা হয়েছে
* **Summary** — সব KPI ফর্মুলা দিয়ে হিসাব করা

## ধাপ ৭: Power BI
`powerbi/POWER_BI_GUIDE.md` ফাইলে ধাপে ধাপে লেখা আছে: ডেটা লোড, relationship, theme, DAX আর ৬টা পেজের ডিজাইন।
