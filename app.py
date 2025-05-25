import streamlit as st
import pandas as pd
import chardet
from datetime import datetime

def load_data(uploaded_file):
    raw = uploaded_file.read()
    encoding = chardet.detect(raw)['encoding']
    uploaded_file.seek(0)
    df = pd.read_csv(uploaded_file, encoding=encoding, sep='\t', dayfirst=True)
    return df

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

def filter_data(df, country, campaign_filter, start_date, end_date):
    df_filtered = df[df['Country'] == country].copy()
    if campaign_filter:
        df_filtered = df_filtered[df_filtered['Description'].str.contains(campaign_filter, case=False, na=False)]
    df_filtered['Date Start'] = pd.to_datetime(df_filtered['Date Start'], dayfirst=True, errors='coerce')
    df_filtered['Date End'] = pd.to_datetime(df_filtered['Date End'], dayfirst=True, errors='coerce')
    df_filtered = df_filtered[
        (df_filtered['Date Start'] >= pd.to_datetime(start_date)) &
        (df_filtered['Date End'] <= pd.to_datetime(end_date))
    ]
    return df_filtered

def estimate_demand(df):
    if df.empty:
        return None
    return df['Demand'].mean()

st.title("📊 Campaign Estimator")

uploaded_file = st.file_uploader("Upload campaign data CSV file", type="csv")

if uploaded_file:
    try:
        df = load_data(uploaded_file)
        required_cols = {'Country', 'Description', 'Date Start', 'Date End', 'Demand'}
        if not required_cols.issubset(df.columns):
            st.error(f"❌ Missing required columns: {required_cols - set(df.columns)}")
        else:
            df = clean_demand_column(df)

            country_list = df['Country'].dropna().unique().tolist()
            selected_country = st.selectbox("🌍 Select Country:", country_list)

            campaign_filter = st.text_input("🏷️ Campaign name filter (at least 3 characters):")

            if campaign_filter and len(campaign_filter) < 3:
                st.info("ℹ️ Please enter at least 3 characters for the campaign filter.")

            st.markdown("### Earlier Period")
            earlier_start = st.date_input("Earlier Period Start Date:")
            earlier_end = st.date_input("Earlier Period End Date:")

            earlier_percent = st.number_input(
                "Expected growth percentage on Earlier Period (1-100):", 
                min_value=1, max_value=100, value=10, step=1
            )

            st.markdown("### Later Period")
            later_start = st.date_input("Later Period Start Date:")
            later_end = st.date_input("Later Period End Date:")

            if campaign_filter and len(campaign_filter) >= 3:
                earlier_df = filter_data(df, selected_country, campaign_filter, earlier_start, earlier_end)
                later_df = filter_data(df, selected_country, campaign_filter, later_start, later_end)

                st.markdown("#### Earlier Period Campaigns")
                if earlier_df.empty:
                    st.warning("⚠️ No campaigns found in Earlier Period with the filter.")
                    earlier_selected = []
                else:
                    st.dataframe(earlier_df)  # pokażemy całą tabelę
                    
                    # Checkboxy do wyboru kampanii
                    st.markdown("Select campaigns to include from Earlier Period:")
                    earlier_selected = []
                    for idx, row in earlier_df.iterrows():
                        label = f"{row['Description']} | {row['Date Start'].date()} - {row['Date End'].date()} | Demand: {row['Demand']:.2f}"
                        if st.checkbox(label, value=True, key=f"earlier_{idx}"):
                            earlier_selected.append(idx)

                st.markdown("#### Later Period Campaigns")
                if later_df.empty:
                    st.warning("⚠️ No campaigns found in Later Period with the filter.")
                    later_selected = []
                else:
                    st.dataframe(later_df)  # pokażemy całą tabelę

                    st.markdown("Select campaigns to include from Later Period:")
                    later_selected = []
                    for idx, row in later_df.iterrows():
                        label = f"{row['Description']} | {row['Date Start'].date()} - {row['Date End'].date()} | Demand: {row['Demand']:.2f}"
                        if st.checkbox(label, value=True, key=f"later_{idx}"):
                            later_selected.append(idx)

                if st.button("📈 Calculate Estimation"):
                    if not earlier_selected or not later_selected:
                        st.error("❌ You must select at least one campaign from both periods.")
                    else:
                        filtered_earlier = earlier_df.loc[earlier_selected]
                        filtered_later = later_df.loc[later_selected]

                        earlier_mean = estimate_demand(filtered_earlier)
                        later_mean = estimate_demand(filtered_later)

                        if earlier_mean is None or later_mean is None:
                            st.warning("⚠️ Cannot compute estimation due to missing demand values in selected campaigns.")
                        else:
                            adjusted_earlier = earlier_mean * (1 + earlier_percent / 100)
                            final_estimation = (adjusted_earlier + later_mean) / 2

                            st.markdown("### Estimation Formula:")
                            st.latex(r'''
                            \text{Adjusted Earlier} = \text{Earlier Mean} \times \left(1 + \frac{\text{percentage}}{100}\right) \\
                            \text{Final Estimation} = \frac{\text{Adjusted Earlier} + \text{Later Mean}}{2}
                            ''')

                            st.success(f"📊 Estimated Demand: **{final_estimation:.2f} EUR**")

                            st.markdown("#### Used Earlier Period Campaigns:")
                            st.dataframe(filtered_earlier)

                            st.markdown("#### Used Later Period Campaigns:")
                            st.dataframe(filtered_later)

                            combined_df = pd.concat([filtered_earlier, filtered_later])
                            csv = combined_df.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                label="📥 Download selected data as CSV",
                                data=csv,
                                file_name='selected_campaigns_estimation.csv',
                                mime='text/csv'
                            )
            else:
                st.info("ℹ️ Please enter at least 3 characters for the campaign filter to enable filtering.")

    except Exception as e:
        st.error(f"❌ Error processing file: {e}")
