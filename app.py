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
        val = val.replace('€', '').replace(' ', '').replace('.', '').replace(',', '.')
        try:
            return float(val)
        except ValueError:
            return None
    df['Demand'] = df['Demand'].apply(parse_demand)
    return df

# Filter data for earlier or later period
def filter_period(df, country, campaign_input, start_date, end_date):
    df = df[df['Country'] == country]
    df = df[df['Description'].str.contains(campaign_input, case=False, na=False)]
    df['Date Start'] = pd.to_datetime(df['Date Start'], dayfirst=True, errors='coerce')
    df['Date End'] = pd.to_datetime(df['Date End'], dayfirst=True, errors='coerce')
    return df[
        (df['Date Start'] >= pd.to_datetime(start_date)) &
        (df['Date End'] <= pd.to_datetime(end_date))
    ].copy()

# App UI
st.title("📊 Campaign Demand Estimator")

uploaded_file = st.file_uploader("Upload a campaign CSV file", type="csv")

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

            campaign_input = st.text_input("🏷️ Campaign search phrase (min. 3 characters):")

            st.markdown("### 📆 Define earlier and later periods")

            col1, col2 = st.columns(2)
            with col1:
                earlier_start = st.date_input("Earlier Period Start")
                earlier_end = st.date_input("Earlier Period End")
            with col2:
                later_start = st.date_input("Later Period Start")
                later_end = st.date_input("Later Period End")

            percentage = st.slider("📈 Target growth from Earlier Period (%)", min_value=0, max_value=100, value=0)

            if campaign_input and len(campaign_input) >= 3:
                filtered_earlier = filter_period(df, selected_country, campaign_input, earlier_start, earlier_end)
                filtered_later = filter_period(df, selected_country, campaign_input, later_start, later_end)

                st.markdown("#### 📋 Select campaigns to include from **Earlier Period**:")
                selected_earlier = []
                for i, row in filtered_earlier.iterrows():
                    label = f"{row['Campaign name']} | {row['Date Start'].date()} - {row['Date End'].date()} | Demand: {row['Demand']}"
                    if st.checkbox(label, key=f"earlier_{i}"):
                        selected_earlier.append(row)

                st.markdown("#### 📋 Select campaigns to include from **Later Period**:")
                selected_later = []
                for i, row in filtered_later.iterrows():
                    label = f"{row['Campaign name']} | {row['Date Start'].date()} - {row['Date End'].date()} | Demand: {row['Demand']}"
                    if st.checkbox(label, key=f"later_{i}"):
                        selected_later.append(row)

                if st.button("🔍 Estimate Demand"):
                    selected_earlier_df = pd.DataFrame(selected_earlier)
                    selected_later_df = pd.DataFrame(selected_later)

                    if selected_later_df.empty:
                        st.warning("⚠️ You must select at least one campaign from the Later Period.")
                    else:
                        adjusted_earlier = None
                        if not selected_earlier_df.empty:
                            earlier_mean = selected_earlier_df['Demand'].mean()
                            adjusted_earlier = earlier_mean * (1 + percentage / 100)
                        later_mean = selected_later_df['Demand'].mean()

                        if adjusted_earlier is not None:
                            final_estimation = (adjusted_earlier + later_mean) / 2
                        else:
                            final_estimation = later_mean

                        st.success(f"📈 Estimated 'Demand': **{final_estimation:.2f} EUR**")

                        st.markdown("### 📘 Estimation formula:")
                        st.markdown(r"""
                        Adjusted Earlier = Earlier Mean × (1 + percentage / 100)  
                        Final Estimation = (Adjusted Earlier + Later Mean) / 2  
                        """)

            else:
                st.info("ℹ️ Please enter at least 3 characters to search campaigns.")

    except Exception as e:
        st.error(f"❌ Error processing file: {e}")
