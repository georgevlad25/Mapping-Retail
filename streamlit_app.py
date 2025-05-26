import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
import base64
import os

st.set_page_config(layout="wide")

# === CONFIGURATION ===
LOCATION_FILE = "Updated_Retailer_Locations_ALL.xlsx"
LOCATION_SHEET = "Sheet1"   # your sheet name
FINANCIAL_FILE = "retailer_financials.xlsx"
LOGO_DIR = "logos"

# === Load Data ===
loc_df = pd.read_excel(LOCATION_FILE, sheet_name=LOCATION_SHEET)
loc_df = loc_df.loc[:, ~loc_df.columns.str.contains("^Unnamed")]
fin_df = pd.read_excel(FINANCIAL_FILE)
fin_df = fin_df.loc[:, ~fin_df.columns.str.contains("^Unnamed")]

# === Merge on correct column names ===
df = loc_df.merge(
    fin_df,
    left_on="Magazin",
    right_on="Retailer Name",
    how="inner"
)

# === Utility to get logo as base64 image ===
def get_logo_base64(retailer_name):
    variants = [
        retailer_name + ".png",
        retailer_name.replace(" ", "") + ".png",
        retailer_name.replace(" ", "_") + ".png",
        retailer_name.replace("/", "_") + ".png",
        retailer_name.replace(" / ", "_") + ".png",
        retailer_name.lower() + ".png",
        retailer_name.replace(" ", "").lower() + ".png",
        retailer_name.replace("/", "").replace(" ", "").lower() + ".png",
    ]
    for fname in variants:
        path = os.path.join(LOGO_DIR, fname)
        if os.path.exists(path):
            with open(path, "rb") as f:
                data = base64.b64encode(f.read()).decode("utf-8")
                return f'<img src="data:image/png;base64,{data}" width="100">'
    return ""

# === Sidebar Filters ===
st.sidebar.header("Filter")
all_domains = df['Domain'].dropna().unique() if 'Domain' in df.columns else []
all_retailers = df['Magazin'].dropna().unique()

domain_sel = st.sidebar.multiselect("Domain", options=all_domains, default=all_domains)
retailer_sel = st.sidebar.multiselect("Retailer", options=all_retailers, default=all_retailers)

filtered_df = df.copy()
if domain_sel and 'Domain' in df.columns:
    filtered_df = filtered_df[filtered_df['Domain'].isin(domain_sel)]
if retailer_sel:
    filtered_df = filtered_df[filtered_df['Magazin'].isin(retailer_sel)]

st.title("Retailer Locations Map with Logos and Financials")
st.write(f"Showing {len(filtered_df)} locations (only retailers with both location and financials data).")

# === SUMMARY TABLE (EXCEL-STYLE) ===
summary = (
    filtered_df.groupby(['Domain', 'Magazin'])
    .agg(
        Number_of_Stores=('Magazin', 'count'),
        Turnover=('Turnover 2023 (mil EUR)', 'first'),
        Employees=('Avg employees number', 'first')
    )
    .reset_index()
    .sort_values(['Domain', 'Magazin'])
)
summary = summary.rename(columns={
    'Domain': 'Domain',
    'Magazin': 'Retailer Name',
    'Number_of_Stores': 'Number of Stores',
    'Turnover': 'Turnover 2023 (mil EUR)',
    'Employees': 'Avg employees number'
})

st.subheader("Retailers Financials & Store Count")
st.dataframe(summary, hide_index=True)

# === Map Setup ===
if len(filtered_df) > 0:
    rom_center = [45.9432, 24.9668]
    lat_center = filtered_df['Latitudine'].mean() if not filtered_df['Latitudine'].isnull().all() else rom_center[0]
    lon_center = filtered_df['Longitudine'].mean() if not filtered_df['Longitudine'].isnull().all() else rom_center[1]

    m = folium.Map(location=[lat_center, lon_center], zoom_start=6)
    marker_cluster = MarkerCluster().add_to(m)

    domain_colors = {}
    color_palette = ['red', 'blue', 'green', 'orange', 'purple', 'cadetblue', 'darkred', 'darkgreen', 'darkpurple', 'lightgray']
    if 'Domain' in df.columns:
        for i, domain in enumerate(all_domains):
            domain_colors[domain] = color_palette[i % len(color_palette)]

    for _, row in filtered_df.iterrows():
        lat, lon = row['Latitudine'], row['Longitudine']
        if pd.isna(lat) or pd.isna(lon):
            continue
        retailer = row['Magazin']
        address = row.get('Adresa', '')
        city = row.get('Oras', '')
        domain = row.get('Domain', '')
        turnover = row.get('Turnover 2023 (mil EUR)', '')
        employees = row.get('Avg employees number', '')

        logo_img = get_logo_base64(retailer)

        popup_html = f"""
        <b>{retailer}</b><br>
        <i>{domain}</i><br>
        {address}, {city}<br>
        Turnover: <b>{turnover}</b> mil EUR<br>
        Employees: <b>{employees}</b><br>
        {logo_img}
        """

        color = domain_colors.get(domain, "blue")
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=300),
            icon=folium.Icon(color=color, icon="info-sign"),
        ).add_to(marker_cluster)

    st_folium(m, width=900, height=600)
else:
    st.warning("No data matches your filters (or no retailers have both location and financial data).")

