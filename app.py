import streamlit as st
import pandas as pd
import chardet
from datetime import datetime

# Load CSV with encoding detection
def load_data(uploaded_file):
    raw = uploaded_file.read()
    encoding = chardet.detect(raw)['encoding']
    uploaded_file.seek(0)
    df = pd.read_csv(uploaded_file, encoding=encoding, sep='\t', dayfirst=True)
    return df

# Clean 'Demand' column
def clean_demand_column(df):
    def parse_demand(val):
        if pd.isna(val):
            return None
        val = str(val).replace('€', '').replace(' ', '').replace('.', '').replace(',', '.')
        try:
            return float(val)
        except ValueError:
            return None
    df['Demand'] = df['Demand'].apply(parse_demand)
    return df

# Filter data
def filter_data(df, country, keyword, start_date, end_date):
    df_filtered = df[df['Country'] == country].copy()
    df_filtered['Date Start'] = pd.to_datetime(df_filtered['Date Start'], dayfirst=True, errors='coerce')
    df_filtered['Date End'] = pd.to_datetime(df_filtered['Date End'], dayfirst=True, errors='coerce')
    df_filtered = df_filtered[
        df_filtered['Description'].str.contains(keyword, na=False)
        & (df_filtered['Date Start'] >= pd.to_datetime(start_date))
        & (df_filtered['Date End'] <= pd.to_datetime(end_date))
    ]
    return df_filtered

# UI
st.title("📊 Campaign Demand Estimator")

uploaded_file = st.file_uploader("Upload campaign CSV file", type="csv")

if uploaded_file:
    try:
        df = load_data(uploaded_file)

        required_cols = {'Country', 'Description', 'Date Start', 'Date End', 'Demand', 'Campaign name'}
        if not required_cols.issubset(df.columns):
            st.error(f"❌ Missing required columns: {required_cols - set(df.columns)}")
        else:
            df = clean_demand_column(df)
            country_list = df['Country'].dropna().unique().tolist()
            selected_country = st.selectbox("🌍 Select country:", country_list)

            keyword = st.text_input("🔍 Campaign keyword (min. 3 characters):")
            if keyword and len(keyword) >= 3:

                st.subheader("🕓 Define Time Ranges")

                st.markdown("### 📅 Earlier Period")
                earlier_col1, earlier_col2 = st.columns(2)
                with earlier_col1:
                    earlier_start = st.date_input("Start date (Earlier Period)", key="es")
                with earlier_col2:
                    earlier_end = st.date_input("End date (Earlier Period)", key="ee")

                percent_growth = st.number_input(
                    "🎯 Target growth from Earlier Period (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=0.0,
                    step=0.1
                )

                st.markdown("### 📅 Later Period")
                later_col1, later_col2 = st.columns(2)
                with later_col1:
                    later_start = st.date_input("Start date (Later Period)", key="ls")
                with later_col2:
                    later_end = st.date_input("End date (Later Period)", key="le")

                if st.button("📈 Estimate Demand"):
                    filtered_earlier = filter_data(df, selected_country, keyword, earlier_start, earlier_end)
                    filtered_later = filter_data(df, selected_country, keyword, later_start, later_end)

                    # Select campaigns to include
                    st.markdown("#### 📋 Select campaigns to include from **Earlier Period**:")
                    selected_earlier = []
                    for i, row in filtered_earlier.iterrows():
                        label = f"{row['Campaign name']} | {row['Date Start'].date()} - {row['Date End'].date()} | Demand: {row['Demand']}"
                        if st.checkbox(label, key=f"earlier_{i}", value=True):
                            selected_earlier.append(row)

                    st.markdown("#### 📋 Select campaigns to include from **Later Period**:")
                    selected_later = []
                    for i, row in filtered_later.iterrows():
                        label = f"{row['Campaign name']} | {row['Date Start'].date()} - {row['Date End'].date()} | Demand: {row['Demand']}"
                        if st.checkbox(label, key=f"later_{i}", value=True):
                            selected_later.append(row)

                    # Estimation logic
                    df_earlier_final = pd.DataFrame(selected_earlier)
                    df_later_final = pd.DataFrame(selected_later)

                    if not df_later_final.empty:
                        mean_earlier = df_earlier_final['Demand'].mean() if not df_earlier_final.empty else 0
                        adjusted_earlier = mean_earlier * (1 + percent_growth / 100)
                        mean_later = df_later_final['Demand'].mean()
                        final_estimation = (adjusted_earlier + mean_later) / 2

                        st.markdown("### 📌 Estimation Result")
                        st.success(f"Estimated Demand: **{final_estimation:.2f} EUR**")

                        st.markdown("---")
                        st.markdown("### 📘 Estimation Formula:")
                        st.markdown(r"""
**Estimation:**

**Adjusted Earlier** = Earlier Mean × (1 + percentage / 100)  
**Final Estimation** = (Adjusted Earlier + Later Mean) / 2
""")
                    else:
                        st.warning("⚠️ You must select at least one campaign from the Later Period.")
            else:
                st.info("ℹ️ Please enter at least 3 characters to search for campaigns.")
    except Exception as e:
        st.error(f"❌ Error processing file: {e}")
