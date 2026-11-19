import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
from pathlib import Path
import io

st.set_page_config(page_title="Hospital Disease Analytics", page_icon="🏥", layout="wide")

st.title("Hospital Disease Pattern & Treatment Analysis")
st.caption("Disease, Medication, Hospital Stay & Association Rule Analysis")

REQUIRED_COLUMNS = [
    "patient_name", "age", "gender", "blood_type", "medical_condition",
    "date_of_admission", "doctor", "hospital", "insurance_provider",
    "billing_amount", "room_number", "admission_type", "discharge_date",
    "medication", "test_results", "length_of_stay", "age_group",
    "admission_year", "admission_month"
]

COLUMN_ALIASES = {
    "Name": "patient_name", "Patient Name": "patient_name",
    "Age": "age", "Gender": "gender", "Blood Type": "blood_type",
    "Medical Condition": "medical_condition", "Disease": "medical_condition",
    "Date of Admission": "date_of_admission", "Admission Date": "date_of_admission",
    "Doctor": "doctor", "Hospital": "hospital", "Insurance Provider": "insurance_provider",
    "Billing Amount": "billing_amount", "Room Number": "room_number",
    "Admission Type": "admission_type", "Discharge Date": "discharge_date",
    "Medication": "medication", "Test Results": "test_results",
    "Length_of_Stay": "length_of_stay", "Length of Stay": "length_of_stay",
    "Age_Group": "age_group", "Age Group": "age_group",
    "Admission_Year": "admission_year", "Admission Year": "admission_year",
    "Admission_Month": "admission_month", "Admission Month": "admission_month",
}

def normalize_columns(data):
    data = data.copy()
    data.columns = [str(c).strip() for c in data.columns]
    rename = {c: COLUMN_ALIASES[c] for c in data.columns if c in COLUMN_ALIASES}
    data = data.rename(columns=rename)
    return data

def clean_dataset(data):
    data = normalize_columns(data)
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in data.columns]
    if missing_cols:
        return None, missing_cols, {"original_rows": len(data), "duplicates_removed": 0, "negative_billing": 0, "missing_values": int(data.isna().sum().sum())}
    data = data[REQUIRED_COLUMNS].copy()
    original_rows = len(data)
    duplicates_removed = int(data.duplicated().sum())
    data = data.drop_duplicates()
    data["billing_amount"] = pd.to_numeric(data["billing_amount"], errors="coerce")
    data["age"] = pd.to_numeric(data["age"], errors="coerce")
    data["length_of_stay"] = pd.to_numeric(data["length_of_stay"], errors="coerce")
    data["date_of_admission"] = pd.to_datetime(data["date_of_admission"], errors="coerce")
    data["discharge_date"] = pd.to_datetime(data["discharge_date"], errors="coerce")
    negative_billing = int((data["billing_amount"] < 0).sum())
    data.loc[data["billing_amount"] < 0, "billing_amount"] = pd.NA
    # Keep the rows, but flag/fix invalid numeric/date values as missing for review.
    data.loc[(data["age"] < 0) | (data["age"] > 120), "age"] = pd.NA
    data.loc[data["length_of_stay"] < 0, "length_of_stay"] = pd.NA
    data["admission_year"] = data["date_of_admission"].dt.year.fillna(
        pd.to_numeric(data["admission_year"], errors="coerce")
    )
    data["admission_month"] = data["date_of_admission"].dt.month.fillna(
        pd.to_numeric(data["admission_month"], errors="coerce")
    )
    summary = {
        "original_rows": original_rows,
        "duplicates_removed": duplicates_removed,
        "negative_billing": negative_billing,
        "missing_values": int(data.isna().sum().sum()),
        "clean_rows": len(data),
    }
    # Return human-readable column names for dashboard functions.
    data = data.rename(columns={
        "patient_name":"Name", "age":"Age", "gender":"Gender", "blood_type":"Blood Type",
        "medical_condition":"Medical Condition", "date_of_admission":"Date of Admission",
        "doctor":"Doctor", "hospital":"Hospital", "insurance_provider":"Insurance Provider",
        "billing_amount":"Billing Amount", "room_number":"Room Number", "admission_type":"Admission Type",
        "discharge_date":"Discharge Date", "medication":"Medication", "test_results":"Test Results",
        "length_of_stay":"Length_of_Stay", "age_group":"Age_Group",
        "admission_year":"Admission_Year", "admission_month":"Admission_Month"
    })
    return data, [], summary

def read_upload(uploaded):
    name = uploaded.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded)
    if name.endswith(".xlsx") or name.endswith(".xls"):
        return pd.read_excel(uploaded)
    raise ValueError("Please upload a CSV or Excel file.")

def get_engine():
    host = st.session_state.get("db_host", "localhost").strip()
    port = int(st.session_state.get("db_port", 3306))
    database = st.session_state.get("db_name", "hospital_dwdm").strip()
    username = st.session_state.get("db_user", "root").strip()
    password = st.session_state.get("db_password", "")
    if not password:
        raise ValueError("Enter your MySQL password in the sidebar first.")
    return create_engine(
        f"mysql+pymysql://{quote_plus(username)}:{quote_plus(password)}@{host}:{port}/{database}"
    )

def load_default_data():
    try:
        engine = get_engine()
        query = """
        SELECT patient_name AS Name, age AS Age, gender AS Gender, blood_type AS `Blood Type`,
        medical_condition AS `Medical Condition`, date_of_admission AS `Date of Admission`,
        doctor AS Doctor, hospital AS Hospital, insurance_provider AS `Insurance Provider`,
        billing_amount AS `Billing Amount`, room_number AS `Room Number`,
        admission_type AS `Admission Type`, discharge_date AS `Discharge Date`,
        medication AS Medication, test_results AS `Test Results`, length_of_stay AS Length_of_Stay,
        age_group AS Age_Group, admission_year AS Admission_Year, admission_month AS Admission_Month
        FROM staging_hospital
        """
        with engine.connect() as conn:
            data = pd.read_sql(text(query), conn)
        return data, None
    except Exception as exc:
        return None, str(exc)

def draw_original_dashboard(data, rules):
    total_rules = len(rules) if rules is not None else 0
    disease_counts = data["Medical Condition"].dropna().value_counts()
    medication_counts = data["Medication"].dropna().value_counts()
    stay = data.groupby("Medical Condition")["Length_of_Stay"].mean().dropna().sort_values(ascending=True)

    fig = plt.figure(figsize=(18, 11))
    fig.patch.set_facecolor("#F7F9FC")
    fig.suptitle("Hospital Disease Pattern & Treatment Analysis", fontsize=25, fontweight="bold", y=0.97)
    fig.text(0.5, 0.935, "Disease, Medication, Hospital Stay & Association Rule Analysis",
             ha="center", fontsize=12, color="dimgray")

    kpi_data = [
        (f"{len(data):,}", "VISIT RECORDS"),
        (f"{data['Medical Condition'].nunique():,}", "DISEASES"),
        (f"{data['Medication'].nunique():,}", "MEDICATIONS"),
        (f"{total_rules:,}", "ASSOCIATION RULES")
    ]
    for (value, label), x in zip(kpi_data, [0.08, 0.31, 0.54, 0.77]):
        card = FancyBboxPatch((x, 0.82), 0.17, 0.075, boxstyle="round,pad=0.012",
                              linewidth=0, facecolor="white")
        fig.add_artist(card)
        fig.text(x + 0.085, 0.865, value, ha="center", va="center", fontsize=22, fontweight="bold")
        fig.text(x + 0.085, 0.838, label, ha="center", va="center", fontsize=9, color="dimgray")

    ax1 = fig.add_axes([0.05, 0.48, 0.40, 0.28])
    if len(disease_counts):
        ax1.pie(disease_counts.values, labels=disease_counts.index, autopct="%1.1f%%", startangle=90,
                pctdistance=0.78, wedgeprops=dict(width=0.42, edgecolor="white"))
    ax1.set_title("Disease Distribution", fontsize=16, fontweight="bold", pad=15)

    ax2 = fig.add_axes([0.55, 0.48, 0.40, 0.28])
    if len(medication_counts):
        ax2.pie(medication_counts.values, labels=medication_counts.index, autopct="%1.1f%%", startangle=90,
                pctdistance=0.78, wedgeprops=dict(width=0.42, edgecolor="white"))
    ax2.set_title("Medication Distribution", fontsize=16, fontweight="bold", pad=15)

    ax3 = fig.add_axes([0.06, 0.10, 0.39, 0.27])
    if len(stay):
        bars = ax3.barh(stay.index, stay.values)
        ax3.set_xlim(0, max(float(stay.max()) + 2, 1))
        for bar, value in zip(bars, stay.values):
            ax3.text(value + 0.2, bar.get_y() + bar.get_height()/2, f"{value:.1f} days",
                     va="center", fontsize=9)
    ax3.set_title("Average Length of Stay by Disease", fontsize=16, fontweight="bold", pad=12)
    ax3.set_xlabel("Average Stay (Days)")
    ax3.grid(axis="x", alpha=0.20)
    ax3.set_axisbelow(True)

    ax4 = fig.add_axes([0.53, 0.08, 0.42, 0.30])
    ax4.axis("off")
    ax4.set_title("Top Disease → Medication Associations", fontsize=16, fontweight="bold", pad=12)
    table_data = []
    if rules is not None and len(rules):
        r = rules.copy()
        if "Disease" not in r.columns and "antecedents" in r.columns:
            r = r.rename(columns={"antecedents":"Disease", "consequents":"Medication"})
        for col in ["Disease", "Medication", "support", "confidence", "lift"]:
            if col not in r.columns:
                r[col] = ""
        r["lift_num"] = pd.to_numeric(r["lift"], errors="coerce")
        r = r.sort_values("lift_num", ascending=False).head(6)
        for _, row in r.iterrows():
            disease = str(row["Disease"]).replace("Disease_", "")
            med = str(row["Medication"]).replace("Medication_", "")
            table_data.append([f"{disease}  →  {med}",
                               f"{float(row['support']):.3f}" if pd.notna(pd.to_numeric(row["support"], errors="coerce")) else str(row["support"]),
                               f"{float(row['confidence']):.3f}" if pd.notna(pd.to_numeric(row["confidence"], errors="coerce")) else str(row["confidence"]),
                               f"{float(row['lift']):.3f}" if pd.notna(pd.to_numeric(row["lift"], errors="coerce")) else str(row["lift"])])
    if table_data:
        table = ax4.table(cellText=table_data, colLabels=["Association", "Support", "Confidence", "Lift"],
                          loc="center", cellLoc="center", colWidths=[0.48, 0.15, 0.18, 0.12])
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 1.65)
        for cell in table.get_celld().values():
            cell.set_edgecolor("#D9DEE7")
        for col in range(4):
            table[(0, col)].set_text_props(fontweight="bold")
    else:
        ax4.text(0.5, 0.5, "Upload association_rules.csv to display rules", ha="center", va="center")

    fig.text(0.5, 0.025,
             "Association rules indicate statistical co-occurrence in the dataset and are not clinical treatment recommendations.",
             ha="center", fontsize=9, color="dimgray")
    return fig

with st.sidebar:
    st.header("MySQL Connection")
    st.text_input("Host", value="localhost", key="db_host")
    st.number_input("Port", min_value=1, max_value=65535, value=3306, key="db_port")
    st.text_input("Database", value="hospital_dwdm", key="db_name")
    st.text_input("Username", value="root", key="db_user")
    st.text_input("MySQL password", type="password", key="db_password")
    st.caption("The password is used only for this running session.")

dashboard_tab, upload_tab, etl_tab = st.tabs(["📊 Dashboard", "📁 Upload Dataset", "🧹 ETL & Data Quality"])

with dashboard_tab:
    st.subheader("Hospital analytics")
    rules_upload = st.file_uploader("Association rules file (CSV, optional)", type=["csv"], key="rules_file")
    rules = None
    if rules_upload is not None:
        try:
            rules = pd.read_csv(rules_upload)
        except Exception as exc:
            st.error(f"Could not read association rules: {exc}")
    elif Path("association_rules.csv").exists():
        try:
            rules = pd.read_csv("association_rules.csv")
        except Exception:
            rules = None

    if "active_data" in st.session_state:
        data = st.session_state["active_data"]
        st.info("Dashboard is using the dataset uploaded in this session.")
    else:
        data, error = load_default_data()
        if error:
            st.warning("Could not load data from MySQL yet. Enter your MySQL details in the sidebar, or upload a dataset in the Upload Dataset tab.")
            with st.expander("Connection details"):
                st.code(error)
    if data is not None:
        if not {"Medical Condition", "Medication", "Length_of_Stay"}.issubset(data.columns):
            st.error("Dataset does not have the required analytics columns. Use the Upload Dataset tab to validate it.")
        else:
            fig = draw_original_dashboard(data, rules)
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)
            st.caption(f"Rows analyzed: {len(data):,}")

with upload_tab:
    st.subheader("Upload a new hospital dataset")
    st.write("Upload CSV or Excel data. The app checks the expected hospital columns before using it.")
    uploaded = st.file_uploader("Choose a CSV or Excel file", type=["csv", "xlsx", "xls"], key="hospital_file")
    if uploaded is not None:
        try:
            raw = read_upload(uploaded)
            st.write("**Uploaded file preview**")
            st.dataframe(raw.head(10), use_container_width=True)
            cleaned, missing_cols, summary = clean_dataset(raw)
            if missing_cols:
                st.error("Required columns are missing. Rename/map these columns before processing: " + ", ".join(missing_cols))
                st.caption("Common names such as 'Medical Condition', 'Length of Stay', and 'Patient Name' are recognized.")
            else:
                st.success("Dataset structure validated.")
                c1, c2, c3 = st.columns(3)
                c1.metric("Original rows", f"{summary['original_rows']:,}")
                c2.metric("Duplicate rows removed", f"{summary['duplicates_removed']:,}")
                c3.metric("Rows after duplicate removal", f"{summary['clean_rows']:,}")
                st.session_state["pending_data"] = cleaned
                if st.button("Use this dataset in the dashboard", type="primary"):
                    st.session_state["active_data"] = cleaned
                    st.success("Dataset selected. Open the Dashboard tab to view its analytics.")
        except Exception as exc:
            st.error(f"Could not process this file: {exc}")

with etl_tab:
    st.subheader("ETL and data quality summary")
    st.write("This preview performs validation and cleaning in memory. It does not overwrite your original staging_hospital table.")
    if "pending_data" in st.session_state:
        cleaned = st.session_state["pending_data"]
        st.metric("Rows ready for analysis", f"{len(cleaned):,}")
        st.metric("Missing values after basic cleaning", f"{int(cleaned.isna().sum().sum()):,}")
        st.dataframe(cleaned.head(20), use_container_width=True)
        st.download_button("Download cleaned dataset as CSV",
                           data=cleaned.to_csv(index=False).encode("utf-8"),
                           file_name="cleaned_hospital_data.csv", mime="text/csv")
    else:
        st.info("Upload a dataset first to see its ETL summary.")

st.divider()
st.caption("For academic analysis only. Association rules show co-occurrence and are not clinical recommendations.")
