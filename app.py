import streamlit as st
import pandas as pd
import chardet
from datetime import datetime

# Load data with encoding detection
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
        val = str(val)
        val = val.replace('€', '').replace(' ', '')
        val = val.replace('.', '').replace(',', '.')
        try:
            return float(val)
        except ValueError:
            return None

    df['Demand'] = df['Demand'].apply(parse_demand)
    return df

# Filter data for a date range
def filter_data(df, country, campaign_keyword, start_date, end_date):
    df_filtered = df[df['Country'] == country].copy()
    df_filtered = df_filtered[df_filtered['Description'].str.contains(campaign_keyword, na=False, case=False)]

    df_filtered['Date Start'] = pd.to_datetime(df_filtered['Date Start'], dayfirst=True, errors='coerce')
    df_filtered['Date End'] = pd.to_datetime(df_filtered['Date End'], dayfirst=True, errors='coerce')

    df_filtered = df_filtered[
        (df_filtered['Date Start'] >= pd.to_datetime(start_date)) &
        (df_filtered['Date End'] <= pd.to_datetime(end_date))
    ]
    return df_filtered

# Streamlit UI
st.title("📊 Campaign Demand Estimator")

uploaded_file = st.file_uploader("Upload CSV campaign data", type="csv")

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

            campaign_name = st.text_input("🏷️ Campaign keyword (min. 3 characters):")

            if campaign_name and len(campaign_name) >= 3:
                st.subheader("📆 Define Time Periods")

                st.markdown("### 🕒 Earlier Period")
                earlier_start = st.date_input("Start date (Earlier Period)", key='start1')
                earlier_end = st.date_input("End date (Earlier Period)", key='end1')

                growth_percent = st.number_input(
                    "🌟 Target growth from Earlier Period (%)",
                    min_value=0,
                    max_value=100,
                    value=0,
                    step=1
                )

                st.markdown("### 🕒 Later Period")
                later_start = st.date_input("Start date (Later Period)", key='start2')
                later_end = st.date_input("End date (Later Period)", key='end2')

                if st.button("📈 Calculate Estimation"):
                    df_earlier = filter_data(df, selected_country, campaign_name, earlier_start, earlier_end)
                    df_later = filter_data(df, selected_country, campaign_name, later_start, later_end)

                    # Campaign selection UI
                    st.markdown("---")
                    st.markdown("#### ✅ Select campaigns to include from Earlier Period:")
                    selected_earlier = []
                    for i, row in df_earlier.iterrows():
                        label = f"{row['Campaign name']} | {row['Date Start'].date()} → {row['Date End'].date()} | Demand: {row['Demand']} | {row['Description']}"
                        if st.checkbox(label, key=f"early_{i}", value=True):
                            selected_earlier.append(row)

                    st.markdown("#### ✅ Select campaigns to include from Later Period:")
                    selected_later = []
                    for i, row in df_later.iterrows():
                        label = f"{row['Campaign name']} | {row['Date Start'].date()} → {row['Date End'].date()} | Demand: {row['Demand']} | {row['Description']}"
                        if st.checkbox(label, key=f"late_{i}", value=True):
                            selected_later.append(row)

                    # Perform estimation
                    if not selected_later:
                        st.warning("⚠️ You must select at least one campaign from the Later Period.")
                    else:
                        df_earlier_selected = pd.DataFrame(selected_earlier) if selected_earlier else pd.DataFrame(columns=df.columns)
                        df_later_selected = pd.DataFrame(selected_later)

                        earlier_mean = df_earlier_selected['Demand'].mean() if not df_earlier_selected.empty else 0
                        adjusted_earlier = earlier_mean * (1 + (growth_percent / 100))
                        later_mean = df_later_selected['Demand'].mean()

                        final_estimation = (adjusted_earlier + later_mean) / 2

                        st.success(f"📊 Estimated Demand: **{final_estimation:.2f} EUR**")

                        st.markdown("""
                        ### 📊 Estimation Formula:

                        *Adjusted Earlier* = Earlier Mean × (1 + percentage / 100)  
                        *Final Estimation* = (Adjusted Earlier + Later Mean) / 2
                        """)

            else:
                st.info("ℹ️ Please enter at least 3 characters for the campaign keyword.")

    except Exception as e:
        st.error(f"❌ Error processing the file: {e}")
