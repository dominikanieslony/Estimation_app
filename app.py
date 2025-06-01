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

def filter_data(df, country, campaign_filter, start_date, end_date, selected_category=None):
    df_filtered = df[df['Country'] == country].copy()

    if selected_category and selected_category != "All":
        df_filtered = df_filtered[df_filtered['Category_name'].str.contains(selected_category, case=False, na=False)]

    if campaign_filter and len(campaign_filter) >= 3:
        mask_desc = df_filtered['Description'].str.contains(campaign_filter, case=False, na=False)
        mask_camp = df_filtered['Campaign name'].str.contains(campaign_filter, case=False, na=False)
        df_filtered = df_filtered[mask_desc | mask_camp]

    df_filtered['Date Start'] = pd.to_datetime(df_filtered['Date Start'], dayfirst=True, errors='coerce')
    df_filtered['Date End'] = pd.to_datetime(df_filtered['Date End'], dayfirst=True, errors='coerce')
    df_filtered = df_filtered[
        (df_filtered['Date Start'] >= pd.to_datetime(start_date)) &
        (df_filtered['Date End'] <= pd.to_datetime(end_date))
    ]
    return df_filtered

def estimate_demand(earlier_df, later_df, percentage):
    earlier_mean = earlier_df['Demand'].mean() if not earlier_df.empty else None
    later_mean = later_df['Demand'].mean() if not later_df.empty else None

    if earlier_mean is None and later_mean is None:
        return None
    elif earlier_mean is not None and later_mean is not None:
        adjusted_earlier = earlier_mean * (1 + percentage / 100)
        return (adjusted_earlier + later_mean) / 2
    elif earlier_mean is not None:
        return earlier_mean * (1 + percentage / 100)
    else:
        return later_mean

def reorder_columns(df):
    cols = df.columns.tolist()
    if 'Campaign name' in cols and 'Description' in cols:
        cols.remove('Description')
        idx = cols.index('Campaign name') + 1
        cols.insert(idx, 'Description')
        return df[cols]
    return df

st.title("📊 Marketing Campaign Estimator")

uploaded_file = st.file_uploader("Upload campaign data CSV file", type="csv")

if uploaded_file:
    try:
        df = load_data(uploaded_file)
        required_cols = {'Country', 'Description', 'Date Start', 'Date End', 'Demand', 'Campaign name', 'Category_name'}
        if not required_cols.issubset(df.columns):
            st.error(f"❌ Missing required columns: {required_cols - set(df.columns)}")
        else:
            df = clean_demand_column(df)
            country_list = df['Country'].dropna().unique().tolist()
            selected_country = st.selectbox("🌍 Select country:", country_list)

            categories = [
                "Wäsche (Damen/Herren)", "Outdoor, Sport (Damen/Herren)", 
                "Fashion, DOB, Designer (Damen)", "Herrenbekleidung", "Accessoires", "Baby-/Kinderbekleidung", 
                "Baby-/Kinderschuhe", "Babyausstattung", "Beauty (Parfum, Pflege, Kosmetik)", 
                "Denim, Casual (Damen/Herren)", "Erwachsenenschuhe", "Heimtex", "Home and Living", 
                "Kinderhartwaren (Sitze, Wägen, etc.)", "Möbel", "Schmuck", "Spielzeug", 
                "Technik", "Tierbedarf", "Tracht"
            ]
            selected_category = st.selectbox("🏷️ Select category:", ["All"] + categories)

            campaign_filter = st.text_input("🔎 Filter campaigns (contains, min 3 letters):")

            st.subheader("⏳ Earlier Period")
            earlier_start_date = st.date_input("Start date (Earlier Period):", key='earlier_start')
            earlier_end_date = st.date_input("End date (Earlier Period):", key='earlier_end')

            st.subheader("📈 Target growth from Earlier Period (%)")
            target_growth = st.number_input("Enter growth percentage (can be negative):", min_value=-100, max_value=1000, step=1, format="%d")

            st.subheader("⏳ Later Period")
            later_start_date = st.date_input("Start date (Later Period):", key='later_start')
            later_end_date = st.date_input("End date (Later Period):", key='later_end')

            earlier_filtered = filter_data(df, selected_country, campaign_filter, earlier_start_date, earlier_end_date, selected_category)
            later_filtered = filter_data(df, selected_country, campaign_filter, later_start_date, later_end_date, selected_category)

            earlier_filtered = reorder_columns(earlier_filtered)
            later_filtered = reorder_columns(later_filtered)

            st.subheader("Select campaigns to include from Earlier Period:")
            earlier_selections = {}
            for idx, row in earlier_filtered.iterrows():
                label = f"{row['Campaign name']} | {row['Description']} | Start: {row['Date Start'].date()} | End: {row['Date End'].date()} | Demand: {row['Demand']}"
                earlier_selections[idx] = st.checkbox(label, value=True, key=f"earlier_{idx}")

            st.subheader("Select campaigns to include from Later Period:")
            later_selections = {}
            for idx, row in later_filtered.iterrows():
                label = f"{row['Campaign name']} | {row['Description']} | Start: {row['Date Start'].date()} | End: {row['Date End'].date()} | Demand: {row['Demand']}"
                later_selections[idx] = st.checkbox(label, value=True, key=f"later_{idx}")

            earlier_selected_df = earlier_filtered.loc[[idx for idx, checked in earlier_selections.items() if checked]]
            later_selected_df = later_filtered.loc[[idx for idx, checked in later_selections.items() if checked]]

            if st.button("📈 Calculate Estimation"):
                if earlier_selected_df.empty and later_selected_df.empty:
                    st.warning("⚠️ No campaigns selected in either period for estimation.")
                else:
                    estimation = estimate_demand(earlier_selected_df, later_selected_df, target_growth)
                    if estimation is None:
                        st.warning("⚠️ Unable to calculate estimation with the given data.")
                    else:
                        st.success(f"Estimated Demand: **{estimation:.2f} EUR**")
                        st.markdown("### Data used for estimation:")
                        st.write("Earlier Period Campaigns:")
                        st.dataframe(earlier_selected_df)

                        st.write("Later Period Campaigns:")
                        st.dataframe(later_selected_df)

                        combined_df = pd.concat([earlier_selected_df, later_selected_df]).drop_duplicates()
                        csv = combined_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Download selected campaigns data as CSV",
                            data=csv,
                            file_name='campaign_estimation_data.csv',
                            mime='text/csv'
                        )
    except Exception as e:
        st.error(f"❌ Error processing file: {e}")

