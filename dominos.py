import time
import csv
import io
import pandas as pd
import streamlit as st
from datetime import datetime
from playwright.sync_api import sync_playwright

st.set_page_config(page_title="Dominos Coupon Finder", page_icon="🍕")

st.title("🍕 Dominos Coupon Finder")
st.write("Enter an address to find percentage discount coupons at your local Dominos store.")

def scrape_store_by_address(target_address, progress_bar, status_text):
    """
    Scrape coupons with percentage discounts from a specific Dominos store by address
    
    Parameters:
    target_address (str): Part of the address to identify the store
    progress_bar: Streamlit progress bar to update
    status_text: Streamlit text element to update with status messages
    
    Returns:
    pd.DataFrame: DataFrame containing coupon information
    """
    # Setup Playwright
    status_text.text("Setting up Playwright...")
    progress_bar.progress(10)
    
    coupons_data = []
    
    with sync_playwright() as p:
        try:
            # Launch browser
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            
            # Navigate to the Dominos location search page
            status_text.text("Navigating to Dominos website...")
            progress_bar.progress(20)
            page.goto("https://www.dominos.ca/en/pages/order/#!/locations/search/")
            page.wait_for_load_state("networkidle")
            
            # Click carryout option
            page.locator("span.Carryout").click()
            
            # Enter "Montreal, QC" in the search input field
            status_text.text("Searching for Montreal, QC locations...")
            progress_bar.progress(30)
            search_input = page.locator("#cityFinder")
            search_input.fill("")
            search_input.fill("Montreal, QC")
            
            # Click the search button
            page.locator("button.js-searchboxButton").click()
            page.wait_for_load_state("networkidle")
            progress_bar.progress(40)
            
            # Find all store containers
            store_containers = page.locator("div.store__list-container").all()
            
            target_store = None
            store_full_address = ""
            
            # Find the store with the matching address
            status_text.text(f"Looking for store with address containing: {target_address}")
            progress_bar.progress(50)
            for container in store_containers:
                try:
                    # Find the street element
                    street_element = container.locator("div[data-quid$='-street']")
                    street_text = street_element.inner_text()
                    
                    # Check if our target address is in the street text
                    if target_address.lower() in street_text.lower():
                        # Get the store's ID for the button click
                        carryout_button = container.locator("button[data-type='Carryout']")
                        store_id = carryout_button.get_attribute("data-id")
                        
                        # Get full address for display
                        city_element = container.locator("div[data-quid$='-city'] span")
                        store_full_address = f"{street_text}, {city_element.inner_text()}"
                        
                        target_store = {
                            "container": container,
                            "id": store_id,
                            "button": carryout_button,
                            "address": store_full_address
                        }
                        status_text.text(f"Found target store: {store_full_address}")
                        break
                except Exception:
                    continue
            
            if not target_store:
                status_text.text(f"No store found with address containing '{target_address}'")
                return pd.DataFrame()
            
            # Click on the target store's carryout button
            status_text.text(f"Selecting store: {target_store['address']}...")
            progress_bar.progress(60)
            target_store['button'].click()
            page.wait_for_load_state("networkidle")
            
            # Navigate to coupons section
            status_text.text("Navigating to coupons page...")
            progress_bar.progress(70)
            
            # Click on the Coupons tile
            page.locator("a[data-quid='entree-coupons']").click()
            page.wait_for_load_state("networkidle")
            
            # Click on the "Find a Coupon" button
            page.locator("a.findCouponButton").click()
            page.wait_for_load_state("networkidle")
            
            # Wait for coupons to load
            status_text.text("Waiting for coupons to load...")
            progress_bar.progress(80)
            
            # Find percentage coupons
            status_text.text("Finding percentage discount coupons...")
            coupon_containers = page.locator("div.local-coupon__container").all()
            
            # Filter coupons with "%" in description
            for coupon in coupon_containers:
                try:
                    description_element = coupon.locator(".local-coupon__description p")
                    description_text = description_element.inner_text()
                    
                    if "%" in description_text:
                        coupon_code = coupon.locator("a").get_attribute("data-couponcode")
                        
                        try:
                            price_element = coupon.locator(".local-coupon__price")
                            price = price_element.inner_text()
                        except:
                            price = "N/A"
                        
                        # Add coupon to data list
                        coupons_data.append({
                            "Store Address": store_full_address,
                            "Coupon Description": description_text,
                            "Coupon Code": coupon_code,
                            "Price": price
                        })
                        
                        status_text.text(f"Found coupon: {description_text}")
                except Exception as e:
                    status_text.text(f"Error processing a coupon: {str(e)}")
            
            progress_bar.progress(100)
            status_text.text(f"Found {len(coupons_data)} percentage coupons for {store_full_address}")
            
        except Exception as e:
            status_text.text(f"An error occurred: {str(e)}")
            return pd.DataFrame()
        finally:
            browser.close()
    
    # Convert data to DataFrame
    if coupons_data:
        return pd.DataFrame(coupons_data)
    else:
        return pd.DataFrame()

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