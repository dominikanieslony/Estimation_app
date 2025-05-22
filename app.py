import streamlit as st
import pandas as pd
import chardet
from datetime import datetime

# Wczytywanie danych z automatycznym wykrywaniem kodowania
def load_data(uploaded_file):
    raw = uploaded_file.read()
    encoding = chardet.detect(raw)['encoding']
    uploaded_file.seek(0)

    df = pd.read_csv(uploaded_file, encoding=encoding, sep='\t', dayfirst=True)
    return df

# Czyszczenie kolumny 'Demand'
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

# Filtrowanie danych według kryteriów
def filter_data(df, country, campaign_substr, start_date, end_date):
    df_filtered = df[df['Country'] == country].copy()
    df_filtered = df_filtered[df_filtered['Description'].str.contains(campaign_substr, na=False, case=False)]

    df_filtered['Date Start'] = pd.to_datetime(df_filtered['Date Start'], dayfirst=True, errors='coerce')
    df_filtered['Date End'] = pd.to_datetime(df_filtered['Date End'], dayfirst=True, errors='coerce')

    df_filtered = df_filtered[
        (df_filtered['Date Start'] >= pd.to_datetime(start_date)) &
        (df_filtered['Date End'] <= pd.to_datetime(end_date))
    ]
    return df_filtered

# Obliczenie średniej wartości 'Demand'
def estimate_demand(df):
    if df.empty:
        return None
    return df['Demand'].mean()

# UI Streamlit
st.title("📊 Marketing Campaign Estimator")

uploaded_file = st.file_uploader("Upload campaign CSV data file", type="csv")

if uploaded_file:
    try:
        df = load_data(uploaded_file)

        required_cols = {'Country', 'Description', 'Date Start', 'Date End', 'Demand'}
        if not required_cols.issubset(df.columns):
            st.error(f"❌ Missing required columns: {required_cols - set(df.columns)}")
        else:
            df = clean_demand_column(df)

            country_list = df['Country'].dropna().unique().tolist()
            selected_country = st.selectbox("🌍 Select country:", country_list)

            campaign_name = st.text_input("🏷️ Enter campaign name (min. 3 characters):")

            st.markdown("### Select Earlier Period")
            earlier_start_date = st.date_input("Start date (Earlier Period)", key="earlier_start")
            earlier_end_date = st.date_input("End date (Earlier Period)", key="earlier_end")

            st.markdown("### Select Later Period")
            later_start_date = st.date_input("Start date (Later Period)", key="later_start")
            later_end_date = st.date_input("End date (Later Period)", key="later_end")

            percentage = st.number_input(
                "Enter percentage increase from Earlier Period (1-100%)",
                min_value=1, max_value=100, value=10, step=1
            )

            if campaign_name and len(campaign_name) >= 3:
                campaign_substr = campaign_name  # use full input substring

                if st.button("📈 Calculate estimation"):
                    # Filter data for Earlier Period
                    earlier_df = filter_data(df, selected_country, campaign_substr, earlier_start_date, earlier_end_date)
                    earlier_mean = estimate_demand(earlier_df)

                    # Filter data for Later Period
                    later_df = filter_data(df, selected_country, campaign_substr, later_start_date, later_end_date)
                    later_mean = estimate_demand(later_df)

                    if earlier_mean is not None:
                        adjusted_earlier = earlier_mean * (1 + percentage / 100)
                    else:
                        adjusted_earlier = None

                    if adjusted_earlier is not None and later_mean is not None:
                        final_estimation = (adjusted_earlier + later_mean) / 2
                    elif adjusted_earlier is not None:
                        final_estimation = adjusted_earlier
                    elif later_mean is not None:
                        final_estimation = later_mean
                    else:
                        final_estimation = None

                    if final_estimation is not None:
                        st.success(f"Estimated 'Demand' value: **{final_estimation:.2f} EUR**")

                        st.write("### Data from Earlier Period:")
                        st.dataframe(earlier_df)

                        st.write("### Data from Later Period:")
                        st.dataframe(later_df)

                        combined_df = pd.concat([earlier_df, later_df]).drop_duplicates()
                        csv = combined_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Download combined data as CSV",
                            data=csv,
                            file_name='campaign_estimation.csv',
                            mime='text/csv'
                        )
                    else:
                        st.warning("⚠️ No data matching the criteria.")
            else:
                st.info("ℹ️ Please enter at least 3 characters for the campaign name.")
    except Exception as e:
        st.error(f"❌ Error processing file: {e}")
