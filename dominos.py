import time
import csv
import io
import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import streamlit as st
from datetime import datetime
from playwright.sync_api import sync_playwright

st.set_page_config(page_title="Dominos Coupon Finder", page_icon="🍕")

st.title("🍕 Dominos Coupon Finder")
st.write("Enter an address to find percentage discount coupons at your local Dominos store.")

def scrape_store_by_address(target_address, progress_bar, status_text):
    """
    Scrape coupons with percentage discounts from Dominos using API calls and HTML parsing
    
    Parameters:
    target_address (str): Part of the address to identify the store
    progress_bar: Streamlit progress bar to update
    status_text: Streamlit text element to update with status messages
    
    Returns:
    pd.DataFrame: DataFrame containing coupon information
    """
    BASE_URL = "https://www.dominos.ca"
    coupons_data = []
    
    try:
        # Step 1: Find store ID by address
        status_text.text("Searching for store locations...")
        progress_bar.progress(20)
        
        search_url = f"{BASE_URL}/en/pages/order/#!/locations/search/"
        session = requests.Session()
        
        # First get the search page to set cookies
        session.get(search_url)
        
        # Search for Montreal locations
        search_params = {
            'type': 'Carryout',
            'c': 'Montreal, QC'
        }
        
        response = session.get(f"{BASE_URL}/pps/finder/storelocator", params=search_params)
        stores = response.json().get('result', {}).get('Stores', [])
        
        # Find matching store
        target_store = None
        for store in stores:
            if target_address.lower() in store.get('StreetName', '').lower():
                target_store = store
                break
        
        if not target_store:
            status_text.text(f"No store found with address containing '{target_address}'")
            return pd.DataFrame()
        
        store_id = target_store['StoreID']
        store_address = f"{target_store['StreetName']}, {target_store['City']}"
        status_text.text(f"Found store: {store_address}")
        progress_bar.progress(40)
        
        # Step 2: Get coupons for this store
        status_text.text("Fetching coupons...")
        progress_bar.progress(60)
        
        menu_url = f"{BASE_URL}/en/pages/order/menu#!/menu/category/coupons/"
        response = session.get(menu_url)
        
        # Get the store-specific coupons page
        coupon_params = {
            'storeid': store_id,
            'coupons': 'all'
        }
        response = session.get(f"{BASE_URL}/order/loadcoupons", params=coupon_params)
        
        # Parse coupons
        soup = BeautifulSoup(response.text, 'html.parser')
        coupon_items = soup.find_all('div', class_='local-coupon__container')
        
        for coupon in coupon_items:
            description = coupon.find('p', class_='local-coupon__description')
            if description and '%' in description.text:
                coupon_code = coupon.find('a').get('data-couponcode', '')
                price = coupon.find('div', class_='local-coupon__price')
                
                coupons_data.append({
                    "Store Address": store_address,
                    "Coupon Description": description.text.strip(),
                    "Coupon Code": coupon_code,
                    "Price": price.text.strip() if price else "N/A"
                })
        
        progress_bar.progress(100)
        status_text.text(f"Found {len(coupons_data)} coupons for {store_address}")
        
    except Exception as e:
        status_text.text(f"An error occurred: {str(e)}")
        return pd.DataFrame()
    
    return pd.DataFrame(coupons_data) if coupons_data else pd.DataFrame()

# Create the Streamlit UI
st.sidebar.header("Search Settings")
address_input = st.sidebar.text_input("Enter Address Keywords", value="1215 Rue Bishop")

# Add a search button
if st.sidebar.button("Find Coupons"):
    if address_input:
        # Create a placeholder for the progress bar
        progress_bar = st.progress(0)
        
        # Create a placeholder for status updates
        status_text = st.empty()
        
        # Start the scraping process
        status_text.text("Starting search...")
        
        coupons_df = scrape_store_by_address(address_input, progress_bar, status_text)
        
        # Display results
        if not coupons_df.empty:
            st.subheader("Found Coupons")
            st.dataframe(coupons_df)
            
            # Create a download button for the results
            csv = coupons_df.to_csv(index=False)
            st.download_button(
                label="Download Coupons CSV",
                data=csv,
                file_name=f"dominos_coupons_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            
            # Also display the coupons as cards
            st.subheader("Coupon Details")
            for i, row in coupons_df.iterrows():
                with st.expander(f"Coupon: {row['Coupon Description'][:50]}..."):
                    st.write(f"**Description:** {row['Coupon Description']}")
                    st.write(f"**Code:** {row['Coupon Code']}")
                    st.write(f"**Price:** {row['Price']}")
                    st.write(f"**Store:** {row['Store Address']}")
        else:
            st.warning("No coupons found with the given address. Try a different address.")
    else:
        st.error("Please enter an address to search.")

# Instructions
with st.expander("How to use this app"):
    st.write("""
    1. Enter keywords from a Dominos store address in the sidebar (e.g., "1215 Rue Bishop")
    2. Click "Find Coupons" to start the search
    3. Wait for the scraper to find coupons with percentage discounts
    4. View the results in the table and download as CSV if needed
    
    Note: This app is currently configured to search for Dominos locations in Montreal, QC.
    """)

# Footer
st.sidebar.markdown("---")
st.sidebar.caption("Dominos Coupon Finder v1.0")