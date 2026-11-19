# Hospital Disease Analytics Website

## 1. Install
Open Anaconda Prompt or Command Prompt in this folder and run:

```bash
python -m pip install -r requirements.txt
```

## 2. Start the website

```bash
streamlit run app.py
```

The browser should open the app. If it does not, open the Local URL printed in the terminal.

## 3. Connect to MySQL
In the left sidebar, enter your MySQL password. The app reads the existing `hospital_dwdm.staging_hospital` table for the default dashboard.

## 4. Upload another dataset
Open **Upload Dataset**, select a CSV or Excel file, review the preview and validation summary, then click **Use this dataset in the dashboard**. Open the Dashboard tab to view its charts.

The current upload workflow validates, cleans basic data issues, and uses the uploaded data for the current app session. It does **not** overwrite or append to your original MySQL staging table. The cleaned dataset can be downloaded from the ETL tab.

## Expected hospital columns
The uploaded file should contain the hospital fields used by the project, such as patient name, age, gender, blood type, medical condition, admission/discharge dates, doctor, hospital, insurance provider, billing amount, room number, admission type, medication, test results, length of stay, age group, admission year, and admission month. Common display-name variants are recognized.

## Association rules
Put `association_rules.csv` beside `app.py`, or upload it in the Dashboard tab. The original notebook's rules file is separate from the hospital records dataset.
